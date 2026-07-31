from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Optional

import hashlib
import json
import math

import torch
from torch import nn
from torchvision import models, transforms
from PIL import Image


@dataclass(frozen=True)
class ChilliPrediction:
    status: str
    predicted_class: Optional[str]
    calibrated_confidence: Optional[float]
    calibrated_margin: Optional[float]
    result_code: Optional[str]
    abstention_code: Optional[str]
    probabilities: Dict[str, float]

    def to_dict(self) -> dict:
        return asdict(self)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


class RestrictedChilliRuntime:
    EXPECTED_CLASS_MAP = {
        "chilli__bacterial_spot": 0,
        "chilli__cercospora_leaf_spot": 1,
        "chilli__healthy": 2,
        "chilli__leaf_curl_virus": 3,
    }

    EXPECTED_MODEL_NAME = (
        "chilli_mobilenetv3_small_v1"
    )

    EXPECTED_CHECKPOINT_EPOCH = 5

    def __init__(
        self,
        package_root: str | Path,
        device: Optional[str] = None,
    ) -> None:
        self.package_root = Path(
            package_root
        ).resolve()

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
            raise RuntimeError(
                "RUNTIME_CONFIG_MISSING"
            )

        if not policy_path.is_file():
            raise RuntimeError(
                "RUNTIME_POLICY_MISSING"
            )

        if not class_map_path.is_file():
            raise RuntimeError(
                "CLASS_MAP_MISSING"
            )

        self.config = json.loads(
            config_path.read_text(
                encoding="utf-8"
            )
        )

        self.policy = json.loads(
            policy_path.read_text(
                encoding="utf-8"
            )
        )

        self.class_to_index = json.loads(
            class_map_path.read_text(
                encoding="utf-8"
            )
        )

        if (
            self.class_to_index
            != self.EXPECTED_CLASS_MAP
        ):
            raise RuntimeError(
                "CLASS_REGISTRY_MISMATCH"
            )

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
            raise RuntimeError(
                "CHECKPOINT_MISSING"
            )

        expected_hash = str(
            self.config["checkpoint_sha256"]
        )

        actual_hash = sha256_file(
            checkpoint_path
        )

        if actual_hash != expected_hash:
            raise RuntimeError(
                "CHECKPOINT_HASH_MISMATCH"
            )

        self.temperature = float(
            self.config["temperature"]
        )

        self.confidence_threshold = float(
            self.config[
                "minimum_calibrated_confidence"
            ]
        )

        self.margin_threshold = float(
            self.config[
                "minimum_calibrated_margin"
            ]
        )

        if (
            not math.isfinite(self.temperature)
            or self.temperature <= 0
        ):
            raise RuntimeError(
                "INVALID_TEMPERATURE"
            )

        if (
            not 0.0
            <= self.confidence_threshold
            <= 1.0
        ):
            raise RuntimeError(
                "INVALID_CONFIDENCE_THRESHOLD"
            )

        if (
            not 0.0
            <= self.margin_threshold
            <= 1.0
        ):
            raise RuntimeError(
                "INVALID_MARGIN_THRESHOLD"
            )

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
            self.EXPECTED_MODEL_NAME
        ):
            raise RuntimeError(
                "MODEL_NAME_MISMATCH"
            )

        if checkpoint.get("epoch") != (
            self.EXPECTED_CHECKPOINT_EPOCH
        ):
            raise RuntimeError(
                "CHECKPOINT_EPOCH_MISMATCH"
            )

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

        self.model = model.to(self.device)
        self.model.eval()

        preprocessing = self.config[
            "image_preprocessing"
        ]

        self.transform = transforms.Compose([
            transforms.Resize(
                int(
                    preprocessing[
                        "resize_size"
                    ]
                )
            ),
            transforms.CenterCrop(
                int(
                    preprocessing[
                        "crop_size"
                    ]
                )
            ),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=preprocessing[
                    "normalization"
                ]["mean"],
                std=preprocessing[
                    "normalization"
                ]["std"],
            ),
        ])

    def _abstain(
        self,
        code: str,
        predicted_class: Optional[str] = None,
        confidence: Optional[float] = None,
        margin: Optional[float] = None,
        probabilities: Optional[
            Dict[str, float]
        ] = None,
    ) -> ChilliPrediction:
        return ChilliPrediction(
            status="ABSTAINED",
            predicted_class=predicted_class,
            calibrated_confidence=confidence,
            calibrated_margin=margin,
            result_code=None,
            abstention_code=code,
            probabilities=(
                probabilities
                if probabilities is not None
                else {}
            ),
        )

    def predict(
        self,
        image: Image.Image,
    ) -> ChilliPrediction:
        try:
            image = image.convert("RGB")

            input_tensor = (
                self.transform(image)
                .unsqueeze(0)
                .to(self.device)
            )

            with torch.no_grad():
                logits = self.model(
                    input_tensor
                )

                probabilities_tensor = (
                    torch.softmax(
                        logits / self.temperature,
                        dim=1,
                    )[0]
                )

            probabilities = {
                self.index_to_class[index]: float(
                    probabilities_tensor[
                        index
                    ].item()
                )
                for index in range(
                    len(self.index_to_class)
                )
            }

            if not all(
                math.isfinite(value)
                for value in probabilities.values()
            ):
                return self._abstain(
                    "NON_FINITE_PROBABILITY"
                )

            sorted_predictions = sorted(
                probabilities.items(),
                key=lambda item: item[1],
                reverse=True,
            )

            predicted_class, confidence = (
                sorted_predictions[0]
            )

            second_confidence = (
                sorted_predictions[1][1]
            )

            margin = (
                confidence - second_confidence
            )

            if predicted_class not in (
                self.class_to_index
            ):
                return self._abstain(
                    "UNKNOWN_PREDICTED_CLASS",
                    predicted_class,
                    confidence,
                    margin,
                    probabilities,
                )

            if (
                confidence
                < self.confidence_threshold
            ):
                return self._abstain(
                    "CONFIDENCE_BELOW_THRESHOLD",
                    predicted_class,
                    confidence,
                    margin,
                    probabilities,
                )

            if margin < self.margin_threshold:
                return self._abstain(
                    "MARGIN_BELOW_THRESHOLD",
                    predicted_class,
                    confidence,
                    margin,
                    probabilities,
                )

            return ChilliPrediction(
                status=(
                    "ACCEPTED_RESTRICTED_RESULT"
                ),
                predicted_class=predicted_class,
                calibrated_confidence=confidence,
                calibrated_margin=margin,
                result_code=predicted_class,
                abstention_code=None,
                probabilities=probabilities,
            )

        except Exception:
            return ChilliPrediction(
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
