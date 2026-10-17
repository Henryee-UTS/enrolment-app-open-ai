
"""Cross-platform pre-commit hook launcher: run pytest from the project root."""

import os
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)


def main() -> int:
    os.chdir(PROJECT_ROOT)
    
    return subprocess.call(  # noqa: S603 - trusted Python executable, shell=False
        [sys.executable, "-m", "pytest", *sys.argv[1:]]
    )



if __name__ == "__main__":
    sys.exit(main())
