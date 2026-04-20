from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

import plotly.graph_objects as go

HIGH_PRIORITY_LABELS = {"opp", "idp", "maxrevenue"}
MEDIUM_PRIORITY_LABELS = {"pmi", "pme", "maxtrial"}
LOW_PRIORITY_LABELS = {"tested price", "tested_price"}


@dataclass(frozen=True, slots=True)
class PriceBenchmark:
    label: str
    price: float
    key: str | None = None
    color: str = "#7c3aed"
    line_dash: str = "dash"
    line_width: int = 2
    preferred_side: str = "right"
    label_y: float = 1.004
    label_shift: int = 6


@dataclass(frozen=True, slots=True)
class _MarkerLayout:
    side: str
    y: float


def is_valid_tested_price(value: object) -> bool:
    if value is None:
        return False
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(numeric) and numeric > 0.0


def annotation_anchor_for_side(side: str, *, shift: int = 6) -> tuple[str, int]:
    if side == "left":
        return "right", -abs(int(shift))
    return "left", abs(int(shift))


def _preferred_side(marker: PriceBenchmark) -> str:
    return marker.preferred_side if marker.preferred_side in {"left", "right"} else "right"


def _manual_side(
    marker: PriceBenchmark,
    label_side_overrides: Mapping[str, Literal["left", "right"]] | None,
) -> str | None:
    if not marker.key or not label_side_overrides:
        return None
    side = label_side_overrides.get(marker.key)
    return side if side in {"left", "right"} else None


def _marker_priority(marker: PriceBenchmark) -> int:
    marker_name = str(marker.key or marker.label).strip().lower()
    label = str(marker.label).strip().lower()
    if marker_name in HIGH_PRIORITY_LABELS or label.startswith("maximum turnover"):
        return 0
    if marker_name in MEDIUM_PRIORITY_LABELS:
        return 1
    if marker_name in LOW_PRIORITY_LABELS or label in LOW_PRIORITY_LABELS:
        return 2
    return 1


def _finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _iter_finite_trace_x_values(fig: go.Figure) -> list[float]:
    values: list[float] = []
    for trace in fig.data:
        x_values = getattr(trace, "x", None)
        if x_values is None:
            continue
        for value in x_values:
            number = _finite_float(value)
            if number is not None:
                values.append(number)
    return values


def _layout_x_range(fig: go.Figure, markers: Sequence[PriceBenchmark]) -> tuple[float, float]:
    axis_range = getattr(fig.layout.xaxis, "range", None)
    if axis_range and len(axis_range) >= 2:
        left = _finite_float(axis_range[0])
        right = _finite_float(axis_range[1])
        if left is not None and right is not None and left != right:
            return min(left, right), max(left, right)

    values = _iter_finite_trace_x_values(fig)
    for marker in markers:
        number = _finite_float(marker.price)
        if number is not None:
            values.append(number)
    if not values:
        return 0.0, 1.0
    left = min(values)
    right = max(values)
    if left == right:
        pad = max(abs(left) * 0.1, 1.0)
        return left - pad, right + pad
    return left, right


def _label_clearance(marker: PriceBenchmark, span: float) -> float:
    label_len = len(str(marker.label))
    if label_len <= 6:
        return max(span * 0.035, 3.0)
    if label_len <= 18:
        return max(span * 0.055, 5.0)
    return max(span * 0.09, 7.0)


def _edge_adjusted_side(
    marker: PriceBenchmark,
    *,
    x_min: float,
    x_max: float,
    span: float,
    label_side_overrides: Mapping[str, Literal["left", "right"]] | None,
) -> tuple[str, bool]:
    manual_side = _manual_side(marker, label_side_overrides)
    if manual_side is not None:
        return manual_side, False

    side = _preferred_side(marker)
    price = float(marker.price)
    clearance = _label_clearance(marker, span)
    near_left = (price - x_min) <= clearance
    near_right = (x_max - price) <= clearance
    if near_left and not near_right:
        return "right", True
    if near_right and not near_left:
        return "left", True
    return side, False


def _cluster_threshold(
    left: PriceBenchmark,
    right: PriceBenchmark,
    *,
    span: float,
    collision_distance: float | None,
) -> float:
    if collision_distance is not None:
        return max(float(collision_distance), 0.0)
    return max(_label_clearance(left, span), _label_clearance(right, span))


def _colliding_marker_clusters(
    indexed_markers: list[tuple[int, PriceBenchmark]],
    *,
    span: float,
    collision_distance: float | None,
) -> list[list[tuple[int, PriceBenchmark]]]:
    if not indexed_markers:
        return []
    ordered = sorted(indexed_markers, key=lambda item: (float(item[1].price), item[0]))
    clusters: list[list[tuple[int, PriceBenchmark]]] = []
    current = [ordered[0]]
    for item in ordered[1:]:
        previous = current[-1][1]
        marker = item[1]
        distance = abs(float(marker.price) - float(previous.price))
        threshold = _cluster_threshold(
            previous,
            marker,
            span=span,
            collision_distance=collision_distance,
        )
        if distance <= threshold:
            current.append(item)
        else:
            clusters.append(current)
            current = [item]
    clusters.append(current)
    return clusters


def _opposite_side(side: str) -> str:
    return "left" if side == "right" else "right"


def _side_conflicts(
    *,
    side: str,
    marker: PriceBenchmark,
    assignments: dict[int, str],
    markers_by_idx: dict[int, PriceBenchmark],
    span: float,
    collision_distance: float | None,
) -> bool:
    for other_idx, other_candidate in assignments.items():
        other_marker = markers_by_idx[other_idx]
        distance = abs(float(marker.price) - float(other_marker.price))
        threshold = _cluster_threshold(
            marker,
            other_marker,
            span=span,
            collision_distance=collision_distance,
        )
        if distance > threshold:
            continue
        if side == other_candidate:
            return True
    return False


def _resolve_cluster_assignments(
    cluster: list[tuple[int, PriceBenchmark]],
    *,
    base_sides: list[str],
    edge_locked: list[bool],
    span: float,
    collision_distance: float | None,
) -> dict[int, str]:
    markers_by_idx = dict(cluster)
    assignments: dict[int, str] = {}
    priority_order = sorted(
        cluster,
        key=lambda item: (_marker_priority(item[1]), float(item[1].price), item[0]),
    )
    for idx, marker in priority_order:
        candidates = (
            [base_sides[idx]]
            if edge_locked[idx]
            else [
                base_sides[idx],
                _opposite_side(base_sides[idx]),
            ]
        )
        for candidate_side in candidates:
            if not _side_conflicts(
                side=candidate_side,
                marker=marker,
                assignments=assignments,
                markers_by_idx=markers_by_idx,
                span=span,
                collision_distance=collision_distance,
            ):
                assignments[idx] = candidate_side
                break
        else:
            assignments[idx] = base_sides[idx]
    return assignments


def _resolve_marker_label_layouts(
    markers: Sequence[PriceBenchmark],
    *,
    x_range: tuple[float, float],
    collision_distance: float | None = None,
    label_side_overrides: Mapping[str, Literal["left", "right"]] | None = None,
) -> list[_MarkerLayout]:
    layouts = [_MarkerLayout(side=_preferred_side(marker), y=marker.label_y) for marker in markers]
    finite_markers = [
        (idx, marker) for idx, marker in enumerate(markers) if math.isfinite(float(marker.price))
    ]
    if not finite_markers:
        return layouts

    x_min, x_max = x_range
    span = max(x_max - x_min, 1.0)
    sides: list[str] = []
    edge_locked: list[bool] = []
    side_locked: list[bool] = []
    for marker in markers:
        if math.isfinite(float(marker.price)):
            manual_side = _manual_side(marker, label_side_overrides)
            side, locked = _edge_adjusted_side(
                marker,
                x_min=x_min,
                x_max=x_max,
                span=span,
                label_side_overrides=label_side_overrides,
            )
            sides.append(side)
            edge_locked.append(locked or manual_side is not None)
            side_locked.append(manual_side is not None)
        else:
            sides.append(_preferred_side(marker))
            edge_locked.append(False)
            side_locked.append(False)

    clusters = _colliding_marker_clusters(
        finite_markers,
        span=span,
        collision_distance=collision_distance,
    )
    for cluster in clusters:
        if len(cluster) < 2:
            continue
        assignments = _resolve_cluster_assignments(
            cluster,
            base_sides=sides,
            edge_locked=edge_locked,
            span=span,
            collision_distance=collision_distance,
        )
        for idx, side in assignments.items():
            if not side_locked[idx]:
                sides[idx] = side

    return [
        _MarkerLayout(
            side=side,
            y=marker.label_y,
        )
        for idx, (marker, side) in enumerate(zip(markers, sides, strict=True))
    ]


def resolve_marker_label_sides(
    markers: Sequence[PriceBenchmark],
    *,
    collision_distance: float | None = None,
) -> list[str]:
    marker_prices = [
        float(marker.price) for marker in markers if math.isfinite(float(marker.price))
    ]
    if not marker_prices:
        return [_preferred_side(marker) for marker in markers]
    x_min = min(marker_prices)
    x_max = max(marker_prices)
    if x_min == x_max:
        x_min -= 1.0
        x_max += 1.0
    else:
        pad = max((x_max - x_min) * 0.2, 8.0)
        x_min -= pad
        x_max += pad
    layouts = _resolve_marker_label_layouts(
        markers,
        x_range=(x_min, x_max),
        collision_distance=collision_distance,
    )
    return [layout.side for layout in layouts]


def add_vertical_price_markers(
    fig: go.Figure,
    markers: Sequence[PriceBenchmark] | None,
    *,
    collision_distance: float | None = None,
    label_side_overrides: Mapping[str, Literal["left", "right"]] | None = None,
) -> None:
    if not markers:
        return

    finite_markers = [marker for marker in markers if math.isfinite(float(marker.price))]
    x_range = _layout_x_range(fig, finite_markers)
    layouts = _resolve_marker_label_layouts(
        finite_markers,
        x_range=x_range,
        collision_distance=collision_distance,
        label_side_overrides=label_side_overrides,
    )
    for marker, layout in zip(finite_markers, layouts, strict=False):
        fig.add_vline(
            x=float(marker.price),
            line_dash=marker.line_dash,
            line_width=marker.line_width,
            line_color=marker.color,
        )
        xanchor, xshift = annotation_anchor_for_side(layout.side, shift=marker.label_shift)
        fig.add_annotation(
            x=float(marker.price),
            y=layout.y,
            xref="x",
            yref="paper",
            text=marker.label,
            showarrow=False,
            xanchor=xanchor,
            yanchor="bottom",
            xshift=xshift,
            align="left",
            font={"size": 12, "color": marker.color},
        )
