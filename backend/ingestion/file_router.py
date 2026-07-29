from pathlib import Path


# Supported file extensions
IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
}

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
}

DOCUMENT_EXTENSIONS = {
    ".pdf",
}


def identify_file_type(filename: str) -> str:
    """
    Identify the type of uploaded evidence
    based on its file extension.
    """

    extension = Path(filename).suffix.lower()

    if extension in IMAGE_EXTENSIONS:
        return "image"

    if extension in VIDEO_EXTENSIONS:
        return "video"

    if extension in DOCUMENT_EXTENSIONS:
        return "document"

    return "unsupported"