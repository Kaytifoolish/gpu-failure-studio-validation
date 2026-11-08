import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
from safety import check_source, publish_no_overwrite, validate_export

class TestSafety(unittest.TestCase):
    def test_original_integrity_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            source=d/'source.jpg'
            Image.new('RGB',(120,80),(20,40,60)).save(source)
            before=hashlib.sha256(source.read_bytes()).hexdigest()
            self.assertEqual(check_source(source),source.resolve())
            temp=d/'.output.tmp';temp.write_bytes(b'output bytes')
            dest=d/'output.tif'
            publish_no_overwrite(temp,dest)
            self.assertEqual(dest.read_bytes(),b'output bytes')
            second=d/'.output2.tmp';second.write_bytes(b'different')
            with self.assertRaises(FileExistsError):
                publish_no_overwrite(second,dest)
            self.assertEqual(dest.read_bytes(),b'output bytes')
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),before)
    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            original=d/'original.jpg';original.write_bytes(b'data')
            link=d/'link.jpg';link.symlink_to(original)
            with self.assertRaises(ValueError):check_source(link)
    def test_export_formats(self):
        import tifffile
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            tiff=d/'a.tif';jpeg=d/'b.jpg'
            a=np.full((100,150,3),40000,dtype=np.uint16)
            tifffile.imwrite(tiff,a,photometric='rgb')
            Image.fromarray((a//257).astype('uint8'),'RGB').save(jpeg,quality=95)
            validate_export(tiff,'tiff');validate_export(jpeg,'jpeg')
            with tifffile.TiffFile(tiff) as t:self.assertEqual(t.pages[0].dtype,np.dtype('uint16'))

if __name__=='__main__':unittest.main()
