import csv
import json
from pathlib import Path

from src.core.agv import AGV
from src.core.task import Task
from src.core.uav import UAV
from src.simulation.environment import Environment
from src.utils.result_bundle import ResultGenerator


def _build_environment():
    environment = Environment(map_size=(100, 100))
    environment.uavs.append(UAV(1, (10, 10)))
    environment.agvs.append(AGV(1, (5, 5)))
    environment.tasks = [
        Task(id=1, start_point=(10, 10), end_point=(20, 20), payload=1.0, priority=1),
        Task(id=2, start_point=(15, 15), end_point=(25, 25), payload=1.5, priority=2),
    ]
    environment.delivery_points = [task.end_point for task in environment.tasks]
    return environment


def test_result_generator_writes_timestamped_run_directory():
    generator = ResultGenerator(
        _build_environment(),
        experiment_name="result_bundle_test",
        timestamp="20990101_010203",
    )

    result_paths = generator.generate_all()
    output_dir = Path(result_paths["output_dir"])

    assert output_dir.parent.name == "result_bundle_test"
    assert output_dir.name == "20990101_010203"
    assert (output_dir / "metrics.json").exists()
    assert (output_dir / "records.csv").exists()
    assert (output_dir / "chart.png").exists()
    assert (output_dir / "metadata.json").exists()
    assert (output_dir / "plots" / "environment_state.png").exists()


def test_result_generator_metadata_and_records_schema():
    generator = ResultGenerator(
        _build_environment(),
        experiment_name="result_bundle_schema_test",
        timestamp="20990101_020304",
    )

    result_paths = generator.generate_all()
    output_dir = Path(result_paths["output_dir"])

    with (output_dir / "metadata.json").open("r", encoding="utf-8") as file_obj:
        metadata = json.load(file_obj)

    assert metadata["records_granularity"] == "task"
    assert metadata["required_artifacts"] == ["metrics.json", "records.csv", "chart.png"]

    with (output_dir / "records.csv").open("r", encoding="utf-8") as file_obj:
        reader = csv.DictReader(file_obj)
        rows = list(reader)

    assert rows, "records.csv should contain task rows"
    assert "task_id" in rows[0]
    assert "path_distance" in rows[0]
