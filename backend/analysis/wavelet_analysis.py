import cv2
import numpy as np
import pywt

HH_SUSPICION_THRESHOLD = 0.12


def analyze_wavelet(
    image_path: str,
    output_path: str,
):
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

    if image is None:
        raise ValueError("Unable to read image")

    # Downscale for faster DWT on large images
    h, w = image.shape
    if max(h, w) > 1600:
        scale = 1600 / max(h, w)
        image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    image = image.astype(np.float32)

    coeffs = pywt.dwt2(image, "haar")
    approximation, (horizontal, vertical, diagonal) = coeffs

    lh_energy = float(np.mean(np.abs(horizontal)))
    hl_energy = float(np.mean(np.abs(vertical)))
    base_energy = lh_energy + hl_energy

    # Adaptive HH — only when LH/HL suggest suspicious high-frequency content
    if base_energy / 255.0 > HH_SUSPICION_THRESHOLD:
        high_frequency = np.abs(horizontal) + np.abs(vertical) + np.abs(diagonal)
    else:
        high_frequency = np.abs(horizontal) + np.abs(vertical)

    high_frequency_energy = float(np.mean(high_frequency))
    score = min(high_frequency_energy / 255.0, 1.0)

    wavelet_map = np.abs(high_frequency)
    wavelet_map = cv2.normalize(wavelet_map, None, 0, 255, cv2.NORM_MINMAX)
    wavelet_map = wavelet_map.astype(np.uint8)
    wavelet_map = cv2.resize(wavelet_map, (w, h))

    cv2.imwrite(output_path, wavelet_map)

    return {
        "high_frequency_energy": high_frequency_energy,
        "wavelet_score": float(score),
        "hh_included": base_energy / 255.0 > HH_SUSPICION_THRESHOLD,
        "lh_energy": lh_energy,
        "hl_energy": hl_energy,
    }
