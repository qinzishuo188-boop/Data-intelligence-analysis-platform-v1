from __future__ import annotations

import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def resolve_service_path() -> Path:
    direct_path = ROOT / "平台服务.py"
    if direct_path.exists():
        return direct_path

    for candidate in ROOT.glob("*.py"):
        if candidate.name == Path(__file__).name:
            continue
        if "服务" in candidate.stem:
            return candidate

    raise FileNotFoundError("Cannot find the service script in the project folder.")


def main() -> None:
    service_path = resolve_service_path()
    runpy.run_path(str(service_path), run_name="__main__")


if __name__ == "__main__":
    main()
