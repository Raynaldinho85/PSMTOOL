from __future__ import annotations

import importlib.util
from pathlib import Path

from psm_tool.ui.auth import require_auth


def test_require_auth_exists() -> None:
    assert callable(require_auth)


def test_pages_import_with_empty_app_password(monkeypatch) -> None:
    monkeypatch.delenv("APP_PASSWORD", raising=False)

    page_paths = [
        Path("src/psm_tool/ui/pages/1_upload.py"),
        Path("src/psm_tool/ui/pages/2_results.py"),
        Path("src/psm_tool/ui/pages/3_export.py"),
        Path("src/psm_tool/ui/pages/4_knowledge.py"),
    ]
    for page_path in page_paths:
        spec = importlib.util.spec_from_file_location(f"module_{page_path.stem}", page_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert hasattr(module, "main")
