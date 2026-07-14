#!/usr/bin/env python3
"""Experiment calibration module for UAV-AGV energy models."""

import csv
import matplotlib
import yaml

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

from src.energy.energy_model import EnergyModel


class ExperimentCalibrator:
    """Experiment calibrator for energy models.

    Note:
        Current calibration is SIMPLIFIED:
        - Only calculates a unified energy-per-distance ratio (k)
        - Cannot separately calibrate UAV cruise_energy_per_km and AGV agv_energy_per_km
          because experiment data doesn't distinguish between UAV and AGV measurements
        - Maps the unified k to both parameters as a best-effort approach
        - For proper separate calibration, experiment data should include:
          1. Entity type field (uav/agv)
          2. Separate measurements for UAV and AGV
    """
    
    def __init__(self, energy_model: EnergyModel):
        """Initialize experiment calibrator.
        
        Args:
            energy_model: Energy model to calibrate
        """
        self.energy_model = energy_model
        self.experiment_data = []
        self.calibration_params = {}
    
    def load_experiment_data(self, path: str) -> list:
        """Load experiment data from CSV file.
        
        Args:
            path: Path to experiment CSV file
            
        Returns:
            list: Loaded experiment data
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Experiment data file not found: {path}")
        
        data = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                for key, value in row.items():
                    try:
                        row[key] = float(value)
                    except ValueError:
                        pass
                data.append(row)
        
        self.experiment_data = data
        return data
    
    def calibrate(self, experiment_data: list = None) -> dict:
        """Calibrate energy model based on experiment data.
        
        Args:
            experiment_data: Experiment data to use for calibration. If None, uses loaded data.
            
        Returns:
            dict: Calibrated parameters
        """
        if experiment_data is None:
            experiment_data = self.experiment_data
        
        if not experiment_data:
            raise ValueError("No experiment data available for calibration")
        
        total_distance = 0.0
        total_energy = 0.0
        
        for data_point in experiment_data:
            if "distance" in data_point and "energy" in data_point:
                total_distance += data_point["distance"]
                total_energy += data_point["energy"]
        
        if total_distance > 0:
            calibrated_k = total_energy / total_distance
            
            self.calibration_params = {
                "cruise_energy_per_km": calibrated_k * 1000,
                "agv_energy_per_km": calibrated_k * 1000 * 0.6,
                "raw_k": calibrated_k,
            }
            
            self.energy_model.cruise_energy_per_km = self.calibration_params["cruise_energy_per_km"]
            self.energy_model.agv_energy_per_km = self.calibration_params["agv_energy_per_km"]
        
        return self.calibration_params
    
    def compare_sim_vs_real(self, output_path: str = None) -> dict:
        """Compare simulation results with real experiment data.
        
        Args:
            output_path: Path to save comparison plot
            
        Returns:
            dict: Comparison results
        """
        if not self.experiment_data:
            raise ValueError("No experiment data available for comparison")
        
        real_distances = []
        real_energies = []
        sim_energies = []
        
        for data_point in self.experiment_data:
            if "distance" in data_point and "energy" in data_point:
                distance = data_point["distance"]
                real_energy = data_point["energy"]
                
                # Calculate simulated energy
                # Create a mock UAV for simulation
                class MockUAV:
                    def __init__(self, distance):
                        self.position = (0, 0)
                        self.max_speed = 10  # 添加最大速度属性
                        self.max_payload = 5.0  # 添加最大负载属性
                        self.battery = 100.0  # 添加电池属性
                        self.task = type('obj', (object,), {
                            'start_point': (0, 0),
                            'end_point': (distance, 0)
                        })
                
                mock_uav = MockUAV(distance)
                sim_energy = self.energy_model.compute(mock_uav)
                
                real_distances.append(distance)
                real_energies.append(real_energy)
                sim_energies.append(sim_energy)
        
        # Generate comparison plot
        plt.figure(figsize=(10, 6))
        plt.scatter(real_distances, real_energies, label="Real Experiment", color="blue")
        plt.scatter(real_distances, sim_energies, label="Simulation", color="red")
        plt.plot(real_distances, real_energies, "b-", alpha=0.5)
        plt.plot(real_distances, sim_energies, "r-", alpha=0.5)
        plt.xlabel("Distance")
        plt.ylabel("Energy")
        plt.title("Simulation vs Real Experiment")
        plt.legend()
        plt.grid(True)
        
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(output_path)
            print(f"Comparison plot saved to: {output_path}")
        
        plt.close()
        
        # Calculate metrics
        mae = np.mean(np.abs(np.array(real_energies) - np.array(sim_energies)))
        rmse = np.sqrt(np.mean(np.square(np.array(real_energies) - np.array(sim_energies))))
        
        return {
            "mae": mae,
            "rmse": rmse,
            "real_distances": real_distances,
            "real_energies": real_energies,
            "sim_energies": sim_energies
        }
    
    def save_calibration(self, path: str):
        """Save calibration parameters to file.
        
        Args:
            path: Path to save calibration parameters
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.calibration_params, f, default_flow_style=False, allow_unicode=True)
        
        print(f"Calibration parameters saved to: {path}")
    
    def load_calibration(self, path: str):
        """Load calibration parameters from file.
        
        Args:
            path: Path to load calibration parameters from
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Calibration file not found: {path}")
        
        with open(path, "r", encoding="utf-8") as f:
            self.calibration_params = yaml.safe_load(f)
        
        # Update energy model parameters
        for param, value in self.calibration_params.items():
            if hasattr(self.energy_model, param):
                setattr(self.energy_model, param, value)
        
        print(f"Calibration parameters loaded from: {path}")


def main():
    """Main function for testing experiment calibration."""
    # Create energy model
    energy_model = EnergyModel()
    
    # Create calibrator
    calibrator = ExperimentCalibrator(energy_model)
    
    # Example usage
    print("Experiment Calibration Module")
    print("============================")
    
    # Load experiment data (example CSV format)
    print("\n1. Load experiment data")
    print("Expected CSV format:")
    print("distance,energy,velocity,altitude,payload")
    print("100,5.2,10,10,1.0")
    print("200,10.5,10,10,1.0")
    print("300,15.8,10,10,1.0")
    
    # Calibrate model
    print("\n2. Calibrate model")
    print("Calibration will calculate optimal parameters based on experiment data")
    
    # Compare simulation vs real
    print("\n3. Compare simulation vs real")
    print("Generates a plot comparing simulation results with real experiment data")
    
    # Save calibration
    print("\n4. Save calibration")
    print("Saves calibration parameters to a YAML file")
    
    # Load calibration
    print("\n5. Load calibration")
    print("Loads calibration parameters from a YAML file")


if __name__ == "__main__":
    main()
