"""Subprocess-only image parser and renderer. Not a macOS sandbox."""
import argparse,json,sys,resource
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps
from engine import simulate,EFFECTS
from print_export import validate_dpi, print_report
RAW={'.dng','.nef','.arw','.cr2','.cr3','.raf','.rw2','.orf','.pef','.srw'}
MAX_PIXELS=36_000_000
Image.MAX_IMAGE_PIXELS=MAX_PIXELS

def load(path, preview=False):
    """Return RGB uint16 pixels, valid ICC bytes (if known), and color warning."""
    from color_management import validate_icc, srgb_profile_bytes, to_srgb
    suffix = path.suffix.lower()
    icc = None
    if suffix in RAW:
        import rawpy
        with rawpy.imread(str(path)) as raw:
            sizes = raw.sizes
            if sizes.width * sizes.height > MAX_PIXELS:
                raise ValueError('RAW exceeds 36 MP limit')
            pixels = raw.postprocess(output_bps=16, use_camera_wb=True,
                                     no_auto_bright=True,
                                     output_color=rawpy.ColorSpace.sRGB,
                                     half_size=preview)
        icc = srgb_profile_bytes()  # rawpy explicitly produced sRGB pixel values
    elif suffix in ('.tif', '.tiff') and not preview:
        import tifffile
        with tifffile.TiffFile(str(path)) as tf:
            if len(tf.pages) != 1:
                raise ValueError('Only single-page TIFF supported')
            page = tf.pages[0]
            if page.shape[0] * page.shape[1] > MAX_PIXELS:
                raise ValueError('Image exceeds 36 MP limit')
            orientation = page.tags.get('Orientation')
            if orientation is not None and int(orientation.value) != 1:
                raise ValueError('TIFF avec orientation EXIF non standard: normaliser avant import')
            tag = page.tags.get(34675)
            if tag is not None:
                icc = bytes(tag.value)
                validate_icc(icc)
            pixels = page.asarray()
        if pixels.ndim != 3 or pixels.shape[2] != 3:
            raise ValueError('Only RGB TIFF supported')
        if pixels.dtype == np.uint8:
            pixels = pixels.astype(np.uint16) * 257
        elif pixels.dtype != np.uint16:
            raise ValueError('TIFF must be 8/16-bit RGB')
    else:
        with Image.open(path) as original:
            if original.width * original.height > MAX_PIXELS:
                raise ValueError('Image exceeds 36 MP limit')
            source_icc = original.info.get('icc_profile')
            if source_icc is not None:
                validate_icc(source_icc)
            im = ImageOps.exif_transpose(original)
            if preview:
                im.thumbnail((1200, 800))
            converted, icc = to_srgb(im, source_icc)
            pixels = np.asarray(converted, dtype=np.uint16) * 257
    if (pixels.ndim != 3 or pixels.shape[2] != 3 or
            pixels.dtype != np.uint16 or
            pixels.shape[0] * pixels.shape[1] > MAX_PIXELS):
        raise ValueError('Invalid RGB image')
    return pixels, icc

def limit_worker_resources():
    # Kernel limits, not a sandbox. RLIMIT_AS is not reliable across macOS builds.
    for which, limit in ((resource.RLIMIT_CORE,0),(resource.RLIMIT_FSIZE,1024*1024*1024),
                         (resource.RLIMIT_CPU,210)):
        try:resource.setrlimit(which,(limit,limit))
        except (ValueError,OSError):pass

def main():
    limit_worker_resources()
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--target',required=True)
    p.add_argument('--mode',choices=['preview','tiff','jpeg'],required=True)
    p.add_argument('--effect',choices=EFFECTS,required=True);p.add_argument('--strength',type=float,required=True)
    p.add_argument('--seed',type=int,required=True);p.add_argument('--dpi',type=int,default=300);a=p.parse_args()
    if not 0<=a.strength<=1 or not 0<=a.seed<2**63:raise ValueError('Invalid parameters')
    validate_dpi(a.dpi)
    image, icc = load(Path(a.source),preview=a.mode=='preview')
    if a.mode=='preview' and (image.shape[1]>1200 or image.shape[0]>800):
        im=Image.fromarray((image//257).astype('uint8'),'RGB');im.thumbnail((1200,800))
        image=np.asarray(im,dtype=np.uint16)*257
    out=simulate(image,a.effect,a.strength,a.seed)
    if a.mode=='tiff':
        import tifffile
        tifffile.imwrite(a.target,out,photometric='rgb',compression=None,resolution=(a.dpi,a.dpi),resolutionunit='INCH', extratags=([(34675,'B',len(icc),icc,False)] if icc else []))
    else:
        Image.fromarray((out//257).astype('uint8'),'RGB').save(a.target,format='PNG' if a.mode=='preview' else 'JPEG',**({} if a.mode=='preview' else {'quality':95,'subsampling':0,'dpi':(a.dpi,a.dpi),**({'icc_profile':icc} if icc else {})}))
    print(json.dumps({'width':int(out.shape[1]),'height':int(out.shape[0]),'mode':a.mode, 'print':print_report(int(out.shape[1]),int(out.shape[0]),a.dpi), 'icc':('embedded' if icc else 'unknown')}))
if __name__=='__main__':
    try:main()
    except Exception as e:print(f'{type(e).__name__}: {e}',file=sys.stderr);sys.exit(1)
