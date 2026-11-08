
import gc
import hashlib
import json
import os
import platform
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import psutil
from PIL import Image

# Le moteur se trouve a la racine du depot.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import simulate


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    process = psutil.Process(os.getpid())
    results = []
    sizes = [(800, 600), (2000, 1500), (4000, 3000)]

    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)

        for width, height in sizes:
            # Image synthetique RGB 16 bits.
            image = np.zeros((height, width, 3), dtype=np.uint16)
            image[:, :, 0] = 15000
            image[:, :, 1] = 30000
            image[:, :, 2] = 45000

            # Fichier source synthetique, sans photo personnelle.
            source = folder / f"source_{width}x{height}.png"
            preview = (image // 257).astype(np.uint8)
            Image.fromarray(preview).save(source)
            del preview

            before = sha256(source)
            start = time.monotonic()

            output = simulate(
                image, "Bit flips", 0.3, 12345
            )

            duration = time.monotonic() - start
            after = sha256(source)

            if before != after:
                raise AssertionError("Le fichier source a ete modifie")

            if output.shape != image.shape:
                raise AssertionError("Dimensions incorrectes")

            if output.dtype != np.uint16:
                raise AssertionError("Format 16 bits incorrect")

            results.append({
                "dimensions": f"{width}x{height}",
                "megapixels": width * height / 1_000_000,
                "duration_seconds": round(duration, 3),
                "rss_mib_after": round(
                    process.memory_info().rss / 1024**2, 1
                ),
                "source_unchanged": True,
                "output_uint16": True,
            })

            del image, output
            gc.collect()

    report = {
        "machine": platform.machine(),
        "macos": platform.mac_ver()[0],
        "python": platform.python_version(),
        "tests": results,
        "limitations": [
            "RSS mesure apres traitement, pas le pic garanti",
            "Aucun fichier RAW reel",
            "Aucun test d'interface graphique",
            "Aucune sandbox macOS",
        ],
    }

    Path("reports").mkdir(exist_ok=True)
    Path("reports/phase2.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

