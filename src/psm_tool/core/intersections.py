from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class IntersectionResult:
    value: float
    status: str
    low: float | None = None
    high: float | None = None
    message: str | None = None


def _linear_cross(p1: float, p2: float, d1: float, d2: float) -> float:
    if d1 == d2:
        return p1
    ratio = d1 / (d1 - d2)
    return p1 + ratio * (p2 - p1)


def find_intersection(prices: np.ndarray, y_a: np.ndarray, y_b: np.ndarray) -> IntersectionResult:
    diff = y_a - y_b
    for idx in range(len(prices) - 1):
        d1 = diff[idx]
        d2 = diff[idx + 1]
        p1 = prices[idx]
        p2 = prices[idx + 1]

        if np.isclose(d1, 0.0) and np.isclose(d2, 0.0):
            return IntersectionResult(
                value=float((p1 + p2) / 2),
                status="interval",
                low=float(p1),
                high=float(p2),
                message="Curves overlap on an interval.",
            )
        if np.isclose(d1, 0.0):
            return IntersectionResult(value=float(p1), status="clean")
        if d1 * d2 < 0 or np.isclose(d2, 0.0):
            value = _linear_cross(float(p1), float(p2), float(d1), float(d2))
            return IntersectionResult(value=float(value), status="clean")

    closest_idx = int(np.argmin(np.abs(diff)))
    return IntersectionResult(
        value=float(prices[closest_idx]),
        status="closest",
        message="No clean intersection on the grid; closest approach returned.",
    )
