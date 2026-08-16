from __future__ import annotations

import argparse
import csv
import json
import platform
import random
import sys
from datetime import UTC, datetime
from pathlib import Path

import torch
from torch import nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torch.utils.data import DataLoader

from training_tools.crop_identity_v1.common import (
    CLASSES,
    CLASS_TO_INDEX,
    MEAN,
    STD,
    ManifestDataset,
    build_model,
    class_weights,
    collate_batch,
    confusion_matrix,
    metrics_from_confusion,
    save_json,
)


def evaluate(model, loader, device) -> tuple[float, dict]:
    model.eval()
    criterion = nn.CrossEntropyLoss()
    labels_all, predictions_all = [], []
    total_loss = 0.0
    with torch.inference_mode():
        for images, labels, _ in loader:
            images, labels = images.to(device), labels.to(device)
            logits = model(images)
            total_loss += float(criterion(logits, labels)) * len(labels)
            labels_all.append(labels.cpu())
            predictions_all.append(logits.argmax(dim=1).cpu())
    labels = torch.cat(labels_all)
    predictions = torch.cat(predictions_all)
    return total_loss / len(labels), metrics_from_confusion(confusion_matrix(labels, predictions))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--data-root",
        type=Path,
        required=True,
        help="Root containing the manifest-relative vision/... image paths.",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--patience", type=int, default=6)
    parser.add_argument("--seed", type=int, default=20260729)
    args = parser.parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError("GPU_REQUIRED_FOR_APPROVED_TRAINING_RUN")
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    torch.use_deterministic_algorithms(True, warn_only=True)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    device = torch.device("cuda")
    train_data = ManifestDataset(
        args.manifest, "training", args.data_root, training=True
    )
    dev_data = ManifestDataset(
        args.manifest, "development_validation", args.data_root
    )
    train_loader = DataLoader(
        train_data,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.workers,
        collate_fn=collate_batch,
        pin_memory=True,
    )
    dev_loader = DataLoader(
        dev_data,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.workers,
        collate_fn=collate_batch,
        pin_memory=True,
    )
    model = build_model(pretrained=True).to(device)
    weights = class_weights(train_data).to(device)
    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4)
    scheduler = ReduceLROnPlateau(optimizer, mode="max", factor=0.5, patience=2)
    history = []
    best_macro_f1 = -1.0
    stale = 0
    for epoch in range(1, args.epochs + 1):
        model.train()
        running = 0.0
        seen = 0
        for images, labels, _ in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(images)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()
            running += float(loss) * len(labels)
            seen += len(labels)
        dev_loss, metrics = evaluate(model, dev_loader, device)
        scheduler.step(metrics["macro_f1"])
        row = {
            "epoch": epoch,
            "training_loss": running / seen,
            "development_loss": dev_loss,
            **{key: metrics[key] for key in ("top1", "macro_f1", "balanced_accuracy")},
            "learning_rate": optimizer.param_groups[0]["lr"],
        }
        history.append(row)
        checkpoint = {
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "scheduler_state_dict": scheduler.state_dict(),
            "epoch": epoch,
            "model_name": "crop_identity_mobilenetv3_small_v1",
            "architecture": "mobilenet_v3_small",
            "class_to_index": CLASS_TO_INDEX,
            "preprocessing": {"input_size": 224, "mean": MEAN, "std": STD},
            "development_metrics": metrics,
        }
        torch.save(checkpoint, output / "last.pt")
        if metrics["macro_f1"] > best_macro_f1:
            best_macro_f1 = metrics["macro_f1"]
            stale = 0
            torch.save(checkpoint, output / "best.pt")
        else:
            stale += 1
        if stale >= args.patience:
            break
    with (output / "training_history.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=history[0].keys())
        writer.writeheader()
        writer.writerows(history)
    config = {
        "model_name": "crop_identity_mobilenetv3_small_v1",
        "architecture": "mobilenet_v3_small",
        "input_size": 224,
        "random_seed": args.seed,
        "pretrained_weights": "torchvision IMAGENET1K_V1",
        "optimizer": "AdamW",
        "learning_rate": 3e-4,
        "scheduler": "ReduceLROnPlateau(macro_f1)",
        "batch_size": args.batch_size,
        "max_epochs": args.epochs,
        "early_stopping_patience": args.patience,
        "loss": "class-weighted cross-entropy",
        "imbalance_strategy": "class-weighted loss; natural unweighted evaluation loaders",
        "normalization": {"mean": MEAN, "std": STD},
        "augmentations": [
            "random_resized_crop(scale=0.75..1.0)",
            "horizontal_flip",
            "rotation_10_degrees",
            "mild_color_jitter",
        ],
    }
    save_json(output / "training_config.json", config)
    save_json(output / "class_to_index.json", CLASS_TO_INDEX)
    save_json(output / "index_to_class.json", {str(v): k for k, v in CLASS_TO_INDEX.items()})
    save_json(output / "preprocessing.json", {"resize": 256, "center_crop": 224, "mean": MEAN, "std": STD})
    environment = {
        "python": sys.version,
        "platform": platform.platform(),
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0),
    }
    save_json(output / "environment.json", environment)
    save_json(
        output / "TRAINING_RECEIPT.json",
        {
            "status": "PUBLIC_DATASET_PROVISIONAL",
            "completed_at_utc": datetime.now(UTC).isoformat(),
            "checkpoint_selection": "maximum development_validation macro F1",
            "provisional_test_opened": False,
            "official_accuracy_claim": False,
        },
    )


if __name__ == "__main__":
    main()
