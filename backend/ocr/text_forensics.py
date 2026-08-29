import os
import json
import re

def compute_iou(boxA, boxB):
    xA = max(boxA["x"], boxB["x"])
    yA = max(boxA["y"], boxB["y"])
    xB = min(boxA["x"] + boxA["width"], boxB["x"] + boxB["width"])
    yB = min(boxA["y"] + boxA["height"], boxB["y"] + boxB["height"])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = boxA["width"] * boxA["height"]
    boxBArea = boxB["width"] * boxB["height"]

    iou = interArea / float(boxAArea + boxBArea - interArea) if (boxAArea + boxBArea - interArea) > 0 else 0
    return iou

def get_field_name(element, fields):
    # Try finding an intersecting field
    best_iou = 0
    best_field = None
    for field in fields:
        iou = compute_iou(element["bounding_box"], field["bounding_box"])
        if iou > best_iou:
            best_iou = iou
            best_field = field["label"]
            
    if best_field:
        return best_field
        
    return "Document Text"

def analyze_document_text(document_map_path="analysis/document_map.json", output_path="analysis/text_forensics.json"):
    if not os.path.exists(document_map_path):
        return []

    with open(document_map_path, "r") as f:
        doc_map = json.load(f)

    elements = doc_map.get("elements", [])
    fields = doc_map.get("fields", [])

    if not elements:
        return []

    # Group elements into lines
    # Sort by Y first
    elements = sorted(elements, key=lambda e: e["bounding_box"]["y"])
    lines = []
    current_line = []
    
    for e in elements:
        if not current_line:
            current_line.append(e)
            continue
            
        last_y = current_line[-1]["bounding_box"]["y"]
        current_y = e["bounding_box"]["y"]
        
        # If within 10px vertical tolerance, it's on the same line
        if abs(current_y - last_y) <= 10:
            current_line.append(e)
        else:
            lines.append(sorted(current_line, key=lambda x: x["bounding_box"]["x"]))
            current_line = [e]
            
    if current_line:
        lines.append(sorted(current_line, key=lambda x: x["bounding_box"]["x"]))

    findings = []

    for line in lines:
        if len(line) < 1:
            continue
            
        avg_font_height = sum(e.get("font_height", 0) for e in line) / len(line)
        avg_baseline = sum(e.get("baseline_position", 0) for e in line) / len(line)

        for i, elem in enumerate(line):
            text = elem.get("text", "")
            conf = elem.get("confidence", 1.0)
            fh = elem.get("font_height", 0)
            bp = elem.get("baseline_position", 0)
            bbox = elem.get("bounding_box", {})
            
            # Check conditions
            is_digit = bool(re.search(r'\d', text))
            has_font_anomaly = abs(fh - avg_font_height) > max(2, avg_font_height * 0.1)
            has_baseline_anomaly = abs(bp - avg_baseline) > 2
            
            # Check kerning with previous element
            kerning_anomaly = False
            if i > 0:
                prev = line[i-1]
                dist = bbox["x"] - (prev["bounding_box"]["x"] + prev["bounding_box"]["width"])
                # If they overlap significantly or are unusually far for a single word
                if dist < -2 or (dist > avg_font_height * 1.5 and dist < avg_font_height * 3 and is_digit):
                    kerning_anomaly = True

            # Confidence check
            low_conf = conf < 0.85

            if low_conf or has_font_anomaly or has_baseline_anomaly or kerning_anomaly:
                field_name = get_field_name(elem, fields)
                
                anomaly_type = "Suspicious text modification"
                reason = []
                
                if low_conf:
                    reason.append(f"Low OCR confidence ({int(conf*100)}%)")
                if has_font_anomaly:
                    reason.append(f"Font size mismatch (expected ~{avg_font_height:.1f}, got {fh})")
                if has_baseline_anomaly:
                    reason.append("Baseline misalignment")
                if kerning_anomaly:
                    reason.append("Irregular character spacing/kerning")
                    
                if is_digit:
                    if "Total" in field_name or "Price" in field_name or "Tax" in field_name or "Table Cells" in field_name:
                        anomaly_type = "Modified price"
                    elif "Date" in field_name:
                        anomaly_type = "Modified date"
                    elif len(text) <= 2 and kerning_anomaly:
                        anomaly_type = "Suspicious digit insertion"
                    else:
                        anomaly_type = "Modified digits"
                else:
                    if "Name" in field_name or "Customer" in field_name:
                        anomaly_type = "Modified name"
                    
                findings.append({
                    "field": field_name,
                    "anomaly_type": anomaly_type,
                    "confidence": round(1.0 - conf, 4) if conf > 0.1 else 0.95,
                    "bbox": bbox,
                    "reason": " | ".join(reason)
                })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(findings, f, indent=2)

    return findings

if __name__ == "__main__":
    analyze_document_text()
