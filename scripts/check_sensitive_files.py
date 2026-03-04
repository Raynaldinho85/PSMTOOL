from __future__ import annotations

import sys
from pathlib import Path, PurePosixPath

ALLOWED_PREFIXES = (
    PurePosixPath("src/psm_tool/resources"),
    PurePosixPath("tests/data"),
)
BLOCKED_SUFFIXES = {".sav", ".csv", ".xlsx"}


def as_repo_relative(path: str) -> PurePosixPath:
    return PurePosixPath(path.replace("\\", "/"))


def is_allowed_tabular_path(path: PurePosixPath) -> bool:
    return any(str(path).startswith(str(prefix) + "/") for prefix in ALLOWED_PREFIXES)


def should_block(path: PurePosixPath) -> str | None:
    if str(path) == "data_private" or str(path).startswith("data_private/"):
        return "anything under data_private/ is blocked"

    suffix = Path(path.name).suffix.lower()
    if suffix == ".sav":
        return ".sav files are blocked from commits"

    if suffix in {".csv", ".xlsx"} and not is_allowed_tabular_path(path):
        return f"{suffix} files are only allowed under src/psm_tool/resources/ or tests/data/"

    return None


def main(argv: list[str]) -> int:
    blocked: list[str] = []
    for raw_path in argv:
        path = as_repo_relative(raw_path)
        reason = should_block(path)
        if reason is not None:
            blocked.append(f"{path}: {reason}")

    if not blocked:
        return 0

    print("Commit blocked by data hygiene policy:", file=sys.stderr)
    for message in blocked:
        print(f" - {message}", file=sys.stderr)
    print(
        "Store private client files under data_private/ and keep synthetic fixtures only.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
