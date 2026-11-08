

import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import numpy as np
import psutil
import tifffile
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "worker.py"
REPORT = ROOT / "reports" / "phase3.json"


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run_worker(source, target, mode, timeout=90):
    command = [
        sys.executable, str(WORKER),
        "--source", str(source),
        "--target", str(target),
        "--mode", mode,
        "--effect", "Bit flips",
        "--strength", "0.3",
        "--seed", "12345",
    ]

    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    peak_rss = 0
    stop = threading.Event()

    def monitor():
        nonlocal peak_rss
        try:
            child = psutil.Process(proc.pid)
            while not stop.is_set():
                try:
                    rss = child.memory_info().rss
                    peak_rss = max(peak_rss, rss)
                except psutil.Error:
                    break
                stop.wait(0.02)
        except psutil.Error:
            pass

    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    started = time.monotonic()

    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        raise AssertionError("Worker timeout")
    finally:
        stop.set()
        thread.join(timeout=2)

    duration = time.monotonic() - started

    if proc.returncode != 0:
        raise AssertionError(
            f"Worker failed: {stderr[-2000:]}"
        )

    return {
        "duration_seconds": round(duration, 3),
        "sampled_peak_rss_mib": round(
            peak_rss / (1024 ** 2), 1
        ),
        "stdout": stdout.strip(),
    }


def main():
    results = []

    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)

        # Image synthetique de 3000 x 2000 pixels.
        height, width = 2000, 3000
        image = np.empty(
            (height, width, 3), dtype=np.uint16
        )
        image[:, :, 0] = 15000
        image[:, :, 1] = 30000
        image[:, :, 2] = 45000

        source = folder / "source.tiff"
        tifffile.imwrite(
            source, image, photometric="rgb"
        )
        del image

        original_hash = digest(source)

        for mode, extension in [
            ("tiff", ".tiff"),
            ("jpeg", ".jpg"),
        ]:
            target = folder / ("output_" + mode + extension)

            metrics = run_worker(source, target, mode)

            if not target.is_file():
                raise AssertionError("Missing output")

            if digest(source) != original_hash:
                raise AssertionError("Source modified")

            if mode == "tiff":
                exported = tifffile.imread(target)
                if exported.shape != (height, width, 3):
                    raise AssertionError("TIFF dimensions")
                if exported.dtype != np.uint16:
                    raise AssertionError("TIFF is not uint16")
            else:
                with Image.open(target) as exported:
                    exported.verify()
                with Image.open(target) as exported:
                    if exported.format != "JPEG":
                        raise AssertionError("Not JPEG")
                    if exported.size != (width, height):
                        raise AssertionError("JPEG dimensions")

            results.append({
                "mode": mode,
                "dimensions": f"{width}x{height}",
                "source_unchanged": True,
                "output_valid": True,
                **metrics,
            })

        # Interruption d'un processus de test.
        # Ne teste pas encore tous les cas de fermeture de l'app.
        sleeper = subprocess.Popen([
            sys.executable, "-c",
            "import time; time.sleep(30)"
        ])
        sleeper.terminate()
        try:
            sleeper.wait(timeout=5)
        except subprocess.TimeoutExpired:
            sleeper.kill()
            sleeper.wait(timeout=5)
            raise AssertionError("Termination timeout")

        if sleeper.poll() is None:
            raise AssertionError("Process still running")

        interruption = {
            "synthetic_process_terminated": True,
            "worker_interruption_tested": False,
        }

    report = {
        "architecture": platform.machine(),
        "macos": platform.mac_ver()[0],
        "python": platform.python_version(),
        "exports": results,
        "interruption": interruption,
        "limitations": [
            "RSS peak is sampled, not an absolute maximum",
            "Interruption uses a synthetic sleeper, not the worker",
            "No real RAW files",
            "No GUI test",
            "No macOS sandbox",
            "No overwrite or atomic publication test",
        ],
    }

    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
