import os
import json
import cv2
import numpy as np
from pathlib import Path

def analyze_signatures(image_path: str, output_dir: str = "analysis"):
    """
    Detects signature regions and classifies them into forensic categories:
    genuine, copied, pasted, transparent PNG, reused signature, 
    pressure inconsistency, edge inconsistency.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Load image (with unchanged IMREAD_UNCHANGED to check for alpha channel)
    original_unchanged = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    original_bgr = cv2.imread(image_path, cv2.IMREAD_COLOR)
    
    if original_bgr is None:
        return []
        
    h, w = original_bgr.shape[:2]
    has_alpha = (
        original_unchanged is not None
        and len(original_unchanged.shape) == 3
        and original_unchanged.shape[-1] == 4
    )
    
    # Calculate global document noise variance
    gray_full = cv2.cvtColor(original_bgr, cv2.COLOR_BGR2GRAY)
    doc_laplacian = cv2.Laplacian(gray_full, cv2.CV_64F)
    global_noise_var = doc_laplacian.var()
    
    findings = []
    
    # 2. Detect signature regions (bottom third heuristic for standalone script)
    # Convert to binary
    roi_bottom = gray_full[int(h * 0.60):, :]
    _, thresh = cv2.threshold(roi_bottom, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Dilate to connect cursive strokes
    kernel = np.ones((5, 15), np.uint8)
    dilated = cv2.dilate(thresh, kernel, iterations=2)
    
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    regions = []
    for cnt in sorted(contours, key=cv2.contourArea, reverse=True)[:3]:
        area = cv2.contourArea(cnt)
        if area < 800 or area > w * h * 0.15:
            continue
            
        x, y, bw, bh = cv2.boundingRect(cnt)
        y += int(h * 0.60) # Offset back to full image coordinates
        regions.append([x, y, bw, bh])
        
    # 3. Classify each region
    for idx, (x, y, bw, bh) in enumerate(regions):
        # Extract ROI
        roi_bgr = original_bgr[y:y+bh, x:x+bw]
        if roi_bgr.size == 0:
            continue
            
        roi_gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
        
        # Calculate local noise variance
        roi_laplacian = cv2.Laplacian(roi_gray, cv2.CV_64F)
        local_noise_var = roi_laplacian.var()
        
        # Calculate pressure (intensity standard deviation of dark pixels)
        dark_pixels = roi_gray[roi_gray < 200]
        pressure_var = float(np.std(dark_pixels)) if len(dark_pixels) > 10 else 0.0
        
        # Edge discontinuity
        edges = cv2.Canny(roi_gray, 40, 120)
        fragments = cv2.countNonZero(edges)
        discontinuity = min(1.0, fragments / max(1, bw * bh) * 8.0)
        
        # Classification Logic
        classification = "genuine"
        confidence = 0.90
        reason = "Natural ink pressure and edge continuity detected."
        
        if has_alpha and original_unchanged is not None:
            # Check if this specific ROI has transparent pixels
            roi_unchanged = original_unchanged[y:y+bh, x:x+bw]
            alpha_channel = roi_unchanged[:, :, 3]
            if np.any(alpha_channel < 255):
                classification = "transparent PNG"
                confidence = 0.99
                reason = "Alpha channel transparency detected in signature bounding box."
        
        if classification == "genuine":
            # Noise variance mismatch indicating pasting
            noise_ratio = local_noise_var / max(1.0, global_noise_var)
            if noise_ratio < 0.3 or noise_ratio > 3.0:
                classification = "pasted"
                confidence = 0.95
                reason = f"Severe background noise mismatch (ROI variance: {local_noise_var:.1f} vs Global: {global_noise_var:.1f})."
            
            # Edge inconsistency
            elif discontinuity > 0.8:
                classification = "edge inconsistency"
                confidence = 0.88
                reason = "High edge fragmentation indicating traced or synthetic strokes."
                
            # Pressure inconsistency
            elif pressure_var < 10.0 and len(dark_pixels) > 50:
                classification = "pressure inconsistency"
                confidence = 0.85
                reason = "Unnaturally uniform pixel intensity lacking natural pen pressure variance."
                
            # Copied/Reused (Proxy check: perfect monochrome background)
            elif np.var(roi_gray[roi_gray > 200]) < 1.0:
                classification = "copied"
                confidence = 0.82
                reason = "Perfectly uniform background indicative of a digital copy."

        findings.append({
            "bbox": [int(x), int(y), int(bw), int(bh)],
            "confidence": round(confidence, 4),
            "classification": classification,
            "reason": reason
        })
        
    output_file = os.path.join(output_dir, "signature_analysis.json")
    with open(output_file, "w") as f:
        json.dump(findings, f, indent=2)
        
    return findings

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        analyze_signatures(sys.argv[1])
