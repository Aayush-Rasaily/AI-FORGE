import torch

from torch.utils.data import DataLoader

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score
)

from backend.models.signature.model import (
    SiameseNetwork
)

from backend.models.signature.dataset import (
    SignaturePairDataset,
    get_transforms
)


# ==========================================
# Configuration
# ==========================================

DATASET_PATH = (
    "data/signatures"
)

MODEL_PATH = (
    "backend/models/signature/"
    "weights/siamese_best.pt"
)

BATCH_SIZE = 16

EPOCHS = 10

LEARNING_RATE = 1e-4


# ==========================================
# Device
# ==========================================

device = torch.device(

    "cuda"
    if torch.cuda.is_available()
    else "cpu"

)

print(
    f"\nUsing device: {device}"
)


# ==========================================
# Writer Split
# ==========================================

TRAIN_WRITERS = list(
    range(1, 41)
)

VAL_WRITERS = list(
    range(41, 48)
)

TEST_WRITERS = list(
    range(48, 56)
)


# ==========================================
# Dataset
# ==========================================

train_dataset = SignaturePairDataset(

    DATASET_PATH,

    writers=TRAIN_WRITERS,

    transform=get_transforms(
        training=True
    ),

    pairs_per_writer=20

)


val_dataset = SignaturePairDataset(

    DATASET_PATH,

    writers=VAL_WRITERS,

    transform=get_transforms(
        training=False
    ),

    pairs_per_writer=20

)


test_dataset = SignaturePairDataset(

    DATASET_PATH,

    writers=TEST_WRITERS,

    transform=get_transforms(
        training=False
    ),

    pairs_per_writer=20

)


# ==========================================
# DataLoaders
# ==========================================

train_loader = DataLoader(

    train_dataset,

    batch_size=BATCH_SIZE,

    shuffle=True,

    num_workers=0

)


val_loader = DataLoader(

    val_dataset,

    batch_size=BATCH_SIZE,

    shuffle=False,

    num_workers=0

)


test_loader = DataLoader(

    test_dataset,

    batch_size=BATCH_SIZE,

    shuffle=False,

    num_workers=0

)


# ==========================================
# Model
# ==========================================

model = SiameseNetwork(

    embedding_dim=256

)

model = model.to(
    device
)


# ==========================================
# Loss
# ==========================================

criterion = torch.nn.CosineEmbeddingLoss(

    margin=0.5

)


# ==========================================
# Optimizer
# ==========================================

optimizer = torch.optim.AdamW(

    model.parameters(),

    lr=LEARNING_RATE,

    weight_decay=1e-4

)


# ==========================================
# Validation Function
# ==========================================

def evaluate(

    model,

    loader

):

    model.eval()


    predictions = []

    labels_list = []

    similarities = []


    with torch.no_grad():

        for (

            img1,

            img2,

            labels

        ) in loader:

            img1 = img1.to(
                device
            )

            img2 = img2.to(
                device
            )


            emb1, emb2 = model(

                img1,

                img2

            )


            similarity = (

                torch.cosine_similarity(

                    emb1,

                    emb2

                )

            )


            similarities.extend(

                similarity.cpu().numpy()

            )


            labels_list.extend(

                labels.numpy()

            )


    # Threshold
    predictions = [

        1 if score >= 0.5
        else 0

        for score in similarities

    ]


    accuracy = accuracy_score(

        labels_list,

        predictions

    )


    precision = precision_score(

        labels_list,

        predictions,

        zero_division=0

    )


    recall = recall_score(

        labels_list,

        predictions,

        zero_division=0

    )


    f1 = f1_score(

        labels_list,

        predictions,

        zero_division=0

    )


    try:

        auc = roc_auc_score(

            labels_list,

            similarities

        )

    except:

        auc = 0


    return {

        "accuracy":
            accuracy,

        "precision":
            precision,

        "recall":
            recall,

        "f1":
            f1,

        "auc":
            auc

    }


# ==========================================
# Training
# ==========================================

best_f1 = 0


for epoch in range(

    EPOCHS

):

    model.train()


    total_loss = 0


    for (

        img1,

        img2,

        labels

    ) in train_loader:


        img1 = img1.to(
            device
        )


        img2 = img2.to(
            device
        )


        labels = labels.to(
            device
        )


        # Convert:
        #
        # 1 → +1
        # 0 → -1

        target = (

            labels * 2
        ) - 1


        # Forward pass

        emb1, emb2 = model(

            img1,

            img2

        )


        # Calculate loss

        loss = criterion(

            emb1,

            emb2,

            target

        )


        # Clear gradients

        optimizer.zero_grad()


        # Backpropagation

        loss.backward()


        # Update weights

        optimizer.step()


        total_loss += (

            loss.item()

        )


    avg_loss = (

        total_loss /

        len(train_loader)

    )


    # ==================================
    # Validation
    # ==================================

    metrics = evaluate(

        model,

        val_loader

    )


    print(

        f"\nEpoch "
        f"{epoch + 1}/{EPOCHS}"

    )


    print(

        f"Train Loss: "
        f"{avg_loss:.4f}"

    )


    print(

        f"Validation Accuracy: "
        f"{metrics['accuracy']:.4f}"

    )


    print(

        f"Validation Precision: "
        f"{metrics['precision']:.4f}"

    )


    print(

        f"Validation Recall: "
        f"{metrics['recall']:.4f}"

    )


    print(

        f"Validation F1: "
        f"{metrics['f1']:.4f}"

    )


    print(

        f"Validation ROC-AUC: "
        f"{metrics['auc']:.4f}"

    )


    # ==================================
    # Save Best Model
    # ==================================

    if metrics["f1"] > best_f1:

        best_f1 = metrics["f1"]


        torch.save(

            model.state_dict(),

            MODEL_PATH

        )


        print(

            "✓ Best model saved!"

        )


# ==========================================
# Final Test
# ==========================================

print(

    "\nLoading best model..."

)


model.load_state_dict(

    torch.load(

        MODEL_PATH,

        map_location=device

    )

)


test_metrics = evaluate(

    model,

    test_loader

)


print(

    "\n================================"

)

print(

    "FINAL TEST RESULTS"

)

print(

    "================================"

)


for key, value in (

    test_metrics.items()

):

    print(

        f"{key.upper()}: "
        f"{value:.4f}"

    )


print(

    "\nTraining completed!"

)


print(

    f"Model saved at:"
    f"\n{MODEL_PATH}"

)