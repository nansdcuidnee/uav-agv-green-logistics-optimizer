#!/usr/bin/env python3
"""Generate network topology diagram."""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import networkx as nx
from pathlib import Path


def generate_network_topology(output_path):
    """Generate network topology diagram.
    
    Args:
        output_path: Path to save the diagram
    """
    # Create a directed graph
    G = nx.DiGraph()
    
    # Add nodes
    G.add_node("CONTROL_CENTER", pos=(0, 0), size=3000, color="red")
    G.add_node("UAV_1", pos=(1, 1), size=2000, color="blue")
    G.add_node("UAV_2", pos=(1, -1), size=2000, color="blue")
    G.add_node("AGV_1", pos=(-1, 1), size=2000, color="green")
    G.add_node("AGV_2", pos=(-1, -1), size=2000, color="green")
    
    # Add edges
    G.add_edge("CONTROL_CENTER", "UAV_1", label="TASK_ASSIGNMENT")
    G.add_edge("CONTROL_CENTER", "UAV_2", label="TASK_ASSIGNMENT")
    G.add_edge("CONTROL_CENTER", "AGV_1", label="RELAY_REQUEST")
    G.add_edge("CONTROL_CENTER", "AGV_2", label="RELAY_REQUEST")
    G.add_edge("UAV_1", "CONTROL_CENTER", label="STATUS_UPDATE")
    G.add_edge("UAV_2", "CONTROL_CENTER", label="STATUS_UPDATE")
    G.add_edge("AGV_1", "CONTROL_CENTER", label="STATUS_UPDATE")
    G.add_edge("AGV_2", "CONTROL_CENTER", label="STATUS_UPDATE")
    G.add_edge("UAV_1", "AGV_1", label="CHARGING_REQUEST")
    G.add_edge("UAV_2", "AGV_2", label="CHARGING_REQUEST")
    
    # Get positions
    pos = nx.get_node_attributes(G, "pos")
    
    # Draw nodes
    node_colors = [G.nodes[node]["color"] for node in G.nodes]
    node_sizes = [G.nodes[node]["size"] for node in G.nodes]
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, alpha=0.8)
    
    # Draw edges
    nx.draw_networkx_edges(G, pos, width=1.5, alpha=0.6)
    
    # Draw node labels
    nx.draw_networkx_labels(G, pos, font_size=12, font_weight="bold")
    
    # Draw edge labels
    edge_labels = nx.get_edge_attributes(G, "label")
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)
    
    # Set plot options
    plt.title("Network Topology: CONTROL_CENTER / UAV / AGV Communication")
    plt.axis("off")
    plt.tight_layout()
    
    # Save the plot
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"Network topology diagram saved to: {output_path}")
    
    plt.close()


def main():
    """Main function to generate network topology diagram."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate network topology diagram")
    parser.add_argument("--output", type=str, default="network_topology.png", help="Output file path")
    
    args = parser.parse_args()
    generate_network_topology(args.output)


if __name__ == "__main__":
    main()
