
import tempfile
import unittest
from pathlib import Path

from safety import publish_no_overwrite


class TestPublicationSansEcrasement(unittest.TestCase):

    def test_refuse_ecrasement(self):
        with tempfile.TemporaryDirectory() as dossier:
            dossier = Path(dossier)
            temporaire = dossier / "temporaire.tiff"
            destination = dossier / "photo.tiff"

            temporaire.write_bytes(b"NOUVEL_EXPORT")
            destination.write_bytes(b"FICHIER_ORIGINAL")

            with self.assertRaises(FileExistsError):
                publish_no_overwrite(temporaire, destination)

            self.assertEqual(
                destination.read_bytes(),
                b"FICHIER_ORIGINAL"
            )
            self.assertEqual(
                temporaire.read_bytes(),
                b"NOUVEL_EXPORT"
            )

    def test_publication_reussie(self):
        with tempfile.TemporaryDirectory() as dossier:
            dossier = Path(dossier)
            temporaire = dossier / "temporaire.tiff"
            destination = dossier / "photo.tiff"

            temporaire.write_bytes(b"EXPORT_TEST")

            publish_no_overwrite(temporaire, destination)

            self.assertEqual(
                destination.read_bytes(),
                b"EXPORT_TEST"
            )
            self.assertFalse(temporaire.exists())


if __name__ == "__main__":
    unittest.main()
