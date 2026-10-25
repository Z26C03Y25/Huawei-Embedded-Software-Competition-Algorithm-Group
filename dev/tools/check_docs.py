"""Check local Markdown file links and preserved archive bytes; no web requests."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
IGNORED = {".git", ".venv", ".chrome-profile", "runs", "build", "tmp", "__pycache__"}
LINK = re.compile(r"\[[^\]\n]*\]\((<[^>]+>|[^)\s]+)(?:\s+\"[^\"]*\")?\)")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    errors, checked = [], 0
    # GitHub selects a .github README before the root project's homepage.
    for path in (ROOT / ".github").iterdir():
        if path.is_file() and path.stem.casefold() == "readme":
            errors.append(f"{path.relative_to(ROOT)} shadows the root README; use CONFIGURATION.md")
    documents = []
    for directory, names, files in os.walk(ROOT):
        names[:] = [name for name in names if name not in IGNORED]
        documents.extend(Path(directory) / name for name in files if name.endswith(".md"))
    for path in documents:
        for match in LINK.finditer(path.read_text(encoding="utf-8")):
            target = match.group(1).strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            checked += 1
            destination = (ROOT / unquote(parsed.path).lstrip("/")) if parsed.path.startswith("/") else (
                path.parent / unquote(parsed.path))
            if not destination.exists():
                errors.append(f"{path.relative_to(ROOT)}: missing link {target}")
    for manifest in (ROOT / "docs/archive/manifest.json", ROOT / "data/versions/manifest.json"):
        if not manifest.exists():
            errors.append(f"Missing archive manifest: {manifest.relative_to(ROOT)}")
            continue
        for row in json.loads(manifest.read_text(encoding="utf-8"))["files"]:
            source = ROOT / row["path"]
            if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != row["sha256"]:
                errors.append(f"Archive changed or missing: {row['path']}")
    for error in errors:
        print(error)
    print(f"Checked {checked} local Markdown links and 2 archive manifests; errors={len(errors)}")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
