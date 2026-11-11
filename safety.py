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


def validate_print_metadata(path, mode, expected_dpi, expected_icc=None):
    """Verify stored DPI and ICC against the actual worker result."""
    from color_management import validate_icc
    from print_export import validate_dpi
    validate_dpi(expected_dpi)
    if mode == 'tiff':
        import tifffile
        with tifffile.TiffFile(path) as tf:
            page = tf.pages[0]
            x = page.tags['XResolution'].value
            y = page.tags['YResolution'].value
            unit = page.tags['ResolutionUnit'].value
            if int(unit) != 2 or abs(x[0] / x[1] - expected_dpi) > 0.5 or abs(y[0] / y[1] - expected_dpi) > 0.5:
                raise ValueError('Résolution TIFF incorrecte')
            tag = page.tags.get(34675)
            icc = bytes(tag.value) if tag is not None else None
    elif mode == 'jpeg':
        from PIL import Image
        with Image.open(path) as im:
            dpi = im.info.get('dpi')
            if not dpi or any(abs(x - expected_dpi) > 1 for x in dpi):
                raise ValueError('Résolution JPEG incorrecte')
            icc = im.info.get('icc_profile')
    else:
        raise ValueError('Format inconnu')
    if icc is not None:
        validate_icc(icc)
    if expected_icc == 'embedded' and icc is None:
        raise ValueError('Profil ICC perdu pendant export')
    if expected_icc == 'unknown' and icc is not None:
        raise ValueError('Profil ICC inattendu')
    return bool(icc)
