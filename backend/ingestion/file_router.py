from pathlib import Path


def identify_file_type(filename: str):

    extension = Path(
        filename
    ).suffix.lower()


    # Image files
    if extension in [
        ".jpg",
        ".jpeg",
        ".png",
        ".webp"
    ]:
        return "image"


    # Document files
    if extension in [
        ".pdf"
    ]:
        return "document"


    # Video files
    if extension in [
        ".mp4",
        ".mov",
        ".avi",
        ".mkv"
    ]:
        return "video"


    return "unsupported"