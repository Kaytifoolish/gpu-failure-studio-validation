
"""Phase 5: isolated tests for the wheel verification process."""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "verify_dependencies.py"

PACKAGE = "example"
VERSION = "1.0"
WHEEL_NAME = "example-1.0-py3-none-any.whl"


class Phase5Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

        (self.root / "requirements.txt").write_text(
            f"{PACKAGE}=={VERSION}\n", encoding="utf-8"
        )
        (self.root / "wheelhouse").mkdir()
        (self.root / "verify_dependencies.py").write_bytes(
            VERIFIER.read_bytes()
        )

    def make_wheel(self):
        wheel = self.root / "wheelhouse" / WHEEL_NAME
        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr(
                "example-1.0.dist-info/METADATA",
                "Metadata-Version: 2.1\n"
                "Name: example\n"
                "Version: 1.0\n",
            )
        return wheel

    def approve(self, wheel, digest=None, filename=None):
        if digest is None:
            digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
        manifest = {
            PACKAGE: {
                "filename": filename or wheel.name,
                "sha256": digest,
            }
        }
        (self.root / "approved_wheels.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )

    def run_verifier(self):
        return subprocess.run(
            [sys.executable, str(self.root / "verify_dependencies.py")],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=20,
        )

    def test_refuse_manifest_absent(self):
        self.make_wheel()
        result = self.run_verifier()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("approved_wheels.json absent", result.stderr)

    def test_refuse_empreinte_incorrecte(self):
        wheel = self.make_wheel()
        self.approve(wheel, digest="0" * 64)
        result = self.run_verifier()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Empreinte non conforme", result.stderr)

    def test_refuse_fichier_supplementaire(self):
        wheel = self.make_wheel()
        self.approve(wheel)
        (self.root / "wheelhouse" / "extra.txt").write_text("extra")
        result = self.run_verifier()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("éléments non autorisés", result.stderr)

    def test_refuse_dependance_non_epinglee(self):
        (self.root / "requirements.txt").write_text(
            "example>=1.0\n", encoding="utf-8"
        )
        result = self.run_verifier()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Exigence non épinglée", result.stderr)

    def test_refuse_nom_non_approuve(self):
        wheel = self.make_wheel()
        self.approve(wheel, filename="autre-1.0-py3-none-any.whl")
        result = self.run_verifier()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Nom non approuvé", result.stderr)

    def test_accepte_wheel_synthetique(self):
        wheel = self.make_wheel()
        self.approve(wheel)
        result = self.run_verifier()
        self.assertEqual(
            result.returncode, 0,
            msg=result.stdout + result.stderr,
        )
        lock = self.root / "requirements.lock"
        self.assertTrue(lock.is_file())
        self.assertIn(
            "example==1.0 --hash=sha256:",
            lock.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
