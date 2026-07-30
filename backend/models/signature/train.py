import torch

from torch.utils.data import DataLoader

from torchvision import transforms

from backend.models.signature.model import (
    SiameseNetwork
)

from backend.models.signature.dataset import (
    SignaturePairDataset,
    get_transforms
)


DATASET_PATH = (
    "data/signatures"
)


MODEL_PATH = (
    "backend/models/signature/weights/"
    "siamese_best.pt"
)


def train():

    device = torch.device(

        "cuda"
        if torch.cuda.is_available()
        else "cpu"

    )


    print(
        f"Using device: {device}"
    )


    dataset = SignaturePairDataset(

        DATASET_PATH,

        transform=get_transforms()

    )


    dataloader = DataLoader(

        dataset,

        batch_size=16,

        shuffle=True,

        num_workers=0

    )


    model = SiameseNetwork(

        embedding_dim=256

    )


    model = model.to(
        device
    )


    optimizer = torch.optim.AdamW(

        model.parameters(),

        lr=1e-4

    )


    criterion = torch.nn.CosineEmbeddingLoss(

        margin=0.5

    )


    epochs = 10


    for epoch in range(
        epochs
    ):

        model.train()


        total_loss = 0


        for (

            img1,

            img2,

            labels

        ) in dataloader:


            img1 = img1.to(
                device
            )


            img2 = img2.to(
                device
            )


            labels = labels.to(
                device
            )


            emb1, emb2 = model(

                img1,

                img2

            )


            # Convert 0/1 to -1/+1
            target = (

                labels * 2
            ) - 1


            loss = criterion(

                emb1,

                emb2,

                target

            )


            optimizer.zero_grad()


            loss.backward()


            optimizer.step()


            total_loss += (
                loss.item()
            )


        avg_loss = (

            total_loss /
            len(dataloader)

        )


        print(

            f"Epoch "
            f"{epoch + 1}/{epochs} "
            f"- Loss: "
            f"{avg_loss:.4f}"

        )


    torch.save(

        model.state_dict(),

        MODEL_PATH

    )


    print(

        f"\nModel saved to:"
        f"\n{MODEL_PATH}"

    )


if __name__ == "__main__":

    train()