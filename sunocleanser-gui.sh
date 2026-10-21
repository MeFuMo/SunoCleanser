#!/usr/bin/env bash
# Launch the GUI with the first Python that has Tk 8.6+ and the audio libraries.
# Apple's system Python (/usr/bin/python3, Command Line Tools) ships Tk 8.5, which
# draws a blank gray window on current macOS, so it is skipped automatically.
# Override with: SUNOCLEANSER_PYTHON=/path/to/python ./sunocleanser-gui.sh
set -uo pipefail
cd "$(dirname "$0")"

PROBE='import sys, tkinter
missing = []
for mod in ("numpy", "scipy", "soundfile"):
    try:
        __import__(mod)
    except Exception:
        missing.append(mod)
print("Python %d.%d, Tk %s%s" % (sys.version_info[0], sys.version_info[1], tkinter.TkVersion,
      (", missing: " + " ".join(missing)) if missing else ""))
sys.exit(3 if tkinter.TkVersion < 8.6 else (4 if missing else 0))'

candidates=()
[[ -n "${SUNOCLEANSER_PYTHON:-}" ]] && candidates+=("${SUNOCLEANSER_PYTHON}")
candidates+=(venv/bin/python .venv/bin/python)

# conda env "sunocleanser", wherever conda lives
conda_bases=()
if command -v conda >/dev/null 2>&1; then
  conda_bases+=("$(conda info --base 2>/dev/null)")
fi
conda_bases+=(
  "${HOME}/miniconda3" "${HOME}/anaconda3" "${HOME}/miniforge3" "${HOME}/mambaforge"
  "/opt/homebrew/Caskroom/miniconda/base" "/opt/homebrew/Caskroom/miniforge/base"
  "/usr/local/Caskroom/miniconda/base" "/opt/conda" "/opt/miniconda3"
)
for base in "${conda_bases[@]}"; do
  [[ -n "${base}" ]] && candidates+=("${base}/envs/sunocleanser/bin/python")
done

for v in 3.13 3.12 3.11 3.10; do
  candidates+=("/Library/Frameworks/Python.framework/Versions/${v}/bin/python3"
               "/opt/homebrew/bin/python${v}" "/usr/local/bin/python${v}")
  command -v "python${v}" >/dev/null 2>&1 && candidates+=("$(command -v "python${v}")")
done
command -v python3 >/dev/null 2>&1 && candidates+=("$(command -v python3)")

report=""
seen=" "
for py in "${candidates[@]}"; do
  [[ -x "${py}" ]] || continue
  real="$(cd "$(dirname "${py}")" && pwd -P)/$(basename "${py}")"
  [[ "${seen}" == *" ${real} "* ]] && continue
  seen+="${real} "
  info="$("${py}" -c "${PROBE}" 2>/dev/null)"
  status=$?
  if [[ ${status} -eq 0 ]]; then
    exec "${py}" -m src.gui "$@"
  fi
  [[ -z "${info}" ]] && info="no tkinter"
  report+="  ${py}  (${info})"$'\n'
done

cat >&2 <<EOF
Error: no Python found with Tk 8.6+ and numpy/scipy/soundfile.

Checked:
${report:-  (none found)}
Fix (pick one):
  * conda:   conda env create -f environment.yml
  * python.org installer (bundles a modern Tk), then:
             rm -rf venv && /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -m venv venv
             venv/bin/pip install -r requirements.txt
  * Homebrew: brew install python@3.12 python-tk@3.12, then recreate venv with /opt/homebrew/bin/python3.12
  If a listed Python has Tk 8.6 but is only missing modules, install them:
             <that python> -m pip install -r requirements.txt
EOF
exit 1
