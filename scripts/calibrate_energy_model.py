#!/usr/bin/env python3
"""Script to calibrate energy model using experiment data."""

from src.energy.energy_model import EnergyModel
from src.energy.experiment_calibration import ExperimentCalibrator


def main():
    """Main function to calibrate energy model."""
    # Create energy model
    energy_model = EnergyModel()
    
    # Create calibrator
    calibrator = ExperimentCalibrator(energy_model)
    
    print("=== Energy Model Calibration ===")
    
    # 1. Load experiment data
    print("\n1. Loading experiment data...")
    try:
        experiment_data = calibrator.load_experiment_data("data/experiment_data.csv")
        print(f"Loaded {len(experiment_data)} data points from experiment data")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return
    
    # 2. Calibrate model
    print("\n2. Calibrating energy model...")
    calibration_params = calibrator.calibrate()
    print(f"Calibrated parameters: {calibration_params}")
    
    # 3. Compare simulation vs real
    print("\n3. Comparing simulation vs real experiment data...")
    comparison_results = calibrator.compare_sim_vs_real("results/calibration/sim_vs_real.png")
    print(f"Comparison results:")
    print(f"  Mean Absolute Error (MAE): {comparison_results['mae']:.4f}")
    print(f"  Root Mean Square Error (RMSE): {comparison_results['rmse']:.4f}")
    
    # 4. Save calibration
    print("\n4. Saving calibration parameters...")
    calibrator.save_calibration("data/constants/calibrated_params.yaml")
    
    print("\n=== Calibration Complete ===")
    print("You can now use the calibrated energy model for more accurate simulations.")


if __name__ == "__main__":
    main()
