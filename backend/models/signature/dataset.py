import random
from pathlib import Path

from PIL import Image

import torch
from torch.utils.data import Dataset

from torchvision import transforms


class SignaturePairDataset(
    Dataset
):

    def __init__(
        self,
        root_dir,
        transform=None
    ):

        self.root_dir = Path(
            root_dir
        )


        self.transform = transform


        self.genuine = []

        self.forged = []


        # Find signature files
        for path in self.root_dir.rglob(
            "*.png"
        ):

            filename = (
                path.name.lower()
            )


            if "genuine" in filename:

                self.genuine.append(
                    path
                )


            elif "forged" in filename:

                self.forged.append(
                    path
                )


        print(
            f"Genuine signatures: "
            f"{len(self.genuine)}"
        )


        print(
            f"Forged signatures: "
            f"{len(self.forged)}"
        )


    def __len__(self):

        return max(

            len(self.genuine),

            len(self.forged)

        ) * 2


    def load_image(
        self,
        path
    ):

        image = Image.open(
            path
        ).convert(
            "RGB"
        )


        if self.transform:

            image = self.transform(
                image
            )


        return image


    def __getitem__(
        self,
        index
    ):

        # 50% genuine pair
        if random.random() < 0.5:

            img1_path = random.choice(
                self.genuine
            )

            img2_path = random.choice(
                self.genuine
            )


            label = 1.0


        # 50% forged pair
        else:

            img1_path = random.choice(
                self.genuine
            )

            img2_path = random.choice(
                self.forged
            )


            label = 0.0


        img1 = self.load_image(
            img1_path
        )


        img2 = self.load_image(
            img2_path
        )


        return (

            img1,

            img2,

            torch.tensor(
                label,
                dtype=torch.float32
            )

        )


def get_transforms():

    return transforms.Compose([

        transforms.Resize(
            (224, 224)
        ),

        transforms.RandomRotation(
            5
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