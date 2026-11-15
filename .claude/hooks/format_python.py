"""Claude Code hook (PostToolUse on Edit|Write): format the edited Python file with ruff.

Reads the hook payload (JSON) from stdin. Only formats, never fixes lint findings: an
automatic fix would remove an import that is added one edit before it is used. The hook
never blocks; a file that cannot be formatted (e.g. half-written syntax) is left alone.
"""

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    file_path = (payload.get("tool_input") or {}).get("file_path")
    if not file_path:
        return 0
    path = Path(file_path)
    if path.suffix != ".py" or not path.is_file():
        return 0
    subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--quiet", str(path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
