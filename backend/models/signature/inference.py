import torch

from PIL import Image

from torchvision import transforms

from backend.models.signature.model import (
    SiameseNetwork
)


MODEL_PATH = (
    "backend/models/signature/weights/"
    "siamese_best.pt"
)


device = torch.device(

    "cuda"
    if torch.cuda.is_available()
    else "cpu"

)


model = SiameseNetwork(

    embedding_dim=256

)


def load_model():

    checkpoint = torch.load(

        MODEL_PATH,

        map_location=device

    )


    model.load_state_dict(
        checkpoint
    )


    model.to(
        device
    )


    model.eval()


def preprocess(
    image_path
):

    transform = transforms.Compose([

        transforms.Resize(
            (224, 224)
        ),

        transforms.ToTensor(),

        transforms.Normalize(

            mean=[
                0.485,
                0.456,
                0.406
            ],

            std=[
                0.229,
                0.224,
                0.225
            ]

        )

    ])


    image = Image.open(

        image_path

    ).convert(
        "RGB"
    )


    image = transform(
        image
    )


    return image.unsqueeze(
        0
    )


def verify_signature(

    reference_path,

    query_path

):

    load_model()


    reference = preprocess(

        reference_path

    ).to(
        device
    )


    query = preprocess(

        query_path

    ).to(
        device
    )


    with torch.no_grad():

        emb1 = model.encoder(

            reference

        )


        emb2 = model.encoder(

            query

        )


        similarity = torch.cosine_similarity(

            emb1,

            emb2

        ).item()


    # Threshold
    threshold = 0.50


    if similarity >= threshold:

        verdict = "Genuine"

    else:

        verdict = "Forged"


    confidence = abs(

        similarity

    )


    return {

        "verdict":
            verdict,

        "similarity":
            round(
                similarity,
                4
            ),

        "confidence":
            round(
                confidence,
                4
            )

    }