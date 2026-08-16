from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import torch
from PIL import Image
from torch import nn
from torch.utils.data import Dataset
from torchvision import models, transforms

CLASSES = ("banana", "paddy", "cotton", "groundnut")
CLASS_TO_INDEX = {name: index for index, name in enumerate(CLASSES)}
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]


class ManifestDataset(Dataset[tuple[torch.Tensor, int, dict[str, str]]]):
    def __init__(
        self,
        manifest: Path,
        split: str,
        data_root: Path,
        training: bool = False,
    ):
        document = json.loads(manifest.read_text(encoding="utf-8"))
        self.rows = [row for row in document["rows"] if row["split"] == split]
        self.data_root = data_root
        self.transform = (
            transforms.Compose(
                [
                    transforms.RandomResizedCrop(224, scale=(0.75, 1.0)),
                    transforms.RandomHorizontalFlip(),
                    transforms.RandomRotation(10),
                    transforms.ColorJitter(0.15, 0.15, 0.1, 0.05),
                    transforms.ToTensor(),
                    transforms.Normalize(MEAN, STD),
                ]
            )
            if training
            else transforms.Compose(
                [
                    transforms.Resize(256),
                    transforms.CenterCrop(224),
                    transforms.ToTensor(),
                    transforms.Normalize(MEAN, STD),
                ]
            )
        )

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, int, dict[str, str]]:
        row = self.rows[index]
        path = self.data_root / Path(row["path"])
        with Image.open(path) as image:
            tensor = self.transform(image.convert("RGB"))
        return tensor, CLASS_TO_INDEX[row["crop_class"]], {
            "image_id": row["image_id"],
            "sha256": row["sha256"],
            "path": row["path"],
        }


def collate_batch(batch):
    return (
        torch.stack([item[0] for item in batch]),
        torch.as_tensor([item[1] for item in batch], dtype=torch.long),
        [item[2] for item in batch],
    )


def class_weights(dataset: ManifestDataset) -> torch.Tensor:
    counts = Counter(row["crop_class"] for row in dataset.rows)
    total = len(dataset.rows)
    return torch.tensor(
        [total / (len(CLASSES) * counts[name]) for name in CLASSES],
        dtype=torch.float32,
    )


def build_model(pretrained: bool = True) -> nn.Module:
    weights = models.MobileNet_V3_Small_Weights.IMAGENET1K_V1 if pretrained else None
    model = models.mobilenet_v3_small(weights=weights)
    model.classifier[3] = nn.Linear(model.classifier[3].in_features, len(CLASSES))
    return model


def confusion_matrix(labels: torch.Tensor, predictions: torch.Tensor) -> torch.Tensor:
    matrix = torch.zeros((len(CLASSES), len(CLASSES)), dtype=torch.long)
    for truth, predicted in zip(labels.cpu(), predictions.cpu(), strict=True):
        matrix[int(truth), int(predicted)] += 1
    return matrix


def metrics_from_confusion(matrix: torch.Tensor) -> dict[str, Any]:
    values = matrix.float()
    support = values.sum(dim=1)
    predicted = values.sum(dim=0)
    true_positive = values.diag()
    recall = true_positive / support.clamp_min(1)
    precision = true_positive / predicted.clamp_min(1)
    f1 = 2 * precision * recall / (precision + recall).clamp_min(1e-12)
    return {
        "top1": float(true_positive.sum() / values.sum().clamp_min(1)),
        "macro_f1": float(f1.mean()),
        "balanced_accuracy": float(recall.mean()),
        "per_class": {
            name: {
                "precision": float(precision[index]),
                "recall": float(recall[index]),
                "f1": float(f1[index]),
                "support": int(support[index]),
            }
            for index, name in enumerate(CLASSES)
        },
        "confusion_matrix": matrix.tolist(),
    }


def entropy(probabilities: torch.Tensor) -> torch.Tensor:
    return -(probabilities * probabilities.clamp_min(1e-12).log()).sum(dim=1)


def save_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
