import os
import json
import uuid

def compute_iou(boxA, boxB):
    # Determine the (x, y)-coordinates of the intersection rectangle
    xA = max(boxA["x"], boxB["x"])
    yA = max(boxA["y"], boxB["y"])
    xB = min(boxA["x"] + boxA["width"], boxB["x"] + boxB["width"])
    yB = min(boxA["y"] + boxA["height"], boxB["y"] + boxB["height"])

    # Compute the area of intersection
    interArea = max(0, xB - xA) * max(0, yB - yA)
    if interArea == 0:
        return 0.0

    # Compute the area of both rectangles
    boxAArea = boxA["width"] * boxA["height"]
    boxBArea = boxB["width"] * boxB["height"]

    # Compute IoU
    iou = interArea / float(boxAArea + boxBArea - interArea)
    return iou

SEVERITY_RANKS = {
    "Critical": 4,
    "High": 3,
    "Medium": 2,
    "Low": 1,
    "Info": 0
}

def map_severity(confidence, anomaly_type):
    anomaly = anomaly_type.lower()
    if "paste" in anomaly or "clone" in anomaly or "transparent" in anomaly or "copy-move" in anomaly:
        return "Critical"
    if "signature" in anomaly or "deepfake" in anomaly:
        return "High"
    if "price" in anomaly or "date" in anomaly or "name" in anomaly:
        return "High" if confidence > 0.8 else "Medium"
    if confidence > 0.9:
        return "High"
    if confidence > 0.7:
        return "Medium"
    return "Low"

def get_recommendation(anomaly_type):
    anomaly = anomaly_type.lower()
    if "paste" in anomaly or "transparent" in anomaly:
        return "Verify source of pasted element and cross-check origin documents."
    if "copy-move" in anomaly or "clone" in anomaly:
        return "Review identical duplicated regions for intentional obfuscation."
    if "price" in anomaly or "total" in anomaly:
        return "Cross-reference invoice amounts with corresponding bank/ledger transactions."
    if "date" in anomaly:
        return "Verify transaction timestamps against authorized records."
    if "signature" in anomaly:
        return "Require in-person authentication or biometric verification of signature."
    return "Flag document for manual compliance review."

def load_json(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def normalize_bbox(bbox):
    # Convert array [x, y, w, h] to dict if needed, or handle dicts
    if isinstance(bbox, list) and len(bbox) >= 4:
        return {"x": float(bbox[0]), "y": float(bbox[1]), "width": float(bbox[2]), "height": float(bbox[3])}
    if isinstance(bbox, dict):
        if "width" in bbox and "height" in bbox:
            return {"x": float(bbox.get("x", 0)), "y": float(bbox.get("y", 0)), "width": float(bbox.get("width", 0)), "height": float(bbox.get("height", 0))}
        if "w" in bbox and "h" in bbox:
            return {"x": float(bbox.get("x", 0)), "y": float(bbox.get("y", 0)), "width": float(bbox.get("w", 0)), "height": float(bbox.get("h", 0))}
    return {"x": 0.0, "y": 0.0, "width": 0.0, "height": 0.0}

def generate_forensic_dossier(analysis_dir="analysis"):
    dossier = []
    
    # 1. Load outputs
    loc_data = load_json(os.path.join(analysis_dir, "localization.json"))
    text_data = load_json(os.path.join(analysis_dir, "text_forensics.json"))
    sig_data = load_json(os.path.join(analysis_dir, "signature_analysis.json"))
    copymove_data = load_json(os.path.join(analysis_dir, "copymove.json"))
    
    # 2. Normalize Localization
    if isinstance(loc_data, list):
        for item in loc_data:
            anomaly_type = item.get("anomaly_type", "Pixel Anomaly")
            conf = float(item.get("confidence", 0.5))
            dossier.append({
                "id": str(uuid.uuid4())[:8],
                "page": item.get("page", 1),
                "label": anomaly_type.title(),
                "bbox": normalize_bbox(item.get("bbox", {})),
                "confidence": conf,
                "severity": map_severity(conf, anomaly_type),
                "reason": f"AI segmentation detected pixel manipulation indicating a {anomaly_type}.",
                "recommendation": get_recommendation(anomaly_type)
            })
            
    # 3. Normalize Text Forensics
    if isinstance(text_data, list):
        for item in text_data:
            anomaly_type = item.get("anomaly_type", "Text Anomaly")
            conf = float(item.get("confidence", 0.5))
            dossier.append({
                "id": str(uuid.uuid4())[:8],
                "page": 1,
                "label": f"{anomaly_type} ({item.get('field', 'Unknown Field')})",
                "bbox": normalize_bbox(item.get("bbox", {})),
                "confidence": conf,
                "severity": map_severity(conf, anomaly_type),
                "reason": item.get("reason", "Typographic inconsistencies detected."),
                "recommendation": get_recommendation(anomaly_type)
            })
            
    # 4. Normalize Signature
    if isinstance(sig_data, list):
        for item in sig_data:
            classification = item.get("classification", "Signature Anomaly")
            if classification.lower() == "genuine":
                continue # Skip genuine signatures
            conf = float(item.get("confidence", 0.5))
            dossier.append({
                "id": str(uuid.uuid4())[:8],
                "page": 1,
                "label": f"Forged Signature ({classification.title()})",
                "bbox": normalize_bbox(item.get("bbox", {})),
                "confidence": conf,
                "severity": map_severity(conf, classification),
                "reason": item.get("reason", "Signature exhibits unnatural patterns."),
                "recommendation": get_recommendation(classification)
            })
            
    # 5. Normalize Copy-Move
    if isinstance(copymove_data, dict) and "duplicated_regions" in copymove_data:
        for item in copymove_data["duplicated_regions"]:
            classification = item.get("classification", "Duplicated Region")
            conf = float(item.get("confidence", 0.5))
            dossier.append({
                "id": str(uuid.uuid4())[:8],
                "page": 1,
                "label": f"Copy-Move Clone ({classification.title()})",
                "bbox": normalize_bbox(item.get("copied_area", {}).get("bbox", {})),
                "confidence": conf,
                "severity": map_severity(conf, classification),
                "reason": f"Region identified as a geometric clone of another area (Cluster {item.get('cluster_id')}).",
                "recommendation": get_recommendation("copy-move")
            })

    # 6. Deduplication (NMS)
    # Sort by severity rank (desc), then confidence (desc)
    dossier.sort(key=lambda x: (SEVERITY_RANKS.get(x["severity"], 0), x["confidence"]), reverse=True)
    
    deduped = []
    for current in dossier:
        is_duplicate = False
        for kept in deduped:
            if current["page"] != kept["page"]:
                continue
            iou = compute_iou(current["bbox"], kept["bbox"])
            if iou > 0.5:
                # current overlaps significantly with a kept finding.
                # Since list is sorted by highest severity/confidence, we discard current.
                is_duplicate = True
                break
        if not is_duplicate:
            deduped.append(current)
            
    # Save final dossier
    os.makedirs(analysis_dir, exist_ok=True)
    with open(os.path.join(analysis_dir, "forensic_dossier.json"), "w") as f:
        json.dump(deduped, f, indent=2)
        
    return deduped

if __name__ == "__main__":
    generate_forensic_dossier()
