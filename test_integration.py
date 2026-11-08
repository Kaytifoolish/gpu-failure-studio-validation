import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
from safety import validate_export, publish_no_overwrite

HERE=Path(__file__).resolve().parent
class TestWorkerIntegration(unittest.TestCase):
    def test_jpeg_to_tiff_and_jpeg(self):
        import tifffile
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            src=d/'source.jpg'
            Image.new('RGB',(160,100),(100,50,20)).save(src)
            before=hashlib.sha256(src.read_bytes()).hexdigest()
            for mode,suffix in [('tiff','.tif'),('jpeg','.jpg')]:
                tmp=d/('temp'+suffix)
                cmd=[sys.executable,str(HERE/'worker.py'),'--source',str(src),'--target',str(tmp),
                     '--mode',mode,'--effect','Scanlines','--strength','0.5','--seed','2026']
                result=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stderr)
                validate_export(tmp,mode)
                dest=d/('final'+suffix)
                publish_no_overwrite(tmp,dest)
                self.assertTrue(dest.exists())
                with self.assertRaises(FileExistsError):
                    tmp.write_bytes(b'other');publish_no_overwrite(tmp,dest)
            self.assertEqual(hashlib.sha256(src.read_bytes()).hexdigest(),before)
if __name__=='__main__':unittest.main()
