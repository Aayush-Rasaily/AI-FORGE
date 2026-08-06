from pathlib import Path

import torch
from PIL import Image
from torchvision import transforms

from backend.models.signature.model import SiameseNetwork


from backend.utils.hardware import get_torch_device


# ==========================================
# Configuration
# ==========================================

MODEL_PATH = Path(
    "backend/models/signature/weights/siamese_best.pt"
)

DEVICE = torch.device(get_torch_device())


# ==========================================
# Image Transform
# ==========================================

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


# ==========================================
# Load Model
# ==========================================

def load_model():

    model = SiameseNetwork(
        embedding_dim=256
    )

    model.load_state_dict(

        torch.load(

            MODEL_PATH,

            map_location=DEVICE

        )

    )

    model = model.to(
        DEVICE
    )

    model.eval()

    return model


# ==========================================
# Load Image
# ==========================================

def load_image(
    image_path
):

    image = Image.open(

        image_path

    ).convert(

        "RGB"

    )

    image = transform(
        image
    )

    image = image.unsqueeze(
        0
    )

    return image.to(
        DEVICE
    )


# ==========================================
# Verify Signature
# ==========================================

def verify_signature(

    reference_path,

    query_path

):

    model = load_model()


    reference = load_image(

        reference_path

    )


    query = load_image(

        query_path

    )


    with torch.no_grad():

        embedding1, embedding2 = model(

            reference,

            query

        )


        similarity = (

            torch.cosine_similarity(

                embedding1,

                embedding2

            )

            .item()

        )


    # ======================================
    # Decision
    # ======================================

    threshold = 0.5


    if similarity >= threshold:

        verdict = "Genuine"

    else:

        verdict = "Potential Forgery"


    # Convert similarity to
    # confidence-like score

    confidence = (

        abs(similarity)

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