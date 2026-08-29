import os
import json
import cv2
import numpy as np
from backend.analysis.localization.providers.registry import get_active_provider


def _merge_overlapping_boxes(boxes, iou_thresh=0.3):
    if not boxes:
        return []
    merged = []
    used = [False] * len(boxes)
    for i in range(len(boxes)):
        if used[i]:
            continue
        b1 = boxes[i]
        used[i] = True
        for j in range(i + 1, len(boxes)):
            if used[j]:
                continue
            b2 = boxes[j]
            x1, y1, w1, h1 = b1["bbox"]
            x2, y2, w2, h2 = b2["bbox"]

            ix1, iy1 = max(x1, x2), max(y1, y2)
            ix2, iy2 = min(x1 + w1, x2 + w2), min(y1 + h1, y2 + h2)
            inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
            if inter > 0:
                union = w1 * h1 + w2 * h2 - inter
                iou = inter / union if union > 0 else 0
                if iou >= iou_thresh:
                    used[j] = True
                    nx1 = min(x1, x2)
                    ny1 = min(y1, y2)
                    nx2 = max(x1 + w1, x2 + w2)
                    ny2 = max(y1 + h1, y2 + h2)
                    b1["bbox"] = [nx1, ny1, nx2 - nx1, ny2 - ny1]
                    b1["confidence"] = max(b1["confidence"], b2["confidence"])
        merged.append(b1)
    
    # Clean up and normalize
    for idx, item in enumerate(merged):
        item["id"] = f"loc-{idx + 1}"
    
    return merged


def generate_pixel_localization(image_path: str, output_dir: str = "analysis"):
    os.makedirs(output_dir, exist_ok=True)
    provider = get_active_provider()
    
    try:
        out = provider.segment(image_path, output_dir)
        heatmap = out.confidence_heatmap
        mask = out.binary_mask
        anomaly_type = "splicing" if "trufor" in provider.name.lower() else "forgery"
    except Exception as e:
        print(f"Error running segmentation provider: {e}")
        return []

    # Ensure masks are sized properly
    original = cv2.imread(image_path)
    if original is not None:
        h, w = original.shape[:2]
        if heatmap.shape != (h, w):
            heatmap = cv2.resize(heatmap, (w, h))
        if mask.shape != (h, w):
            mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)

    # 2. Generate anomaly mask, confidence mask, binary tamper mask
    heatmap_u8 = (np.clip(heatmap, 0, 1) * 255).astype(np.uint8)
    anomaly_mask = cv2.applyColorMap(heatmap_u8, cv2.COLORMAP_JET)
    
    cv2.imwrite(os.path.join(output_dir, "anomaly_mask.png"), anomaly_mask)
    cv2.imwrite(os.path.join(output_dir, "confidence_mask.png"), heatmap_u8)
    cv2.imwrite(os.path.join(output_dir, "binary_tamper_mask.png"), mask)

    # 3. Convert masks into bounding boxes
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    findings = []
    
    for cnt in contours:
        if cv2.contourArea(cnt) < 50:
            continue
        x, y, bw, bh = cv2.boundingRect(cnt)
        roi = heatmap[y:y+bh, x:x+bw]
        conf = float(roi.mean()) if roi.size > 0 else 0.0
        
        findings.append({
            "id": "", # Will be set during merge
            "page": 1,
            "bbox": [int(x), int(y), int(bw), int(bh)],
            "confidence": round(conf, 4),
            "anomaly_type": anomaly_type
        })
        
    # 4. Merge nearby detections
    merged_findings = _merge_overlapping_boxes(findings)

    # 5. Save results
    json_path = os.path.join(output_dir, "localization.json")
    with open(json_path, "w") as f:
        json.dump(merged_findings, f, indent=2)
        
    return merged_findings
