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

    @property
    def is_clean(self) -> bool:
        return self.status == "clean"


def _linear_cross(p1: float, p2: float, d1: float, d2: float) -> float:
    if np.isclose(d1, d2):
        return p1
    ratio = d1 / (d1 - d2)
    return p1 + ratio * (p2 - p1)


def _finite_slices(
    prices: np.ndarray, y_a: np.ndarray, y_b: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mask = np.isfinite(prices) & np.isfinite(y_a) & np.isfinite(y_b)
    return prices[mask], y_a[mask], y_b[mask]


def find_intersection(prices: np.ndarray, y_a: np.ndarray, y_b: np.ndarray) -> IntersectionResult:
    prices, y_a, y_b = _finite_slices(prices, y_a, y_b)
    if len(prices) == 0:
        return IntersectionResult(
            value=float("nan"), status="closest", message="No finite values available."
        )

    diff = y_a - y_b
    idx = 0
    while idx < len(prices) - 1:
        d1 = float(diff[idx])
        d2 = float(diff[idx + 1])
        p1 = float(prices[idx])
        p2 = float(prices[idx + 1])

        if np.isclose(d1, 0.0) and np.isclose(d2, 0.0):
            start = idx
            end = idx + 1
            while end < len(prices) and np.isclose(diff[end], 0.0):
                end += 1
            low = float(prices[start])
            high = float(prices[end - 1])
            return IntersectionResult(
                value=float((low + high) / 2.0),
                status="interval",
                low=low,
                high=high,
                message="Curves overlap across an interval.",
            )

        if np.isclose(d1, 0.0):
            return IntersectionResult(value=p1, status="clean")
        if d1 * d2 < 0.0 or np.isclose(d2, 0.0):
            return IntersectionResult(value=float(_linear_cross(p1, p2, d1, d2)), status="clean")
        idx += 1

    if np.isclose(diff[-1], 0.0):
        return IntersectionResult(value=float(prices[-1]), status="clean")

    closest_idx = int(np.argmin(np.abs(diff)))
    return IntersectionResult(
        value=float(prices[closest_idx]),
        status="closest",
        message="No clean intersection on the grid; closest approach returned.",
    )
