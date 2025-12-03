#!/usr/bin/env python3
"""
Generate performance comparison plots from benchmark JSON files.
"""

import json
import os
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

# Configuration
GRAPH_DATA_FOLDER = "graph_data"
GRAPH_OUTPUT_FOLDER = "graph_output"

def load_json_files(folder_path):
    """Load all JSON files from the specified folder."""
    json_files = []
    folder = Path(folder_path)
    
    if not folder.exists():
        print(f"Warning: {folder_path} does not exist. Creating it...")
        folder.mkdir(parents=True, exist_ok=True)
        return json_files
    
    for file_path in folder.glob("*.json"):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                json_files.append(data)
                print(f"Loaded: {file_path.name}")
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
    
    return json_files

def extract_test_data(data, test_prefix, metric_key):
    """
    Extract test data for a specific test type and metric.
    
    Args:
        data: The JSON data dictionary
        test_prefix: Prefix of the test (e.g., 'seq_write_', 'rand_write_')
        metric_key: The metric to extract (e.g., 'speed_bytes_per_sec', 'iops')
    
    Returns:
        Dictionary mapping file_size to list of values
    """
    results = {}
    aggregated_stats = data.get('aggregated_statistics', {})
    
    for test_name, test_data in aggregated_stats.items():
        if test_name.startswith(test_prefix):
            # Get file size from test data if available
            file_size_data = test_data.get('file_size', {})
            if isinstance(file_size_data, dict) and file_size_data:
                file_size = file_size_data.get('mean', 0)
            else:
                # If not in data, extract from test name
                # Test name format: prefix_filesize (e.g., 'seq_write_10240')
                try:
                    file_size = int(test_name.replace(test_prefix, ''))
                except (ValueError, AttributeError):
                    print(f"Warning: Could not extract file size from test name: {test_name}")
                    continue
            
            # Get the metric values
            metric_data = test_data.get(metric_key, {})
            values = metric_data.get('values', [])
            
            if values and file_size > 0:
                results[int(file_size)] = values
            elif not values:
                print(f"Warning: No values found for {test_name} with metric {metric_key}")
    
    return results

def format_file_size(size_bytes):
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
    
    Returns:
        Formatted string (e.g., '10 KB', '1 MB', '500 MB')
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes // 1024} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        mb = size_bytes / (1024 * 1024)
        if mb >= 100:
            return f"{int(mb)} MB"
        else:
            return f"{mb:.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def extract_file_operation_data(data, operation_type, metric_key):
    """
    Extract file creation/deletion data.
    
    Args:
        data: The JSON data dictionary
        operation_type: 'file_creation' or 'file_deletion'
        metric_key: The metric to extract (e.g., 'files_per_sec')
    
    Returns:
        Dictionary with operation data
    """
    aggregated_stats = data.get('aggregated_statistics', {})
    operation_data = aggregated_stats.get(operation_type, {})
    
    if operation_data:
        num_files = operation_data.get('files_created' if operation_type == 'file_creation' else 'files_deleted', {}).get('mean', 0)
        metric_data = operation_data.get(metric_key, {})
        values = metric_data.get('values', [])
        
        if values:
            return {int(num_files): values}
    
    return {}

def create_box_plot(all_data, title, ylabel, xlabel, output_filename, format_x_as_filesize=False):
    """
    Create a box and whisker plot from the data.
    
    Args:
        all_data: Dictionary mapping test_name -> {file_size/num_files: [values]}
        title: Plot title
        ylabel: Y-axis label
        xlabel: X-axis label
        output_filename: Output file path
        format_x_as_filesize: If True, format x-axis labels as file sizes
    """
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Get all unique x-positions (file_size or num_files) across all tests
    all_x_positions = set()
    for test_data in all_data.values():
        all_x_positions.update(test_data.keys())
    x_positions = sorted(all_x_positions)
    
    # Prepare data for plotting
    num_tests = len(all_data)
    colors = plt.cm.Set3(np.linspace(0, 1, num_tests))
    
    # Calculate positions for grouped box plots
    width = 0.8 / num_tests  # Width of each box
    offset_start = -(num_tests - 1) * width / 2
    
    for idx, (test_name, test_data) in enumerate(all_data.items()):
        positions = []
        data_to_plot = []
        
        for x_pos in x_positions:
            if x_pos in test_data:
                # Offset position for this test
                positions.append(x_positions.index(x_pos) + offset_start + idx * width)
                data_to_plot.append(test_data[x_pos])
        
        if data_to_plot:
            bp = ax.boxplot(data_to_plot, positions=positions, widths=width * 0.8,
                           patch_artist=True, label=test_name,
                           boxprops=dict(facecolor=colors[idx], alpha=0.7),
                           medianprops=dict(color='red', linewidth=2),
                           whiskerprops=dict(linewidth=1.5),
                           capprops=dict(linewidth=1.5))
    
    # Set labels and title
    ax.set_xlabel(xlabel, fontsize=12, fontweight='bold')
    ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')
    ax.set_title(title, fontsize=14, fontweight='bold')
    
    # Set x-axis ticks
    ax.set_xticks(range(len(x_positions)))
    if format_x_as_filesize:
        ax.set_xticklabels([format_file_size(x) for x in x_positions], rotation=45, ha='right')
    else:
        ax.set_xticklabels([str(x) for x in x_positions])
    
    # Add legend
    ax.legend(loc='best', fontsize=10)
    
    # Add grid
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Tight layout
    plt.tight_layout()
    
    # Save the plot
    plt.savefig(output_filename, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_filename}")
    plt.close()

def main():
    """Main function to generate all plots."""
    # Create output folder if it doesn't exist
    output_folder = Path(GRAPH_OUTPUT_FOLDER)
    output_folder.mkdir(parents=True, exist_ok=True)
    
    # Load all JSON files
    print(f"\nLoading JSON files from {GRAPH_DATA_FOLDER}...")
    json_data_list = load_json_files(GRAPH_DATA_FOLDER)
    
    if not json_data_list:
        print(f"\nNo JSON files found in {GRAPH_DATA_FOLDER}/")
        print("Please add JSON benchmark files to this folder.")
        return
    
    print(f"\nLoaded {len(json_data_list)} JSON file(s)")
    print("\nGenerating plots...\n")
    
    # 1. Sequential Write Performance (MB/s)
    seq_write_data = {}
    for data in json_data_list:
        test_name = data.get('name', 'Unknown')
        # Convert bytes/sec to MB/sec
        raw_data = extract_test_data(data, 'seq_write_', 'speed_bytes_per_sec')
        seq_write_data[test_name] = {k: [v / (1024 * 1024) for v in vals] 
                                      for k, vals in raw_data.items()}
    
    create_box_plot(
        seq_write_data,
        "Sequential Write Performance",
        "Speed (MB/s)",
        "File Size",
        output_folder / "sequential_write_performance.png",
        format_x_as_filesize=True
    )
    
    # 2. Sequential Read Performance (MB/s)
    seq_read_data = {}
    for data in json_data_list:
        test_name = data.get('name', 'Unknown')
        # Convert bytes/sec to MB/sec
        raw_data = extract_test_data(data, 'seq_read_', 'speed_bytes_per_sec')
        seq_read_data[test_name] = {k: [v / (1024 * 1024) for v in vals] 
                                     for k, vals in raw_data.items()}
    
    create_box_plot(
        seq_read_data,
        "Sequential Read Performance",
        "Speed (MB/s)",
        "File Size",
        output_folder / "sequential_read_performance.png",
        format_x_as_filesize=True
    )
    
    # 3. Random Write Test (IOPS)
    rand_write_data = {}
    for data in json_data_list:
        test_name = data.get('name', 'Unknown')
        # For random write, extract file size from test name
        rand_write_data[test_name] = extract_test_data(data, 'rand_write_', 'iops')
    
    create_box_plot(
        rand_write_data,
        "Random Write Performance",
        "IOPS",
        "File Size",
        output_folder / "random_write_performance.png",
        format_x_as_filesize=True
    )
    
    # 4. Random Read Test (IOPS)
    rand_read_data = {}
    for data in json_data_list:
        test_name = data.get('name', 'Unknown')
        # For random read, extract file size from test name
        rand_read_data[test_name] = extract_test_data(data, 'rand_read_', 'iops')
    
    create_box_plot(
        rand_read_data,
        "Random Read Performance",
        "IOPS",
        "File Size",
        output_folder / "random_read_performance.png",
        format_x_as_filesize=True
    )
    
    # 5. File Creation Performance
    file_creation_data = {}
    for data in json_data_list:
        test_name = data.get('name', 'Unknown')
        file_creation_data[test_name] = extract_file_operation_data(data, 'file_creation', 'files_per_sec')
    
    create_box_plot(
        file_creation_data,
        "File Creation Performance",
        "Files per Second",
        "Number of Files Created",
        output_folder / "file_creation_performance.png"
    )
    
    # 6. File Deletion Performance
    file_deletion_data = {}
    for data in json_data_list:
        test_name = data.get('name', 'Unknown')
        file_deletion_data[test_name] = extract_file_operation_data(data, 'file_deletion', 'files_per_sec')
    
    create_box_plot(
        file_deletion_data,
        "File Deletion Performance",
        "Files per Second",
        "Number of Files Deleted",
        output_folder / "file_deletion_performance.png"
    )
    
    print("\n✓ All plots generated successfully!")
    print(f"  Output folder: {output_folder.absolute()}\n")

if __name__ == "__main__":
    main()
