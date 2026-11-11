import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np
import tifffile
from PIL import Image, ImageCms
from color_management import srgb_profile_bytes
from safety import validate_export, validate_print_metadata, publish_no_overwrite

HERE = Path(__file__).resolve().parent

def worker(source, target, mode='tiff', dpi=300):
    p = subprocess.run([sys.executable, str(HERE / 'worker.py'), '--source', str(source),
                        '--target', str(target), '--mode', mode, '--effect', 'Scanlines',
                        '--strength', '0', '--seed', '7', '--dpi', str(dpi)],
                       capture_output=True, text=True, cwd=HERE)
    if p.returncode:
        raise AssertionError(p.stderr)
    return json.loads(p.stdout)

class ColorExportTests(unittest.TestCase):
    def test_tagged_16bit_tiff_preserves_pixels_icc_and_dpi(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); src=d/'src.tif'; dest=d/'out.tif'
            pixels=np.arange(6*7*3,dtype=np.uint16).reshape(6,7,3)*251
            icc=srgb_profile_bytes()
            tifffile.imwrite(src,pixels,photometric='rgb',extratags=[(34675,'B',len(icc),icc,False)])
            result=worker(src,dest,dpi=360)
            self.assertEqual(result['icc'],'embedded')
            validate_export(dest,'tiff')
            self.assertTrue(validate_print_metadata(dest,'tiff',360,'embedded'))
            np.testing.assert_array_equal(tifffile.imread(dest),pixels)
            with tifffile.TiffFile(dest) as tf:
                self.assertEqual(bytes(tf.pages[0].tags[34675].value),icc)
    def test_tagged_jpeg_to_tagged_jpeg(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d); src=d/'src.jpg'; dest=d/'out.jpg'
            Image.new('RGB',(18,14),(120,80,40)).save(src,icc_profile=srgb_profile_bytes())
            result=worker(src,dest,mode='jpeg',dpi=300)
            self.assertEqual(result['icc'],'embedded')
            validate_export(dest,'jpeg')
            self.assertTrue(validate_print_metadata(dest,'jpeg',300,'embedded'))
    def test_untagged_tiff_is_not_falsely_tagged(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d); src=d/'src.tif'; dest=d/'out.tif'
            tifffile.imwrite(src,np.zeros((8,9,3),dtype=np.uint16),photometric='rgb')
            result=worker(src,dest)
            self.assertEqual(result['icc'],'unknown')
            self.assertFalse(validate_print_metadata(dest,'tiff',300,'unknown'))
    def test_corrupt_icc_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d); src=d/'src.jpg'; dest=d/'out.jpg'
            Image.new('RGB',(8,8)).save(src,icc_profile=b'bad profile')
            p=subprocess.run([sys.executable,str(HERE/'worker.py'),'--source',str(src),'--target',str(dest),
                '--mode','jpeg','--effect','Scanlines','--strength','0','--seed','1'],capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0)
            self.assertFalse(dest.exists())
    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d); tmp=d/'tmp'; dest=d/'existing'
            tmp.write_bytes(b'new');dest.write_bytes(b'old')
            with self.assertRaises(FileExistsError):
                publish_no_overwrite(tmp,dest)
            self.assertEqual(dest.read_bytes(),b'old')

if __name__=='__main__':unittest.main()
