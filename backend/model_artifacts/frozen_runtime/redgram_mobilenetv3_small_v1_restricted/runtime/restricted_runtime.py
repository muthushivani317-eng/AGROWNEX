from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import hashlib
import json
import math

import torch
from torch import nn
from torchvision import models, transforms
from PIL import Image


@dataclass(frozen=True)
class RestrictedPrediction:
    status: str
    predicted_class: str | None
    calibrated_confidence: float | None
    calibrated_margin: float | None
    result_code: str | None
    abstention_code: str | None
    probabilities: Dict[str, float]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


class RestrictedRedgramRuntime:
    def __init__(
        self,
        package_root: str | Path,
        device: str | None = None,
    ) -> None:
        self.package_root = Path(package_root).resolve()

        config_path = (
            self.package_root
            / "config"
            / "runtime_config.json"
        )

        policy_path = (
            self.package_root
            / "policy"
            / "RESTRICTED_RUNTIME_POLICY.json"
        )

        class_map_path = (
            self.package_root
            / "config"
            / "class_to_index.json"
        )

        if not config_path.is_file():
            raise RuntimeError("RUNTIME_CONFIG_MISSING")

        if not policy_path.is_file():
            raise RuntimeError("RUNTIME_POLICY_MISSING")

        if not class_map_path.is_file():
            raise RuntimeError("CLASS_MAP_MISSING")

        self.config = json.loads(
            config_path.read_text(encoding="utf-8")
        )

        self.policy = json.loads(
            policy_path.read_text(encoding="utf-8")
        )

        self.class_to_index = json.loads(
            class_map_path.read_text(encoding="utf-8")
        )

        expected_class_map = {
            "redgram__healthy": 0,
            "redgram__leaf_spot": 1,
            "redgram__sterility_mosaic": 2,
        }

        if self.class_to_index != expected_class_map:
            raise RuntimeError("CLASS_MAP_MISMATCH")

        self.index_to_class = {
            index: class_name
            for class_name, index
            in self.class_to_index.items()
        }

        checkpoint_path = (
            self.package_root
            / self.config["checkpoint_file"]
        )

        if not checkpoint_path.is_file():
            raise RuntimeError("CHECKPOINT_MISSING")

        expected_hash = self.config[
            "checkpoint_sha256"
        ]

        actual_hash = _sha256_file(checkpoint_path)

        if actual_hash != expected_hash:
            raise RuntimeError("CHECKPOINT_HASH_MISMATCH")

        self.temperature = float(
            self.config["temperature"]
        )

        if (
            not math.isfinite(self.temperature)
            or self.temperature <= 0
        ):
            raise RuntimeError("INVALID_TEMPERATURE")

        if device is None:
            device = (
                "cuda"
                if torch.cuda.is_available()
                else "cpu"
            )

        self.device = torch.device(device)

        checkpoint = torch.load(
            checkpoint_path,
            map_location=self.device,
        )

        if checkpoint.get("model_name") != (
            "redgram_mobilenetv3_small_v1"
        ):
            raise RuntimeError("MODEL_NAME_MISMATCH")

        if checkpoint.get("epoch") != 11:
            raise RuntimeError("CHECKPOINT_EPOCH_MISMATCH")

        if checkpoint.get("class_to_index") != (
            self.class_to_index
        ):
            raise RuntimeError(
                "CHECKPOINT_CLASS_MAP_MISMATCH"
            )

        model = models.mobilenet_v3_small(
            weights=None
        )

        input_features = (
            model.classifier[3].in_features
        )

        model.classifier[3] = nn.Linear(
            input_features,
            len(self.class_to_index),
        )

        model.load_state_dict(
            checkpoint["model_state_dict"]
        )

        model = model.to(self.device)
        model.eval()

        self.model = model

        self.transform = transforms.Compose([
            transforms.Resize(
                self.config["resize_size"]
            ),
            transforms.CenterCrop(
                self.config["image_size"]
            ),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=self.config[
                    "normalization"
                ]["mean"],
                std=self.config[
                    "normalization"
                ]["std"],
            ),
        ])

    def predict(
        self,
        image: Image.Image,
    ) -> RestrictedPrediction:
        try:
            image = image.convert("RGB")
            tensor = self.transform(
                image
            ).unsqueeze(0).to(self.device)

            with torch.no_grad():
                logits = self.model(tensor)

                probabilities_tensor = torch.softmax(
                    logits / self.temperature,
                    dim=1,
                )[0]

            probabilities = {
                self.index_to_class[index]: float(
                    probabilities_tensor[index].item()
                )
                for index in range(
                    len(self.index_to_class)
                )
            }

            if not all(
                math.isfinite(value)
                for value in probabilities.values()
            ):
                return RestrictedPrediction(
                    status="ABSTAINED",
                    predicted_class=None,
                    calibrated_confidence=None,
                    calibrated_margin=None,
                    result_code=None,
                    abstention_code=(
                        "NON_FINITE_PROBABILITY"
                    ),
                    probabilities={},
                )

            sorted_items = sorted(
                probabilities.items(),
                key=lambda item: item[1],
                reverse=True,
            )

            predicted_class, confidence = (
                sorted_items[0]
            )

            second_confidence = sorted_items[1][1]
            margin = confidence - second_confidence

            rule = self.policy["rules"].get(
                predicted_class
            )

            if rule is None:
                return RestrictedPrediction(
                    status="ABSTAINED",
                    predicted_class=predicted_class,
                    calibrated_confidence=confidence,
                    calibrated_margin=margin,
                    result_code=None,
                    abstention_code=(
                        "UNKNOWN_PREDICTED_CLASS"
                    ),
                    probabilities=probabilities,
                )

            if rule["action"] == "ALWAYS_ABSTAIN":
                return RestrictedPrediction(
                    status="ABSTAINED",
                    predicted_class=predicted_class,
                    calibrated_confidence=confidence,
                    calibrated_margin=margin,
                    result_code=None,
                    abstention_code=rule[
                        "abstention_code"
                    ],
                    probabilities=probabilities,
                )

            minimum_confidence = float(
                rule[
                    "minimum_calibrated_confidence"
                ]
            )

            minimum_margin = float(
                rule[
                    "minimum_calibrated_margin"
                ]
            )

            if (
                confidence < minimum_confidence
                or margin < minimum_margin
            ):
                return RestrictedPrediction(
                    status="ABSTAINED",
                    predicted_class=predicted_class,
                    calibrated_confidence=confidence,
                    calibrated_margin=margin,
                    result_code=None,
                    abstention_code=(
                        "CONFIDENCE_OR_MARGIN_FAILED"
                    ),
                    probabilities=probabilities,
                )

            return RestrictedPrediction(
                status=(
                    "ACCEPTED_RESTRICTED_RESULT"
                ),
                predicted_class=predicted_class,
                calibrated_confidence=confidence,
                calibrated_margin=margin,
                result_code=rule["result_wording"],
                abstention_code=None,
                probabilities=probabilities,
            )

        except Exception:
            return RestrictedPrediction(
                status="RUNTIME_ERROR",
                predicted_class=None,
                calibrated_confidence=None,
                calibrated_margin=None,
                result_code=None,
                abstention_code=(
                    "INFERENCE_PROCESSING_FAILED"
                ),
                probabilities={},
            )
