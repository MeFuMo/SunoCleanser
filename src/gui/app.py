from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext

from src.suno.pipeline import ProcessingParams, ProcessingResult, process_suno_wav

OUT_DIR = Path("out")


class SunoCleanserApp:
    def __init__(self, root: tk.Tk, initial_wav: Path | None = None) -> None:
        self.root = root
        self.root.title("SunoCleanser")
        self.root.minsize(520, 380)

        self.wav_var = tk.StringVar()
        self.title_var = tk.StringVar()
        self._processing = False

        frame = tk.Frame(root, padx=12, pady=12)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="WAV de entrada").grid(row=0, column=0, sticky="w")
        entry_row = tk.Frame(frame)
        entry_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(2, 0))
        tk.Entry(entry_row, textvariable=self.wav_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        tk.Button(entry_row, text="Examinar…", command=self._browse).pack(
            side=tk.LEFT, padx=(8, 0)
        )

        tk.Label(frame, text="Título (nombres de salida)").grid(
            row=2, column=0, sticky="w", pady=(10, 0)
        )
        tk.Entry(frame, textvariable=self.title_var).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(2, 0)
        )

        tk.Label(frame, text="Salida: carpeta out/ (solo local)").grid(
            row=4, column=0, sticky="w", pady=(10, 0)
        )

        actions = tk.Frame(frame)
        actions.grid(row=5, column=0, columnspan=2, sticky="w", pady=12)
        self.run_btn = tk.Button(actions, text="Procesar", command=self._start)
        self.run_btn.pack(side=tk.LEFT)
        tk.Button(actions, text="Abrir out/", command=self._open_out).pack(
            side=tk.LEFT, padx=8
        )

        self.log = scrolledtext.ScrolledText(frame, height=14, state=tk.DISABLED)
        self.log.grid(row=6, column=0, columnspan=2, sticky="nsew")

        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(6, weight=1)

        if initial_wav is not None:
            self._set_wav(initial_wav)

    def _set_wav(self, path: Path) -> None:
        self.wav_var.set(str(path))
        if not self.title_var.get().strip():
            self.title_var.set(path.stem)

    def _log(self, message: str) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, message + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def _browse(self) -> None:
        chosen = filedialog.askopenfilename(
            title="Seleccionar WAV",
            filetypes=[("WAV", "*.wav"), ("Todos", "*.*")],
        )
        if chosen:
            self._set_wav(Path(chosen))

    def _open_out(self) -> None:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        folder = OUT_DIR.resolve()
        opened = False
        if sys.platform == "win32":
            os.startfile(folder)  # noqa: S606
            opened = True
        elif sys.platform == "darwin":
            opened = subprocess.run(["open", folder], check=False).returncode == 0
        else:
            opened = subprocess.run(["xdg-open", folder], check=False).returncode == 0
        if not opened:
            messagebox.showinfo("SunoCleanser", f"Carpeta: {folder}")

    def _start(self) -> None:
        if self._processing:
            return
        wav = Path(self.wav_var.get().strip())
        if not wav.is_file():
            messagebox.showerror("SunoCleanser", "Selecciona un archivo WAV válido.")
            return

        title = self.title_var.get().strip() or wav.stem
        self._processing = True
        self.run_btn.configure(state=tk.DISABLED)
        self._log("Procesando…")

        thread = threading.Thread(
            target=self._worker,
            args=(wav, title),
            daemon=True,
        )
        thread.start()

    def _worker(self, wav: Path, title: str) -> None:
        try:
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            report_path = OUT_DIR / f"{wav.stem}.report.json"
            result = process_suno_wav(
                input_path=wav,
                out_dir=OUT_DIR,
                title=title,
                params=ProcessingParams(),
                report_path=report_path,
            )
            self.root.after(0, lambda r=result: self._finish_ok(r))
        except Exception as exc:
            self.root.after(0, lambda msg=str(exc): self._finish_err(msg))

    def _finish_ok(self, result: ProcessingResult) -> None:
        self._log(json.dumps(result.report, indent=2))
        self._log(f"Clean: {result.clean_path.name}")
        self._log(f"Noise: {result.noise_path.name}")
        self._processing = False
        self.run_btn.configure(state=tk.NORMAL)
        messagebox.showinfo("SunoCleanser", "Listo. Revisa la carpeta out/.")

    def _finish_err(self, message: str) -> None:
        self._log(f"Error: {message}")
        self._processing = False
        self.run_btn.configure(state=tk.NORMAL)
        messagebox.showerror("SunoCleanser", message)


def run_app(argv: list[str] | None = None) -> None:
    initial: Path | None = None
    if argv:
        candidate = Path(argv[0])
        if candidate.is_file():
            initial = candidate

    root = tk.Tk()
    SunoCleanserApp(root, initial_wav=initial)
    root.mainloop()
