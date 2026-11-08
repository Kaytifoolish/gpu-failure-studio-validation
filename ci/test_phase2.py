
import hashlib
import json
import os
import platform
import tempfile
import time
from pathlib import Path

import numpy as np
import psutil
from PIL import Image

from engine import apply_effect


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run():
    results = []
    process = psutil.Process(os.getpid())

    # Tailles progressives, limitees pour le runner CI.
    sizes = [(800, 600), (2000, 1500), (4000, 3000)]

    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)

        for width, height in sizes:
            pixels = width * height
            if pixels > 12_000_000:
                raise RuntimeError("Image trop grande pour ce test")

            # Image synthetique reproductible.
            image_array = np.zeros(
                (height, width, 3), dtype=np.uint8
            )
            image_array[:, :, 0] = 100
            image_array[:, :, 1] = 150
            image_array[:, :, 2] = 200

            source = folder / f"source_{width}x{height}.png"
            Image.fromarray(image_array).save(source)

            before = sha256(source)
            start = time.monotonic()

            # Test du moteur avec une image synthetique.
            output = apply_effect(
                image_array.copy(), "bit_flip", 0.3, 12345
            )

            elapsed = time.monotonic() - start
            after = sha256(source)

            if before != after:
                raise AssertionError("Source modifiee")

            if output.shape != image_array.shape:
                raise AssertionError("Dimensions incorrectes")

            results.append({
                "dimensions": f"{width}x{height}",
                "megapixels": pixels / 1_000_000,
                "seconds": round(elapsed, 3),
                "rss_mb_after": round(
                    process.memory_info().rss / 1024**2, 1
                ),
                "source_unchanged": True,
            })

            del image_array, output

    report = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "results": results,
        "note": (
            "RSS mesure apres traitement, "
            "pas le pic de memoire garanti."
        ),
    }

    Path("reports").mkdir(exist_ok=True)
    Path("reports/phase2.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    run()
