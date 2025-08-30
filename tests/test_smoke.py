import subprocess, sys

def _ok(cmd: list[str]) -> bool:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.returncode == 0

def test_validate_canonical_help():
    assert _ok([sys.executable, "-m", "src.validate_canonical", "-h"])

def test_write_fcpxml_help():
    assert _ok([sys.executable, "-m", "src.write_fcpxml", "-h"])
