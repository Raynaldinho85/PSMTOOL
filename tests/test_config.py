from psm_tool.config import GridConfig


def test_grid_defaults_snap_on_with_currency_map() -> None:
    cfg = GridConfig()
    assert cfg.mode == "auto"
    assert cfg.snap_enabled is True
    assert cfg.currency_snap["EUR"] == 5.0
    assert cfg.currency_snap["SEK"] == 20.0
    assert cfg.currency_snap["CHF"] == 5.0
