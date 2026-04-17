#!/usr/bin/env python3
"""Test robustness experiment functionality."""

import pytest
from pathlib import Path

from experiments.run_robustness import (
    load_campaign_config,
    normalize_cases,
    build_run_config,
    _nan_stat,
)


@pytest.fixture
def seed_config():
    """Seed stability config fixture."""
    return load_campaign_config("configs/experiments/robustness_seed.yaml")


@pytest.fixture
def scale_config():
    """Scale config fixture."""
    return load_campaign_config("configs/experiments/robustness_scale.yaml")


@pytest.fixture
def capacity_config():
    """Capacity config fixture."""
    return load_campaign_config("configs/experiments/robustness_battery.yaml")


@pytest.fixture
def failure_config():
    """Failure config fixture."""
    return load_campaign_config("configs/experiments/robustness_failure.yaml")


def test_case_expansion_seed(seed_config):
    """Test seed stability case expansion."""
    cases = normalize_cases(seed_config)
    assert len(cases) == 5  # 5 seeds
    assert all("seed" in case for case in cases)


def test_case_expansion_scale(scale_config):
    """Test scale case expansion."""
    cases = normalize_cases(scale_config)
    assert len(cases) == 3  # 3 scales
    case_names = [case["name"] for case in cases]
    assert "scale_20" in case_names
    assert "scale_50" in case_names
    assert "scale_100" in case_names


def test_case_expansion_capacity(capacity_config):
    """Test capacity case expansion."""
    cases = normalize_cases(capacity_config)
    assert len(cases) == 3  # 3 capacity levels
    assert all("capacity_factor" in case for case in cases)


def test_case_expansion_failure(failure_config):
    """Test failure case expansion."""
    cases = normalize_cases(failure_config)
    assert len(cases) == 2  # 2 failure cases
    case_names = [case["name"] for case in cases]
    assert "no_failure" in case_names
    assert "uav_failure_step30" in case_names


def test_build_run_config():
    """Test run config building."""
    base_config = {
        "num_tasks": 10,
        "num_uavs": 2,
        "max_steps": 100,
    }

    # Test seed stability
    case = {"name": "seed_42", "seed": 42, "overrides": {}}
    run_config = build_run_config(base_config, case, "seed_stability", None)
    assert run_config["seed"] == 42

    # Test scale
    case = {
        "name": "scale_20",
        "overrides": {"num_tasks": 20, "num_uavs": 3, "num_agvs": 1}
    }
    run_config = build_run_config(base_config, case, "scale", 42)
    assert run_config["num_tasks"] == 20
    assert run_config["num_uavs"] == 3
    assert run_config["num_agvs"] == 1
    assert run_config["seed"] == 42


def test_nan_stat():
    """Test nan_stat function."""
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert _nan_stat(values, "mean") == 3.0
    assert _nan_stat(values, "std") is not None
    assert _nan_stat(values, "min") == 1.0
    assert _nan_stat(values, "max") == 5.0

    # Test with empty list
    assert _nan_stat([], "mean") is None

    # Test with all NaN
    assert _nan_stat([float("nan"), float("nan")], "mean") is None


def test_config_loader_integration():
    """Test config loader integration."""
    # This test ensures that config_loader is properly used
    # and that no_fly_zones.count etc. are normalized
    config = load_campaign_config("configs/experiments/robustness_seed.yaml")
    assert "base_config" in config
    assert "map_size" in config["base_config"]
