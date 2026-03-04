from __future__ import annotations

import numpy as np

from psm_tool.core.intersections import find_intersection


def test_clean_intersection_uses_linear_interpolation() -> None:
    prices = np.array([0.0, 1.0])
    y1 = np.array([10.0, 0.0])
    y2 = np.array([0.0, 10.0])
    result = find_intersection(prices, y1, y2)
    assert result.status == "clean"
    assert result.value == 0.5


def test_overlap_returns_interval_status() -> None:
    prices = np.array([1.0, 2.0, 3.0])
    y1 = np.array([50.0, 50.0, 40.0])
    y2 = np.array([50.0, 50.0, 30.0])
    result = find_intersection(prices, y1, y2)
    assert result.status == "interval"
    assert result.low == 1.0
    assert result.high == 2.0
    assert result.value == 1.5


def test_no_crossing_returns_closest_status() -> None:
    prices = np.array([1.0, 2.0, 3.0, 4.0])
    y1 = np.array([80.0, 70.0, 60.0, 55.0])
    y2 = np.array([20.0, 30.0, 40.0, 49.0])
    result = find_intersection(prices, y1, y2)
    assert result.status == "closest"
    assert result.value == 4.0
