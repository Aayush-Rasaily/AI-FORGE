import torch
import torch.nn as nn
import timm


class SignatureEncoder(nn.Module):

    def __init__(
        self,
        embedding_dim=256
    ):

        super().__init__()


        # EfficientNet-B0 backbone
        self.backbone = timm.create_model(

            "efficientnet_b0",

            pretrained=True,

            num_classes=0

        )


        # EfficientNet-B0 output dimension
        feature_dim = (
            self.backbone.num_features
        )


        # Projection layer
        self.embedding = nn.Sequential(

            nn.Linear(
                feature_dim,
                embedding_dim
            ),

            nn.ReLU(),

            nn.Dropout(
                0.3
            ),

            nn.Linear(
                embedding_dim,
                embedding_dim
            )

        )


    def forward(
        self,
        x
    ):

        features = self.backbone(
            x
        )


        embeddings = self.embedding(
            features
        )


        # Normalize embeddings
        embeddings = nn.functional.normalize(

            embeddings,

            p=2,

            dim=1

        )


        return embeddings


class SiameseNetwork(nn.Module):

    def __init__(
        self,
        embedding_dim=256
    ):

        super().__init__()


        self.encoder = SignatureEncoder(

            embedding_dim=embedding_dim

        )


    def forward(
        self,
        image1,
        image2
    ):

        embedding1 = self.encoder(
            image1
        )


        embedding2 = self.encoder(
            image2
        )


        return (

            embedding1,

            embedding2

        )