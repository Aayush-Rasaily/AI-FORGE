import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TextElement:
    text: str
    confidence: float
    bounding_box: Dict[str, float]  # canonical {x, y, width, height} or list
    page_number: int = 1
    line_index: int = 0
    font_height: float = 0.0
    rotation: float = 0.0
    baseline_position: float = 0.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TextElement":
        return cls(
            text=data.get("text", ""),
            confidence=float(data.get("confidence", 0.0)),
            bounding_box=data.get("bounding_box", {}),
            page_number=int(data.get("page_number", 1)),
            line_index=int(data.get("line_index", 0)),
            font_height=float(data.get("font_height", 0.0)),
            rotation=float(data.get("rotation", 0.0)),
            baseline_position=float(data.get("baseline_position", 0.0))
        )


@dataclass
class SemanticField:
    label: str
    text: str
    bounding_box: Dict[str, float]
    confidence: float = 1.0


@dataclass
class DocumentStructure:
    elements: List[TextElement] = field(default_factory=list)
    fields: List[SemanticField] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentStructure":
        elements = [TextElement.from_dict(e) for e in data.get("elements", [])]
        fields = [
            SemanticField(
                label=f.get("label", ""),
                text=f.get("text", ""),
                bounding_box=f.get("bounding_box", {}),
                confidence=float(f.get("confidence", 1.0))
            ) for f in data.get("fields", [])
        ]
        return cls(elements=elements, fields=fields, metadata=data.get("metadata", {}))

    def save_to_file(self, path: str) -> None:
        import os
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        # Format explicitly to the requested schema for document_map.json
        # Format bounding box as [x, y, w, h]
        formatted_fields = []
        for f in self.fields:
            bbox_dict = f.bounding_box or {}
            x = bbox_dict.get("x", 0)
            y = bbox_dict.get("y", 0)
            w = bbox_dict.get("width", 0)
            h = bbox_dict.get("height", 0)
            
            formatted_fields.append({
                "type": f.label,
                "text": f.text,
                "bbox": [x, y, w, h],
                "confidence": f.confidence
            })
            
        formatted_elements = []
        for e in self.elements:
            bbox_dict = e.bounding_box or {}
            x = bbox_dict.get("x", 0)
            y = bbox_dict.get("y", 0)
            w = bbox_dict.get("width", 0)
            h = bbox_dict.get("height", 0)
            
            formatted_elements.append({
                "text": e.text,
                "bbox": [x, y, w, h],
                "confidence": e.confidence,
                "page": e.page_number,
                "line_index": e.line_index
            })
            
        output_schema = {
            "page": 1,
            "elements": formatted_elements,
            "fields": formatted_fields
        }
        
        with open(path, "w", encoding="utf-8") as file:
            json.dump(output_schema, file, indent=2)
