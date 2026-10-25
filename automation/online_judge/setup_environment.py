"""Install Playwright into the local venv, with temp files inside this folder."""

from pathlib import Path
import os
import subprocess
import sys
import venv


def main() -> int:
    if sys.version_info < (3, 10):
        raise SystemExit("Python 3.10 or later is required.")
    base = Path(__file__).resolve().parent
    environment = base / ".venv"
    interpreter = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if not interpreter.is_file():
        venv.EnvBuilder(with_pip=False).create(environment)
    temporary = base / ".setup-tmp"
    temporary.mkdir(exist_ok=True)
    child_environment = os.environ.copy()
    child_environment.update({"TEMP": str(temporary), "TMP": str(temporary),
                              "TMPDIR": str(temporary), "PYTHONUTF8": "1"})
    bootstrap = ("import sys,tempfile,ensurepip; tempfile.tempdir=sys.argv[1]; "
                 "ensurepip.bootstrap(upgrade=True,default_pip=True)")
    subprocess.run([str(interpreter), "-c", bootstrap, str(temporary)], check=True,
                   env=child_environment)
    install = ("import sys,tempfile,runpy; tempfile.tempdir=sys.argv[1]; "
               "sys.argv=['pip','install','--no-cache-dir','-r',sys.argv[2]]; "
               "runpy.run_module('pip',run_name='__main__')")
    subprocess.run([str(interpreter), "-c", install, str(temporary),
                    str(base / "requirements.txt")], check=True, env=child_environment)
    return subprocess.run([str(interpreter), str(base / "judge.py"), "doctor"]).returncode


if __name__ == "__main__":
    raise SystemExit(main())
