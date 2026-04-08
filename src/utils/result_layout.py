from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence


REQUIRED_ARTIFACTS = ("metrics.json", "records.csv", "chart.png")


def sanitize_experiment_name(experiment_name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", (experiment_name or "").strip())
    cleaned = cleaned.strip("._-")
    return cleaned or "default"


@dataclass(frozen=True)
class ResultLayout:
    run_dir: Path
    plots_dir: Path
    logs_dir: Path

    def artifact_path(self, filename: str) -> Path:
        return self.run_dir / filename

    def plot_path(self, filename: str) -> Path:
        return self.plots_dir / filename


def create_result_layout(
    experiment_name: str = "default",
    *,
    timestamp: str | None = None,
    base_dir: str | Path = "results",
) -> ResultLayout:
    experiment_dir = Path(base_dir) / sanitize_experiment_name(experiment_name)
    run_timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = experiment_dir / run_timestamp
    plots_dir = run_dir / "plots"
    logs_dir = run_dir / "logs"

    plots_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    return ResultLayout(run_dir=run_dir, plots_dir=plots_dir, logs_dir=logs_dir)


def write_metadata(layout: ResultLayout, metadata: Mapping[str, Any]) -> str:
    metadata_path = layout.artifact_path("metadata.json")
    with metadata_path.open("w", encoding="utf-8") as file_obj:
        json.dump(metadata, file_obj, indent=2, ensure_ascii=False)
    return str(metadata_path)


def list_relative_artifacts(layout: ResultLayout, paths: Sequence[Path]) -> list[str]:
    return [str(path.relative_to(layout.run_dir)) for path in paths]
