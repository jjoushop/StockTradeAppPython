from __future__ import annotations

from pathlib import Path
from typing import Any


def write_spreadsheet(df: Any, output_file: str | Path) -> Path:
    path = Path(output_file)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.suffix.lower() == ".xlsx":
        df.to_excel(path, index=False)
    else:
        df.to_csv(path, index=False)

    return path
