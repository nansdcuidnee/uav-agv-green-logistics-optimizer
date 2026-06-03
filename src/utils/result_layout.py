from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence


REQUIRED_ARTIFACTS = (
    "metrics.json", 
    "records/steps.csv", 
    "records/tasks.csv", 
    "records/event_timeline.txt",
    "records/coordination_events.csv",
    "records/communication_log.csv",
    "plots/chart.png"
)

KEY_PLOTS = (
    "trajectory_map.png",
    "task_progress.png",
    "battery_status.png",
    "energy_curve.png",
    "kpi_summary.png",
    "coordination_events.png",
    "environment_state.png"
)


def sanitize_experiment_name(experiment_name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", (experiment_name or "").strip())
    cleaned = cleaned.strip("._-")
    return cleaned or "default"


@dataclass(frozen=True)
class ResultLayout:
    run_dir: Path
    plots_dir: Path
    logs_dir: Path
    records_dir: Path

    def artifact_path(self, filename: str) -> Path:
        return self.run_dir / filename

    def plot_path(self, filename: str) -> Path:
        return self.plots_dir / filename

    def record_path(self, filename: str) -> Path:
        return self.records_dir / filename

    def log_path(self, filename: str) -> Path:
        return self.logs_dir / filename


def create_result_layout(
    experiment_name: str = "default",
    *,
    timestamp: str | None = None,
    base_dir: str | Path = "results",
    result_type: str = "runs",
) -> ResultLayout:
    """创建结果目录布局
    
    Args:
        experiment_name: 实验名称
        timestamp: 时间戳
        base_dir: 基础目录
        result_type: 结果类型，可选值: experiments, comparisons, tests
    """
    result_dir = Path(base_dir) / result_type
    experiment_dir = result_dir / sanitize_experiment_name(experiment_name)
    run_timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = experiment_dir / run_timestamp
    plots_dir = run_dir / "plots"
    logs_dir = run_dir / "logs"
    records_dir = run_dir / "records"

    plots_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    records_dir.mkdir(parents=True, exist_ok=True)

    return ResultLayout(run_dir=run_dir, plots_dir=plots_dir, logs_dir=logs_dir, records_dir=records_dir)


def write_metadata(layout: ResultLayout, metadata: Mapping[str, Any]) -> str:
    metadata_path = layout.artifact_path("metadata.json")
    with metadata_path.open("w", encoding="utf-8") as file_obj:
        json.dump(metadata, file_obj, indent=2, ensure_ascii=False)
    return str(metadata_path)


def create_comparison_layout(
    compare_name: str = "default",
    *,
    timestamp: str | None = None,
    base_dir: str | Path = "results",
) -> ResultLayout:
    """创建对比结果目录布局
    
    Args:
        compare_name: 对比名称
        timestamp: 时间戳
        base_dir: 基础目录
    """
    return create_result_layout(
        experiment_name=compare_name,
        timestamp=timestamp,
        base_dir=base_dir,
        result_type="comparisons"
    )


def create_test_layout(
    test_name: str = "default",
    *,
    timestamp: str | None = None,
    base_dir: str | Path = "results",
) -> ResultLayout:
    """创建测试结果目录布局
    
    Args:
        test_name: 测试名称
        timestamp: 时间戳
        base_dir: 基础目录
    """
    return create_result_layout(
        experiment_name=test_name,
        timestamp=timestamp,
        base_dir=base_dir,
        result_type="tests"
    )


def list_relative_artifacts(layout: ResultLayout, paths: Sequence[Path]) -> list[str]:
    return [str(path.relative_to(layout.run_dir)) for path in paths]


def create_robustness_layout(
    campaign_name: str = "default",
    round_type: str = "round1_single_factor",
    *, 
    timestamp: str | None = None,
    base_dir: str | Path = "results",
) -> ResultLayout:
    """创建鲁棒性实验结果目录布局
    
    Args:
        campaign_name: 鲁棒性实验名称
        round_type: 轮次类型，可选值: round1_single_factor, round2_perturbation, round3_extreme_combo
        timestamp: 时间戳
        base_dir: 基础目录
    """
    result_dir = Path(base_dir) / "robustness" / sanitize_experiment_name(campaign_name)
    round_dir = result_dir / round_type
    run_timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = round_dir / run_timestamp
    plots_dir = run_dir / "plots"
    logs_dir = run_dir / "logs"
    records_dir = run_dir / "records"

    plots_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    records_dir.mkdir(parents=True, exist_ok=True)

    return ResultLayout(run_dir=run_dir, plots_dir=plots_dir, logs_dir=logs_dir, records_dir=records_dir)


def create_robustness_summary_layout(
    campaign_name: str = "default",
    *, 
    base_dir: str | Path = "results",
) -> Path:
    """创建鲁棒性实验汇总目录
    
    Args:
        campaign_name: 鲁棒性实验名称
        base_dir: 基础目录
    """
    summary_dir = Path(base_dir) / "robustness" / sanitize_experiment_name(campaign_name) / "summary"
    summary_dir.mkdir(parents=True, exist_ok=True)
    return summary_dir
