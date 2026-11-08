"""Subprocess-only image parser and renderer. Not a macOS sandbox."""
import argparse,json,sys,resource
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps
from engine import simulate,EFFECTS
RAW={'.dng','.nef','.arw','.cr2','.cr3','.raf','.rw2','.orf','.pef','.srw'}
MAX_PIXELS=36_000_000
Image.MAX_IMAGE_PIXELS=MAX_PIXELS

def load(path,preview=False):
    if path.suffix.lower() in RAW:
        import rawpy
        with rawpy.imread(str(path)) as raw:
            # RAW geometry is checked before expensive demosaic, where available.
            sizes=raw.sizes
            if sizes.width*sizes.height>MAX_PIXELS:raise ValueError('RAW exceeds 36 MP limit')
            # half_size reduces decoding cost for preview, not used for export
            a=raw.postprocess(output_bps=16,use_camera_wb=True,no_auto_bright=True,
                output_color=rawpy.ColorSpace.sRGB,half_size=preview)
    else:
        with Image.open(path) as im:
            if im.width*im.height>MAX_PIXELS:raise ValueError('Image exceeds 36 MP limit')
            im=ImageOps.exif_transpose(im)
            if preview:
                im.thumbnail((1200,800))
            # TIFF 16-bit RGB is best handled by tifffile, Pillow RGB conversion is 8-bit.
            if not preview and path.suffix.lower() in ('.tif','.tiff'):
                import tifffile
                a=tifffile.imread(str(path))
                if a.ndim!=3 or a.shape[2]!=3:raise ValueError('Only RGB TIFF supported')
                if a.dtype==np.uint8:a=a.astype(np.uint16)*257
                elif a.dtype!=np.uint16:raise ValueError('TIFF must be 8/16-bit RGB')
            else:
                a=np.asarray(im.convert('RGB'),dtype=np.uint16)*257
    if a.ndim!=3 or a.shape[2]!=3 or a.dtype!=np.uint16 or a.shape[0]*a.shape[1]>MAX_PIXELS:
        raise ValueError('Invalid RGB image')
    return a

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
    p.add_argument('--seed',type=int,required=True);a=p.parse_args()
    if not 0<=a.strength<=1 or not 0<=a.seed<2**63:raise ValueError('Invalid parameters')
    image=load(Path(a.source),preview=a.mode=='preview')
    if a.mode=='preview' and (image.shape[1]>1200 or image.shape[0]>800):
        im=Image.fromarray((image//257).astype('uint8'),'RGB');im.thumbnail((1200,800))
        image=np.asarray(im,dtype=np.uint16)*257
    out=simulate(image,a.effect,a.strength,a.seed)
    if a.mode=='tiff':
        import tifffile
        tifffile.imwrite(a.target,out,photometric='rgb',compression=None)
    else:
        Image.fromarray((out//257).astype('uint8'),'RGB').save(a.target,format='PNG' if a.mode=='preview' else 'JPEG',**({} if a.mode=='preview' else {'quality':95,'subsampling':0}))
    print(json.dumps({'width':int(out.shape[1]),'height':int(out.shape[0]),'mode':a.mode}))
if __name__=='__main__':
    try:main()
    except Exception as e:print(f'{type(e).__name__}: {e}',file=sys.stderr);sys.exit(1)
