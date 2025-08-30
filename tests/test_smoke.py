import subprocess
import sys


def _ok(cmd: list[str]) -> bool:
    p = subprocess.run(cmd, capture_output=True)
    return p.returncode == 0


def test_validate_canonical() -> None:
    assert _ok([sys.executable, "-m", "src.validate_canonical", "-h"])


def test_build_canonical() -> None:
    assert _ok([sys.executable, "src/build_canonical.py", "--help"])
