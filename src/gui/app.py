from __future__ import annotations

import math
import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, font as tkfont, messagebox, scrolledtext, simpledialog, ttk
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.gui.i18n import LANGUAGES, translate
from src.settings import load_settings, save_settings
from src.suno.params import (
    BUILTIN_PRESETS,
    PARAM_SPECS,
    ParamSpec,
    ProcessingParams,
    preset_params,
)
from src.suno.pipeline import ProcessingResult, process_suno_wav

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AUDIO_PATTERNS = "*.wav *.WAV *.flac *.FLAC *.aif *.aiff *.AIF *.AIFF *.ogg *.mp3"
STAGES = ("load", "analyze", "render", "write")
PERCENT_PARAMS = ("mix", "quiet_fraction")
TOP_PROTECT_RANGE = (4000.0, 22000.0)
TOP_PROTECT_DEFAULT = 16000.0
FILE_SEP = "; "
CUSTOM_PREFIX = "★ "


def resolve_output_dir(text: str) -> Path:
    path = Path(text.strip() or "out").expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


def safe_filename(text: str) -> str:
    bad = '<>:"/\\|?*'
    cleaned = "".join("_" if c in bad else c for c in text).strip()
    return cleaned or "untitled"


def format_removal(removal: Dict[str, float]) -> str:
    return "  " + "   ".join(f"{band} {value:+.2f}" for band, value in removal.items())


class Tooltip:
    """Hover help whose text is looked up at show time (follows the language)."""

    def __init__(self, widget: tk.Widget, text_fn: Callable[[], str]) -> None:
        self.widget = widget
        self.text_fn = text_fn
        self.tip: Optional[tk.Toplevel] = None
        self.job: Optional[str] = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event: Any = None) -> None:
        self._cancel()
        self.job = self.widget.after(500, self._show)

    def _cancel(self) -> None:
        if self.job is not None:
            self.widget.after_cancel(self.job)
            self.job = None

    def _show(self) -> None:
        self.job = None
        x = self.widget.winfo_rootx() + 16
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(
            self.tip,
            text=self.text_fn(),
            justify=tk.LEFT,
            wraplength=340,
            background="#ffffe0",
            foreground="#000000",
            relief=tk.SOLID,
            borderwidth=1,
            padx=6,
            pady=4,
        ).pack()

    def _hide(self, _event: Any = None) -> None:
        self._cancel()
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


class ParamControl:
    """One labelled control (slider + numeric entry, or a dropdown) for a ParamSpec."""

    def __init__(
        self,
        parent: tk.Widget,
        row: int,
        spec: ParamSpec,
        app: "SunoCleanserApp",
    ) -> None:
        self.spec = spec
        self.app = app
        self.is_percent = spec.name in PERCENT_PARAMS
        self.is_top = spec.name == "top_protect_hz"

        self.widgets: List[tk.Widget] = []
        self.label = ttk.Label(parent)
        self.label.grid(row=row, column=0, sticky="w", padx=(0, 8), pady=2)
        self.widgets.append(self.label)
        app.register_text(self.label, "p." + spec.name)
        Tooltip(self.label, lambda: app.t("tip." + spec.name))

        self.entry_var = tk.StringVar()
        self.enabled_var = tk.BooleanVar(value=False)
        self.combo: Optional[ttk.Combobox] = None
        self.scale: Optional[ttk.Scale] = None

        if spec.choices is not None:
            self.combo = ttk.Combobox(
                parent,
                values=[str(c) for c in spec.choices],
                textvariable=self.entry_var,
                state="readonly",
                width=10,
            )
            self.combo.grid(row=row, column=1, sticky="w", pady=2)
            self.widgets.append(self.combo)
            self.combo.bind("<<ComboboxSelected>>", lambda _e: app.on_param_changed())
            return

        lo, hi = (TOP_PROTECT_RANGE if self.is_top else (spec.minimum, spec.maximum))
        self.scale_var = tk.DoubleVar(value=lo)
        self.scale = ttk.Scale(
            parent,
            from_=self._to_display(lo),
            to=self._to_display(hi),
            orient=tk.HORIZONTAL,
            variable=self.scale_var,
            command=self._on_scale,
        )
        self.scale.grid(row=row, column=1, sticky="ew", pady=2)

        right = ttk.Frame(parent)
        right.grid(row=row, column=2, sticky="w", padx=(8, 0))
        self.widgets.extend([self.scale, right])
        self.entry = ttk.Entry(right, textvariable=self.entry_var, width=8, justify=tk.RIGHT)
        self.entry.pack(side=tk.LEFT)
        self.entry.bind("<Return>", self._on_entry)
        self.entry.bind("<FocusOut>", self._on_entry)
        ttk.Label(right, text=self._unit(), width=3).pack(side=tk.LEFT, padx=(3, 0))

        if self.is_top:
            self.check = ttk.Checkbutton(
                right, variable=self.enabled_var, command=self._on_toggle
            )
            self.check.pack(side=tk.LEFT, padx=(6, 0))
            app.register_text(self.check, "enabled")

    def show(self, visible: bool) -> None:
        for widget in self.widgets:
            if visible:
                widget.grid()
            else:
                widget.grid_remove()

    # --- unit conversion -------------------------------------------------
    def _to_display(self, value: float) -> float:
        return value * 100.0 if self.is_percent else value

    def _from_display(self, value: float) -> float:
        return value / 100.0 if self.is_percent else value

    def _unit(self) -> str:
        if self.is_percent:
            return "%"
        return self.spec.unit

    def _display_step(self) -> float:
        return self._to_display(self.spec.step)

    def _fmt(self, value: float) -> str:
        step = self._display_step()
        decimals = max(0, -int(math.floor(math.log10(step)))) if step < 1 else 0
        return f"{self._to_display(value):.{decimals}f}"

    def _snap(self, value: float) -> float:
        lo, hi = (TOP_PROTECT_RANGE if self.is_top else (self.spec.minimum, self.spec.maximum))
        step = self.spec.step
        snapped = round(round(value / step) * step, 6)
        return min(max(snapped, lo), hi)

    # --- events ----------------------------------------------------------
    def _on_scale(self, _raw: str) -> None:
        value = self._snap(self._from_display(self.scale_var.get()))
        self.entry_var.set(self._fmt(value))
        if self.is_top and not self.enabled_var.get():
            return
        self.app.on_param_changed()

    def _on_entry(self, _event: Any = None) -> None:
        text = self.entry_var.get().strip().replace(",", ".")
        try:
            value = self._snap(self._from_display(float(text)))
        except ValueError:
            messagebox.showerror("SunoCleanser", self.app.t("invalid_number", value=text))
            value = self._snap(self._from_display(self.scale_var.get()))
        self.scale_var.set(self._to_display(value))
        self.entry_var.set(self._fmt(value))
        self.app.on_param_changed()

    def _on_toggle(self) -> None:
        self._sync_enabled()
        self.app.on_param_changed()

    def _sync_enabled(self) -> None:
        state = tk.NORMAL if self.enabled_var.get() else tk.DISABLED
        if self.scale is not None:
            self.scale.state(["!disabled"] if state == tk.NORMAL else ["disabled"])
        self.entry.configure(state=state)

    # --- value access ----------------------------------------------------
    def get(self) -> Any:
        if self.combo is not None:
            kind = type(self.spec.choices[0])
            return kind(self.entry_var.get())
        if self.is_top and not self.enabled_var.get():
            return 0.0
        return self._snap(self._from_display(self.scale_var.get()))

    def set(self, value: Any) -> None:
        if self.combo is not None:
            self.entry_var.set(str(value))
            return
        if self.is_top:
            enabled = float(value) > 0
            self.enabled_var.set(enabled)
            if enabled:
                value = float(value)
            else:
                value = self._snap(self._from_display(self.scale_var.get())) or TOP_PROTECT_DEFAULT
                if value <= TOP_PROTECT_RANGE[0]:
                    value = TOP_PROTECT_DEFAULT
            self._sync_enabled()
        value = self._snap(float(value))
        self.scale_var.set(self._to_display(value))
        self.entry_var.set(self._fmt(value))


class SunoCleanserApp:
    def __init__(self, root: tk.Tk, initial_wav: Optional[Path] = None) -> None:
        self.root = root
        self.root.title("SunoCleanser")
        self.root.minsize(640, 560)

        self.settings = load_settings()
        self.lang_var = tk.StringVar(value=self.settings["language"])
        self.files_var = tk.StringVar()
        self.title_var = tk.StringVar()
        self.output_var = tk.StringVar(value=self.settings["output_dir"])
        self.preset_var = tk.StringVar()
        self.tag_var = tk.BooleanVar(value=False)
        self.advanced_var = tk.BooleanVar(value=self.settings["show_advanced"])
        self.custom_presets: Dict[str, Dict[str, Any]] = dict(self.settings["custom_presets"])
        self.current_preset = self.settings["preset"]
        if self.current_preset not in BUILTIN_PRESETS and self.current_preset not in self.custom_presets:
            self.current_preset = "original"

        self._texts: List[Tuple[tk.Widget, str]] = []
        self._controls: Dict[str, ParamControl] = {}
        self._suspend = False
        self._processing = False

        self._build()
        self._apply_language()
        self._apply_params(ProcessingParams.from_dict(self.settings["params"], base=self._preset_base()))
        self.files_var.trace_add("write", lambda *_a: self._sync_title_state())

        if initial_wav is not None:
            self._set_files([initial_wav])

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # --- i18n ------------------------------------------------------------
    def t(self, key: str, **kwargs: object) -> str:
        return translate(self.lang_var.get(), key, **kwargs)

    def register_text(self, widget: tk.Widget, key: str) -> None:
        self._texts.append((widget, key))

    def _apply_language(self) -> None:
        for widget, key in self._texts:
            widget.configure(text=self.t(key))
        self._refresh_preset_choices()
        self._sync_title_state()

    # --- layout ----------------------------------------------------------
    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)
        outer.columnconfigure(0, weight=1)

        header = ttk.Frame(outer)
        header.grid(row=0, column=0, sticky="ew")
        title_font = tkfont.nametofont("TkDefaultFont").copy()
        title_font.configure(size=max(14, int(title_font.cget("size")) + 4), weight="bold")
        ttk.Label(header, text="SunoCleanser", font=title_font).pack(side=tk.LEFT)
        self._title_font = title_font  # keep a reference
        lang_box = ttk.Frame(header)
        lang_box.pack(side=tk.RIGHT)
        for code in LANGUAGES:
            button = ttk.Radiobutton(
                lang_box,
                text=code.upper(),
                value=code,
                variable=self.lang_var,
                command=self._apply_language,
                style="Toolbutton",
                width=4,
            )
            button.pack(side=tk.LEFT)
            Tooltip(button, lambda: self.t("tip.language"))

        files = ttk.Frame(outer)
        files.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        files.columnconfigure(0, weight=1)
        input_label = ttk.Label(files)
        input_label.grid(row=0, column=0, sticky="w")
        self.register_text(input_label, "input")
        ttk.Entry(files, textvariable=self.files_var).grid(row=1, column=0, sticky="ew")
        browse = ttk.Button(files, command=self._browse)
        browse.grid(row=1, column=1, padx=(8, 0))
        self.register_text(browse, "browse")

        self.title_label = ttk.Label(files)
        self.title_label.grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.title_entry = ttk.Entry(files, textvariable=self.title_var)
        self.title_entry.grid(row=3, column=0, sticky="ew")
        tag = ttk.Checkbutton(files, variable=self.tag_var)
        tag.grid(row=3, column=1, padx=(8, 0), sticky="w")
        self.register_text(tag, "tag_preset")

        out_label = ttk.Label(files)
        out_label.grid(row=4, column=0, sticky="w", pady=(8, 0))
        self.register_text(out_label, "output")
        out_row = ttk.Frame(files)
        out_row.grid(row=5, column=0, columnspan=2, sticky="ew")
        out_row.columnconfigure(0, weight=1)
        ttk.Entry(out_row, textvariable=self.output_var).grid(row=0, column=0, sticky="ew")
        choose = ttk.Button(out_row, command=self._choose_output)
        choose.grid(row=0, column=1, padx=(8, 0))
        self.register_text(choose, "choose")
        open_btn = ttk.Button(out_row, command=self._open_out)
        open_btn.grid(row=0, column=2, padx=(8, 0))
        self.register_text(open_btn, "open_output")

        box = ttk.LabelFrame(outer, padding=10)
        box.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        box.columnconfigure(0, weight=1)
        self.register_text(box, "settings")

        preset_row = ttk.Frame(box)
        preset_row.grid(row=0, column=0, sticky="ew")
        preset_label = ttk.Label(preset_row)
        preset_label.pack(side=tk.LEFT)
        self.register_text(preset_label, "preset")
        self.preset_combo = ttk.Combobox(preset_row, textvariable=self.preset_var, state="readonly", width=22)
        self.preset_combo.pack(side=tk.LEFT, padx=(8, 4))
        self.preset_combo.bind("<<ComboboxSelected>>", self._on_preset_selected)
        self.modified_label = ttk.Label(preset_row, foreground="#b36b00")
        self.modified_label.pack(side=tk.LEFT)
        for key, cmd in (("delete_preset", self._delete_preset), ("save_preset", self._save_preset), ("reset", self._reset)):
            btn = ttk.Button(preset_row, command=cmd)
            btn.pack(side=tk.RIGHT, padx=(4, 0))
            self.register_text(btn, key)

        grid = ttk.Frame(box)
        grid.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        grid.columnconfigure(1, weight=1)
        gui_specs = [s for s in PARAM_SPECS if s.gui]
        basic_specs = [s for s in gui_specs if not s.advanced]
        advanced_specs = [s for s in gui_specs if s.advanced]
        row = 0
        for spec in basic_specs:
            self._controls[spec.name] = ParamControl(grid, row, spec, self)
            row += 1
        adv_toggle = ttk.Checkbutton(grid, variable=self.advanced_var, command=self._sync_advanced)
        adv_toggle.grid(row=row, column=0, columnspan=3, sticky="w", pady=(8, 4))
        self.register_text(adv_toggle, "advanced")
        row += 1
        for spec in advanced_specs:
            self._controls[spec.name] = ParamControl(grid, row, spec, self)
            row += 1
        self._sync_advanced()

        actions = ttk.Frame(outer)
        actions.grid(row=3, column=0, sticky="ew", pady=(12, 6))
        actions.columnconfigure(1, weight=1)
        self.run_btn = ttk.Button(actions, command=self._start)
        self.run_btn.grid(row=0, column=0)
        self.register_text(self.run_btn, "process")
        self.progress = ttk.Progressbar(actions, mode="determinate")
        self.progress.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        self.status = ttk.Label(outer, foreground="#555555")
        self.status.grid(row=4, column=0, sticky="w")

        self.log = scrolledtext.ScrolledText(outer, height=9, state=tk.DISABLED, wrap=tk.WORD)
        self.log.grid(row=5, column=0, sticky="nsew", pady=(4, 0))
        outer.rowconfigure(5, weight=1)

    def _sync_advanced(self) -> None:
        visible = bool(self.advanced_var.get())
        for control in self._controls.values():
            if control.spec.advanced:
                control.show(visible)

    def _sync_title_state(self) -> None:
        batch = len(self._parse_files()) > 1
        self.title_label.configure(text=self.t("title_batch" if batch else "title"))
        self.title_entry.configure(state=tk.DISABLED if batch else tk.NORMAL)

    # --- presets ---------------------------------------------------------
    def _preset_display(self, name: str) -> str:
        if name in BUILTIN_PRESETS:
            return self.t("preset." + name)
        return CUSTOM_PREFIX + name

    def _preset_names(self) -> List[str]:
        return list(BUILTIN_PRESETS) + sorted(self.custom_presets)

    def _refresh_preset_choices(self) -> None:
        self.preset_combo.configure(values=[self._preset_display(n) for n in self._preset_names()])
        self.preset_var.set(self._preset_display(self.current_preset))
        self._update_modified()

    def _preset_base(self) -> ProcessingParams:
        return preset_params(self.current_preset, self.custom_presets)

    def _on_preset_selected(self, _event: Any = None) -> None:
        shown = self.preset_var.get()
        for name in self._preset_names():
            if self._preset_display(name) == shown:
                self.current_preset = name
                break
        self._apply_params(self._preset_base())

    def _reset(self) -> None:
        self._apply_params(self._preset_base())

    def _save_preset(self) -> None:
        name = simpledialog.askstring("SunoCleanser", self.t("preset_name_prompt"), parent=self.root)
        if not name or not name.strip():
            return
        name = name.strip()
        if name in BUILTIN_PRESETS or name in [self.t("preset." + b) for b in BUILTIN_PRESETS]:
            messagebox.showerror("SunoCleanser", self.t("preset_builtin_name"))
            return
        if name in self.custom_presets and not messagebox.askyesno(
            "SunoCleanser", self.t("preset_overwrite", name=name)
        ):
            return
        try:
            params = self.current_params().validate()
        except ValueError as exc:
            messagebox.showerror("SunoCleanser", str(exc))
            return
        self.custom_presets[name] = params.to_dict()
        self.current_preset = name
        self._refresh_preset_choices()
        self._persist()

    def _delete_preset(self) -> None:
        name = self.current_preset
        if name in BUILTIN_PRESETS:
            messagebox.showinfo("SunoCleanser", self.t("preset_cannot_delete"))
            return
        if not messagebox.askyesno("SunoCleanser", self.t("preset_delete_confirm", name=name)):
            return
        self.custom_presets.pop(name, None)
        self.current_preset = "original"
        self._refresh_preset_choices()
        self._apply_params(self._preset_base())
        self._persist()

    # --- params ----------------------------------------------------------
    def current_params(self) -> ProcessingParams:
        values = {name: control.get() for name, control in self._controls.items()}
        return ProcessingParams.from_dict(values, base=self._preset_base())

    def _apply_params(self, params: ProcessingParams) -> None:
        self._suspend = True
        try:
            for name, control in self._controls.items():
                control.set(getattr(params, name))
        finally:
            self._suspend = False
        self._update_modified()

    def on_param_changed(self) -> None:
        if not self._suspend:
            self._update_modified()

    def _update_modified(self) -> None:
        if not self._controls:
            return
        try:
            modified = self.current_params() != self._preset_base()
        except (KeyError, ValueError):
            modified = True
        self.modified_label.configure(text=self.t("modified") if modified else "")

    # --- files -----------------------------------------------------------
    def _parse_files(self) -> List[Path]:
        text = self.files_var.get().strip()
        if not text:
            return []
        return [Path(p.strip()).expanduser() for p in text.split(FILE_SEP.strip()) if p.strip()]

    def _set_files(self, paths: List[Path]) -> None:
        self.files_var.set(FILE_SEP.join(str(p) for p in paths))
        if len(paths) == 1:
            self.title_var.set(paths[0].stem)
        if paths:
            self.settings["last_dir"] = str(paths[0].parent)

    def _browse(self) -> None:
        chosen = filedialog.askopenfilenames(
            title=self.t("pick_files"),
            initialdir=self.settings.get("last_dir") or None,
            filetypes=[(self.t("audio_files"), AUDIO_PATTERNS), (self.t("all_files"), "*")],
        )
        if chosen:
            self._set_files([Path(c) for c in chosen])

    def _choose_output(self) -> None:
        chosen = filedialog.askdirectory(initialdir=str(resolve_output_dir(self.output_var.get())))
        if chosen:
            self.output_var.set(chosen)

    def _open_out(self) -> None:
        folder = resolve_output_dir(self.output_var.get())
        folder.mkdir(parents=True, exist_ok=True)
        opened = False
        try:
            if sys.platform == "win32":
                os.startfile(folder)  # noqa: S606
                opened = True
            elif sys.platform == "darwin":
                opened = subprocess.run(["open", str(folder)], check=False).returncode == 0
            else:
                opened = subprocess.run(["xdg-open", str(folder)], check=False).returncode == 0
        except OSError:
            opened = False
        if not opened:
            messagebox.showinfo("SunoCleanser", self.t("folder", path=folder))

    # --- processing ------------------------------------------------------
    def _log(self, message: str) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def _start(self) -> None:
        if self._processing:
            return
        files = self._parse_files()
        missing = [p.name or str(p) for p in files if not p.is_file()]
        if not files:
            messagebox.showerror("SunoCleanser", self.t("select_valid"))
            return
        if missing:
            messagebox.showerror("SunoCleanser", self.t("files_missing", files=", ".join(missing)))
            return
        try:
            params = self.current_params().validate()
        except ValueError as exc:
            messagebox.showerror("SunoCleanser", str(exc))
            return

        tag = ""
        if self.tag_var.get():
            tag = f" [{self._preset_display(self.current_preset).replace(CUSTOM_PREFIX, '')}"
            tag += f" {self.t('modified')}]" if self.modified_label.cget("text") else "]"
        single_title = self.title_var.get().strip()
        jobs: List[Tuple[Path, str]] = []
        for path in files:
            base = single_title if (len(files) == 1 and single_title) else path.stem
            jobs.append((path, safe_filename(base + tag)))

        out_dir = resolve_output_dir(self.output_var.get())
        self._processing = True
        self.run_btn.state(["disabled"])
        self.progress.configure(maximum=len(jobs) * len(STAGES), value=0)
        self._persist()
        threading.Thread(target=self._worker, args=(jobs, out_dir, params), daemon=True).start()

    def _worker(self, jobs: List[Tuple[Path, str]], out_dir: Path, params: ProcessingParams) -> None:
        ok = 0
        for index, (path, title) in enumerate(jobs, start=1):
            header = self.t("processing", i=index, n=len(jobs), name=path.name)
            self.root.after(0, lambda h=header: self._log(h))

            def progress(stage: str, h: str = header) -> None:
                self.root.after(0, lambda: self._on_stage(h, stage))

            try:
                out_dir.mkdir(parents=True, exist_ok=True)
                result = process_suno_wav(
                    input_path=path,
                    out_dir=out_dir,
                    title=title,
                    params=params,
                    report_path=out_dir / f"{title}.report.json",
                    progress=progress,
                )
                ok += 1
                self.root.after(0, lambda r=result: self._on_file_done(r))
            except Exception as exc:  # report and continue with the batch
                msg = self.t("file_error", name=path.name, error=exc)
                self.root.after(0, lambda m=msg: self._log(m))
            self.root.after(0, lambda i=index: self.progress.configure(value=i * len(STAGES)))
        self.root.after(0, lambda: self._finish(ok, len(jobs)))

    def _on_stage(self, header: str, stage: str) -> None:
        self.status.configure(text=f"{header} — {self.t('stage_' + stage)}")
        self.progress.step(1)

    def _on_file_done(self, result: ProcessingResult) -> None:
        self._log(self.t("removed_header"))
        self._log(format_removal(result.report.get("band_removal_db", {})))
        self._log(f"  {self.t('clean')}: {result.clean_path.name}")
        self._log(f"  {self.t('noise')}: {result.noise_path.name}")

    def _finish(self, ok: int, total: int) -> None:
        self._processing = False
        self.run_btn.state(["!disabled"])
        summary = self.t("done_all", ok=ok, n=total)
        self.status.configure(text=summary)
        self._log(summary)
        if ok == total:
            messagebox.showinfo(self.t("done_title"), summary)
        else:
            messagebox.showerror(self.t("error_title"), summary)

    # --- persistence -----------------------------------------------------
    def _persist(self) -> None:
        try:
            params = self.current_params().to_dict()
        except (KeyError, ValueError):
            params = {}
        self.settings.update(
            {
                "language": self.lang_var.get(),
                "preset": self.current_preset,
                "params": params,
                "custom_presets": self.custom_presets,
                "output_dir": self.output_var.get().strip() or "out",
                "show_advanced": bool(self.advanced_var.get()),
            }
        )
        save_settings(self.settings)

    def _on_close(self) -> None:
        self._persist()
        self.root.destroy()


OLD_TK_MESSAGE = """\
SunoCleanser: this Python uses Tk {tk} ({exe}).
Apple's system Python ships Tk 8.5, which shows a blank gray window on current macOS.
Use a Python with Tk 8.6+ instead (conda env, python.org installer, or Homebrew
python + python-tk). ./sunocleanser-gui.sh picks one automatically.
Set SUNOCLEANSER_ALLOW_OLD_TK=1 to try anyway."""


def tk_is_usable() -> bool:
    if tk.TkVersion >= 8.6 or os.environ.get("SUNOCLEANSER_ALLOW_OLD_TK") == "1":
        return True
    return sys.platform != "darwin"


def run_app(argv: Optional[List[str]] = None) -> None:
    if not tk_is_usable():
        print(OLD_TK_MESSAGE.format(tk=tk.TkVersion, exe=sys.executable), file=sys.stderr)
        raise SystemExit(1)

    initial: Optional[Path] = None
    if argv:
        candidate = Path(argv[0])
        if candidate.is_file():
            initial = candidate

    root = tk.Tk()
    SunoCleanserApp(root, initial_wav=initial)
    root.mainloop()
