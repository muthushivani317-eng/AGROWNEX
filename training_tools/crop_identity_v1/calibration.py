from __future__ import annotations

import torch
from torch import nn


def fit_temperature(logits: torch.Tensor, labels: torch.Tensor) -> tuple[float, float, float]:
    if logits.ndim != 2 or labels.ndim != 1 or len(logits) != len(labels):
        raise ValueError("LOGIT_LABEL_SHAPE_MISMATCH")
    before = float(nn.functional.cross_entropy(logits, labels))
    log_temperature = torch.zeros((), dtype=torch.float64, requires_grad=True)
    logits64 = logits.detach().double()
    optimizer = torch.optim.LBFGS([log_temperature], lr=0.1, max_iter=100)

    def closure():
        optimizer.zero_grad()
        loss = nn.functional.cross_entropy(logits64 / log_temperature.exp(), labels)
        loss.backward()
        return loss

    optimizer.step(closure)
    temperature = float(log_temperature.detach().exp())
    after = float(nn.functional.cross_entropy(logits64 / temperature, labels))
    if after > before + 1e-9:
        raise RuntimeError("CALIBRATION_NLL_REGRESSION")
    return temperature, before, after


def calibrated_probabilities(logits: torch.Tensor, temperature: float) -> torch.Tensor:
    if temperature <= 0:
        raise ValueError("TEMPERATURE_MUST_BE_POSITIVE")
    return torch.softmax(logits / temperature, dim=1)
