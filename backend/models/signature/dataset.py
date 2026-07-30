import random
from pathlib import Path

from PIL import Image

import torch
from torch.utils.data import Dataset
from torchvision import transforms


class SignaturePairDataset(Dataset):

    def __init__(
        self,
        root_dir,
        writers=None,
        transform=None,
        pairs_per_writer=20
    ):

        self.root_dir = Path(root_dir)
        self.transform = transform
        self.pairs = []

        # --------------------------------
        # Directories
        # --------------------------------

        original_dir = self.root_dir / "full_org"
        forgery_dir = self.root_dir / "full_forg"

        if not original_dir.exists():
            raise FileNotFoundError(
                f"Original directory not found: {original_dir}"
            )

        if not forgery_dir.exists():
            raise FileNotFoundError(
                f"Forgery directory not found: {forgery_dir}"
            )

        # --------------------------------
        # Organize signatures by writer
        # --------------------------------

        self.originals = {}
        self.forgeries = {}

        # --------------------------------
        # Load original signatures
        # --------------------------------

        for path in original_dir.glob("*.png"):

            parts = path.stem.split("_")

            # Example:
            # original_1_1
            # parts = ["original", "1", "1"]

            if len(parts) != 3:
                continue

            writer_id = int(parts[1])

            if (
                writers is None
                or writer_id in writers
            ):

                self.originals.setdefault(
                    writer_id,
                    []
                ).append(path)

        # --------------------------------
        # Load forged signatures
        # --------------------------------

        for path in forgery_dir.glob("*.png"):

            parts = path.stem.split("_")

            # Example:
            # forgeries_1_1
            # parts = ["forgeries", "1", "1"]

            if len(parts) != 3:
                continue

            writer_id = int(parts[1])

            if (
                writers is None
                or writer_id in writers
            ):

                self.forgeries.setdefault(
                    writer_id,
                    []
                ).append(path)

        # --------------------------------
        # Generate pairs
        # --------------------------------

        self.create_pairs(
            pairs_per_writer
        )

        print(
            f"Dataset created | "
            f"Writers: {len(self.originals)} | "
            f"Pairs: {len(self.pairs)}"
        )

    # ====================================
    # CREATE PAIRS
    # ====================================

    def create_pairs(
        self,
        pairs_per_writer
    ):

        # --------------------------------
        # Positive and same-writer
        # negative pairs
        # --------------------------------

        for writer_id in self.originals:

            originals = self.originals[
                writer_id
            ]

            forgeries = self.forgeries.get(
                writer_id,
                []
            )

            # ============================
            # POSITIVE PAIRS
            # Genuine + Genuine
            # Label = 1
            # ============================

            if len(originals) >= 2:

                for _ in range(
                    pairs_per_writer
                ):

                    img1, img2 = random.sample(
                        originals,
                        2
                    )

                    self.pairs.append(
                        (
                            img1,
                            img2,
                            1
                        )
                    )

            # ============================
            # NEGATIVE PAIRS
            # Genuine + Corresponding Forgery
            # ============================

            for original_path in originals:

                parts = (
                    original_path.stem.split("_")
                )

                signature_id = int(
                    parts[2]
                )

                matching_forgery = (

                    self.root_dir
                    / "full_forg"
                    / f"forgeries_{writer_id}_{signature_id}.png"

                )

                if matching_forgery.exists():

                    self.pairs.append(
                        (
                            original_path,
                            matching_forgery,
                            0
                        )
                    )

            # ============================
            # NEGATIVE PAIRS
            # Genuine + Random Forgery
            # ============================

            if forgeries:

                for _ in range(
                    pairs_per_writer
                ):

                    genuine = random.choice(
                        originals
                    )

                    forgery = random.choice(
                        forgeries
                    )

                    self.pairs.append(
                        (
                            genuine,
                            forgery,
                            0
                        )
                    )

        # --------------------------------
        # Different writer pairs
        # --------------------------------

        all_writers = list(
            self.originals.keys()
        )

        if len(all_writers) >= 2:

            for _ in range(
                len(all_writers)
                * pairs_per_writer
            ):

                writer_a, writer_b = random.sample(
                    all_writers,
                    2
                )

                img1 = random.choice(
                    self.originals[
                        writer_a
                    ]
                )

                img2 = random.choice(
                    self.originals[
                        writer_b
                    ]
                )

                self.pairs.append(
                    (
                        img1,
                        img2,
                        0
                    )
                )

    # ====================================
    # DATASET LENGTH
    # ====================================

    def __len__(self):

        return len(
            self.pairs
        )

    # ====================================
    # LOAD IMAGE
    # ====================================

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

    # ====================================
    # GET ITEM
    # ====================================

    def __getitem__(
        self,
        index
    ):

        img1_path, img2_path, label = (
            self.pairs[index]
        )

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


# ========================================
# IMAGE PREPROCESSING
# ========================================

def get_transforms(
    training=True
):

    transform_list = [

        transforms.Resize(
            (224, 224)
        )

    ]

    # ------------------------------------
    # Data augmentation
    # ------------------------------------

    if training:

        transform_list.extend([

            transforms.RandomRotation(
                5
            ),

            transforms.RandomAffine(

                degrees=0,

                translate=(
                    0.05,
                    0.05
                ),

                scale=(
                    0.95,
                    1.05
                )

            )

        ])

    # ------------------------------------
    # Tensor + Normalization
    # ------------------------------------

    transform_list.extend([

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

    return transforms.Compose(
        transform_list
    )