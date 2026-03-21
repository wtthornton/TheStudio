# Developing in WSL (Bash on Windows)

## Why `source c:/cursor/.../activate` fails

In WSL, Bash does **not** treat `c:/...` as a path. The repo lives under **`/mnt/c/...`** (for the `C:` drive). So the activate script must be referenced like this if you insist on the Windows venv:

```bash
source /mnt/c/cursor/TheStudio/.venv/Scripts/activate
```

That only fixes “file not found.” The Windows virtualenv still sets `VIRTUAL_ENV` to a `C:\...` path and prepends **`Scripts/`** (with `python.exe`). In a Linux shell that mix is unreliable, so **do not use the Windows `.venv` from WSL**.

## Recommended: Linux venv in the same clone

From your WSL shell, with the repo under `/mnt/c/cursor/TheStudio` (or your path):

```bash
cd /mnt/c/cursor/TheStudio
bash scripts/setup-wsl-venv.sh    # first time: creates .venv-wsl and installs deps
source .venv-wsl/bin/activate
```

After that, `python`, `pip`, and `pytest` use Linux binaries and behave normally.

## One-liner (manual)

```bash
cd /mnt/c/cursor/TheStudio
python3 -m venv .venv-wsl
source .venv-wsl/bin/activate
pip install -U pip
pip install -e ".[dev]"
```

`.venv-wsl/` is gitignored. Keep using **PowerShell** with `.venv\Scripts\Activate.ps1` on Windows when you work from the Windows side.
