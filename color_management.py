"""Conservative ICC handling: never assign a guessed source profile."""
from io import BytesIO
from PIL import ImageCms

MAX_ICC_BYTES = 4 * 1024 * 1024

def validate_icc(data):
    if data is None:
        return None
    if not isinstance(data, bytes) or not 128 <= len(data) <= MAX_ICC_BYTES:
        raise ValueError('Profil ICC absent, invalide ou trop volumineux')
    if data[36:40] != b'acsp':
        raise ValueError('Signature ICC invalide')
    try:
        profile = ImageCms.ImageCmsProfile(BytesIO(data))
        # RGB-only color data. Gray/CMYK profiles cannot describe RGB output.
        if data[16:20] != b'RGB ':
            raise ValueError('Le profil ICC source ne décrit pas du RGB')
        return profile
    except (OSError, SyntaxError, ValueError) as exc:
        raise ValueError(f'Profil ICC illisible ou incompatible: {exc}') from exc

def srgb_profile_bytes():
    return ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()

def to_srgb(image, source_icc):
    """Convert 8-bit Pillow RGB pixels from embedded ICC to tagged sRGB."""
    if source_icc is None:
        return image.convert('RGB'), None
    profile = validate_icc(source_icc)
    output = ImageCms.profileToProfile(image.convert('RGB'), profile,
                                       ImageCms.createProfile('sRGB'),
                                       outputMode='RGB')
    return output, srgb_profile_bytes()
