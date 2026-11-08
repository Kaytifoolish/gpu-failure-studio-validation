import unittest
import numpy as np
from engine import simulate,EFFECTS
class TestEffects(unittest.TestCase):
    def test_all_effects(self):
        source=np.arange(40*60*3,dtype=np.uint16).reshape(40,60,3)
        for effect in EFFECTS:
            with self.subTest(effect=effect):
                out=simulate(source,effect,.6,2026)
                self.assertEqual(out.shape,source.shape)
                self.assertEqual(out.dtype,np.uint16)
                np.testing.assert_array_equal(out,simulate(source,effect,.6,2026))
    def test_zero(self):
        source=np.ones((8,9,3),dtype=np.uint16)
        np.testing.assert_array_equal(source,simulate(source,'Scanlines',0,1))
if __name__=='__main__':unittest.main()
