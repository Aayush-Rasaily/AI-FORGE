import datetime
from typing import Any, Dict, List

def build_tampering_reconstruction(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforms raw AI analysis outputs into a chronological and human-readable forensic reconstruction.
    """
    loc = analysis.get("localization") or analysis.get("forgery_localization") or {}
    regions = loc.get("regions", [])
    
    metadata = analysis.get("metadata", {})
    copy_move = analysis.get("copy_move") or analysis.get("tampering", {}).get("copy_move") or {}
    
    jury = analysis.get("jury", {})
    fusion = jury.get("fusion", {})
    risk_score = float(analysis.get("risk_score", fusion.get("overall_score", 0)))
    verdict = analysis.get("verdict", jury.get("verdict", "Authentic"))

    # Extract finding details for evidence map
    suspicious_objects = []
    human_findings = []
    risk_reasons = []
    
    # Process Regions
    for r in regions:
        rtype = str(r.get("type", "region")).lower()
        conf = float(r.get("confidence") or r.get("score") or 0)
        
        # Human Findings & Inventory mapping
        if "signature" in rtype:
            human_findings.append("A new signature appears to have been inserted or overwritten.")
            suspicious_objects.append("Added Signature")
            risk_reasons.append("Added or manipulated signature")
        elif "text" in rtype or "modification" in rtype:
            human_findings.append("Text content (possibly an amount or date) appears to have been modified.")
            suspicious_objects.append("Edited Text/Numbers")
            risk_reasons.append("Edited financial or textual content")
        elif "logo" in rtype:
            human_findings.append("The company logo appears pasted from another source.")
            suspicious_objects.append("Added Logo")
            risk_reasons.append("Manipulated corporate logo")
        else:
            human_findings.append(f"A suspicious {rtype} manipulation was detected.")
            suspicious_objects.append(f"Manipulated {rtype}")

    # Process Copy Move
    if copy_move.get("copy_move_detected"):
        human_findings.append("The document contains cloned pixels or regions copied from elsewhere in the image.")
        suspicious_objects.append("Copied Regions")
        risk_reasons.append("Pixel cloning/Copy-Move detected")

    # Process Metadata
    if metadata.get("is_modified") or metadata.get("software"):
        human_findings.append(f"The document was likely exported after editing using {metadata.get('software', 'image editing software')}.")
        risk_reasons.append("Metadata indicates post-processing or export software")

    # Process Noise / ELA / Compression
    if analysis.get("ela", {}).get("suspicious") or analysis.get("noise", {}).get("suspicious"):
        human_findings.append("Multiple editing artifacts and localized compression inconsistencies were found.")
        suspicious_objects.append("Artificial Blur / Inpainting")
        risk_reasons.append("Compression mismatch / Noise anomaly")

    # Deduplicate lists
    human_findings = list(dict.fromkeys(human_findings))
    suspicious_objects = list(dict.fromkeys(suspicious_objects))
    risk_reasons = list(dict.fromkeys(risk_reasons))

    # Fallback for authentic
    if not human_findings and verdict == "Authentic":
        human_findings.append("No clear evidence of digital manipulation found.")

    # Generate Fraud Story
    story = ""
    if verdict in ["Tampered", "High Risk"] or risk_score > 0.6:
        story = "The analysis indicates that the document was likely edited after creation. "
        if "Edited Text/Numbers" in suspicious_objects:
            story += "The original text (possibly totals or dates) appears to have been replaced. "
        if "Added Signature" in suspicious_objects:
            story += "A digitally inserted signature is present. "
        if "Added Logo" in suspicious_objects:
            story += "The logo seems to be copy-pasted. "
        if metadata.get("is_modified"):
            story += "The document was subsequently re-exported. "
        story += "Multiple editing artifacts support this conclusion."
    else:
        story = "The analysis indicates the document is authentic. No significant digital manipulation, cloned regions, or metadata anomalies were detected."

    # Evidence Timeline
    timeline = []
    
    cr = metadata.get("creation_date") or metadata.get("CreationDate")
    mo = metadata.get("modification_date") or metadata.get("ModDate")
    
    if cr:
        timeline.append({"stage": "Original Creation", "description": f"Document originally created. ({cr})"})
    else:
        timeline.append({"stage": "Original Creation", "description": "Document originally created."})
        
    if verdict in ["Tampered", "High Risk"] and human_findings:
        timeline.append({"stage": "Detected Modification", "description": human_findings[0]})
        
    if mo:
        timeline.append({"stage": "Possible Export", "description": f"Document re-exported or saved. ({mo})"})
        
    timeline.append({"stage": "Current Upload", "description": "Document uploaded for analysis."})
    timeline.append({"stage": "Analysis Time", "description": f"AI-FORGE completed forensic analysis."})

    # Risk Explanation
    if risk_score > 0.6 or verdict in ["Tampered", "High Risk"]:
        risk_explanation = f"High Risk because:\n" + "\n".join([f"• {r}" for r in risk_reasons])
    else:
        risk_explanation = "Low Risk. No significant manipulation found."

    # Layout reconstruction estimation
    original_layout = {
        "text_replaced": "Edited Text/Numbers" in suspicious_objects,
        "signature_replaced": "Added Signature" in suspicious_objects,
        "alignment_issues_detected": len(regions) > 0
    }

    return {
        "fraud_story": story,
        "human_findings": human_findings,
        "suspicious_objects": suspicious_objects,
        "timeline": timeline,
        "risk_explanation": risk_explanation,
        "evidence_map": regions,
        "original_layout": original_layout
    }
