

"""Phase 7 : test de refus d'une wheel au SHA-256 incorrect."""

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "verify_dependencies.py"


class Phase7Tests(unittest.TestCase):

    def test_rejects_incorrect_sha256(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wheelhouse = root / "wheelhouse"
            wheelhouse.mkdir()

            (root / "requirements.txt").write_text(
                "example==1.0\n",
                encoding="utf-8",
            )

            wheel_name = "example-1.0-py3-none-any.whl"
            wheel_path = wheelhouse / wheel_name

            with zipfile.ZipFile(wheel_path, "w") as archive:
                archive.writestr(
                    "example-1.0.dist-info/METADATA",
                    "Metadata-Version: 2.1\n"
                    "Name: example\n"
                    "Version: 1.0\n",
                )

            approved = {
                "example": {
                    "filename": wheel_name,
                    "sha256": "0" * 64,
                }
            }

            (root / "approved_wheels.json").write_text(
                json.dumps(approved),
                encoding="utf-8",
            )

            (root / "verify_dependencies.py").write_bytes(
                VERIFIER.read_bytes()
            )

            result = subprocess.run(
                [sys.executable, str(root / "verify_dependencies.py")],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=30,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "Empreinte non conforme",
                result.stdout + result.stderr,
            )
            self.assertFalse(
                (root / "requirements.lock").exists()
            )


if __name__ == "__main__":
    unittest.main()
