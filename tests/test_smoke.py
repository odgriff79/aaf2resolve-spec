import subprocess
import sys


def _ok(cmd: list[str]) -> bool:
    p = subprocess.run(cmd, capture_output=True)
    return p.returncode == 0


def test_validate_canonical() -> None:
    assert _ok([sys.executable, "src/validate_canonical.py", "--help"])


def test_build_canonical() -> None:
    assert _ok([sys.executable, "src/build_canonical.py", "--help"])
