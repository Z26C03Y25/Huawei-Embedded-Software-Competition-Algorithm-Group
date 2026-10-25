"""Install repository Git rules in .git/info, keeping the root at two files.

The versioned templates remain in .github; this does not contact any network.
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BEGIN = "# BEGIN autofocus-lab managed rules"
END = "# END autofocus-lab managed rules"


def git_path(*args) -> Path:
    result = subprocess.run(["git", "rev-parse", *args], cwd=ROOT, capture_output=True,
                            text=True, check=True)
    return (ROOT / result.stdout.strip()).resolve()


def main() -> int:
    common = git_path("--git-common-dir")
    for name, destination in (("gitignore", "info/exclude"), ("gitattributes", "info/attributes")):
        path = git_path("--git-path", destination)
        if not path.is_relative_to(common):
            raise RuntimeError("Git metadata target is outside this repository's common directory")
        template = (ROOT / ".github" / ("repository." + name)).read_text(encoding="utf-8")
        original = path.read_text(encoding="utf-8") if path.exists() else ""
        if BEGIN in original:
            start, end = original.index(BEGIN), original.index(END) + len(END)
            original = original[:start] + original[end:]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(original.rstrip() + "\n\n" + BEGIN + "\n" + template.rstrip() +
                        "\n" + END + "\n", encoding="utf-8")
    print("Installed local Git ignore/attribute rules; no root configuration files created.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
