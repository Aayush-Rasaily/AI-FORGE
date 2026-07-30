import easyocr


reader = easyocr.Reader(
    ["en"],
    gpu=False
)


def extract_text(
    image_path: str
):

    results = reader.readtext(
        image_path
    )


    extracted_text = []


    for result in results:

        text = result[1]

        confidence = result[2]


        extracted_text.append({

            "text": text,

            "confidence":
                float(confidence)

        })


    full_text = " ".join(

        item["text"]

        for item
        in extracted_text

    )


    return {

        "full_text":
            full_text,

        "detections":
            extracted_text

    }