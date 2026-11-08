"""Small safety primitives, intentionally independent of the GUI."""
import os
import stat
from pathlib import Path

MAX_SOURCE_BYTES = 800 * 1024 * 1024
SUPPORTED = {'.dng','.nef','.arw','.cr2','.cr3','.raf','.rw2','.orf','.pef','.srw','.jpg','.jpeg','.png','.tif','.tiff'}

def check_source(path):
    p = Path(path).expanduser().absolute()
    if p.is_symlink():
        raise ValueError('Les liens symboliques sont interdits')
    st = p.stat()
    if not stat.S_ISREG(st.st_mode):
        raise ValueError('Fichier ordinaire requis')
    if not 0 < st.st_size <= MAX_SOURCE_BYTES:
        raise ValueError('Fichier vide ou supérieur à 800 Mio')
    if p.suffix.lower() not in SUPPORTED:
        raise ValueError('Extension non prise en charge')
    return p.resolve()

def publish_no_overwrite(temp, dest):
    """Same-volume hard-link publication. Fail closed if unsupported."""
    temp, dest = Path(temp), Path(dest)
    if temp.parent.resolve() != dest.parent.resolve():
        raise ValueError('Export temporaire et final doivent partager le dossier')
    os.link(temp, dest, follow_symlinks=False)
    temp.unlink()

def validate_export(path, mode, max_pixels=36_000_000):
    if mode == 'tiff':
        import numpy as np
        import tifffile
        with tifffile.TiffFile(path) as t:
            if len(t.pages) != 1:
                raise ValueError('TIFF multipage non autorisé')
            page = t.pages[0]
            shape = page.shape
            if page.dtype != np.dtype('uint16') or len(shape) != 3 or shape[2] != 3:
                raise ValueError('TIFF non RGB 16 bits')
            if shape[0] * shape[1] > max_pixels:
                raise ValueError('TIFF trop grand')
    elif mode == 'jpeg':
        from PIL import Image
        with Image.open(path) as im:
            if im.format != 'JPEG' or im.mode != 'RGB':
                raise ValueError('JPEG RGB attendu')
            if im.width * im.height > max_pixels:
                raise ValueError('JPEG trop grand')
            im.verify()
    else:
        raise ValueError('Format inconnu')
