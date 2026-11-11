"""Conservative print-export metadata and physical-size checks.

DPI metadata does not resample pixels. No ICC conversion is performed.
"""
import math

A3_MM = (297.0, 420.0)

def validate_dpi(dpi):
    if isinstance(dpi, bool) or not isinstance(dpi, int) or not 72 <= dpi <= 1200:
        raise ValueError('Résolution d’impression invalide (72 à 1200 ppp)')
    return dpi

def print_report(width, height, dpi=300):
    validate_dpi(dpi)
    if not (isinstance(width, int) and isinstance(height, int) and width > 0 and height > 0):
        raise ValueError('Dimensions de l’image invalides')
    # Orientation-neutral comparison: A3 without cropping or margins requires matching ratio.
    short, long = sorted((width, height))
    needed_short = math.ceil(A3_MM[0] / 25.4 * dpi)
    needed_long = math.ceil(A3_MM[1] / 25.4 * dpi)
    return {
        'dpi': dpi, 'width': width, 'height': height,
        'width_cm_at_dpi': round(width * 2.54 / dpi, 2),
        'height_cm_at_dpi': round(height * 2.54 / dpi, 2),
        'a3_min_pixels': [needed_short, needed_long],
        'a3_enough_pixels': short >= needed_short and long >= needed_long,
        'a3_ratio_matches': abs(short / long - A3_MM[0] / A3_MM[1]) < 0.005,
    }
