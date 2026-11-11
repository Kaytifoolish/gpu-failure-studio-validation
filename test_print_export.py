import tempfile, unittest, subprocess, sys
from pathlib import Path
import numpy as np
import tifffile
from PIL import Image
from print_export import validate_dpi,print_report

class PrintTests(unittest.TestCase):
 def test_dpi_bounds(self):
  for x in (0, 71, 1201, True, 300.0):
   with self.assertRaises(ValueError):validate_dpi(x)
  self.assertEqual(validate_dpi(300),300)
 def test_a3_report(self):
  self.assertFalse(print_report(1204,831,300)['a3_enough_pixels'])
  self.assertTrue(print_report(5000,3600,300)['a3_enough_pixels'])
 def test_worker_tiff_jpeg_dpi_and_pixels(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);src=d/'input.tif';tgt=d/'output.tif';jpg=d/'output.jpg'
   pixels=np.arange(36*3,dtype=np.uint16).reshape(6,6,3)*300
   tifffile.imwrite(src,pixels,photometric='rgb')
   for mode,dest in [('tiff',tgt),('jpeg',jpg)]:
    cp=subprocess.run([sys.executable,'worker.py','--source',str(src),'--target',str(dest),'--mode',mode,'--effect','Scanlines','--strength','0','--seed','2026','--dpi','360'],capture_output=True,text=True)
    self.assertEqual(cp.returncode,0,cp.stderr)
   with tifffile.TiffFile(tgt) as tf:
    self.assertEqual(tf.pages[0].dtype,np.dtype('uint16'))
    self.assertAlmostEqual(tf.pages[0].tags['XResolution'].value[0]/tf.pages[0].tags['XResolution'].value[1],360)
   np.testing.assert_array_equal(tifffile.imread(tgt),pixels)
   with Image.open(jpg) as im:
    self.assertAlmostEqual(im.info['dpi'][0],360,delta=1)
    self.assertEqual(im.size,(6,6))
 def test_bad_dpi_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);src=d/'in.tif';tgt=d/'out.tif'
   tifffile.imwrite(src,np.zeros((4,4,3),dtype=np.uint16),photometric='rgb')
   cp=subprocess.run([sys.executable,'worker.py','--source',str(src),'--target',str(tgt),'--mode','tiff','--effect','Scanlines','--strength','0','--seed','1','--dpi','9999'],capture_output=True,text=True)
   self.assertNotEqual(cp.returncode,0)
   self.assertFalse(tgt.exists())
if __name__=='__main__':unittest.main()
