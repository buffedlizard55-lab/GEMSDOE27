from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_download_verifier_explains_missing_local_inputs(tmp_path):
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["GEMS_DATA_DIR"] = str(tmp_path / "empty-data-cache")

    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "verify_downloads.py")],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "required local inputs are missing" in result.stderr
    assert "python scripts/restore_data.py" in result.stderr
    assert "not an organizer-authenticated DrivenData download" in result.stderr
    assert "Traceback" not in result.stderr
