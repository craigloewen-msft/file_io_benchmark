#!/usr/bin/env python3
"""
File I/O Performance Testing Script

Tests various file I/O operations with different file sizes and patterns
to measure storage performance characteristics.
"""

import os
import time
import shutil
import random
import statistics
from pathlib import Path
from typing import Dict, List, Tuple
import json


class FileIOBenchmark:
    def __init__(self, test_dir: str = "benchmark_temp", data_size_gb: float = 2.0):
        self.test_dir = Path(test_dir)
        self.data_size_gb = data_size_gb
        self.results = {}
        self.all_runs = []  # Store results from all runs
        
    def setup(self):
        """Create test directory"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(parents=True)
        
    def cleanup(self):
        """Remove test directory"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def _generate_data(self, size_bytes: int) -> bytes:
        """Generate random data of specified size"""
        return os.urandom(size_bytes)
    
    def _format_size(self, size_bytes: int) -> str:
        """Format bytes to human readable size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    def _format_speed(self, bytes_per_sec: float) -> str:
        """Format speed to human readable format"""
        return self._format_size(bytes_per_sec) + "/s"
    
    def test_sequential_write(self, file_size: int, block_size: int = 64*1024) -> Dict:
        """Test sequential write performance"""
        filepath = self.test_dir / "sequential_write_test.bin"
        data_block = self._generate_data(block_size)
        blocks_to_write = file_size // block_size
        
        start_time = time.time()
        with open(filepath, 'wb') as f:
            for _ in range(blocks_to_write):
                f.write(data_block)
            f.flush()
            os.fsync(f.fileno())  # Ensure data is written to disk
        
        elapsed = time.time() - start_time
        speed = file_size / elapsed if elapsed > 0 else 0
        
        filepath.unlink()
        
        return {
            'duration_sec': elapsed,
            'speed_bytes_per_sec': speed,
            'speed_formatted': self._format_speed(speed)
        }
    
    def test_sequential_read(self, file_size: int, block_size: int = 64*1024) -> Dict:
        """Test sequential read performance"""
        filepath = self.test_dir / "sequential_read_test.bin"
        
        # First create the file
        data_block = self._generate_data(block_size)
        blocks_to_write = file_size // block_size
        with open(filepath, 'wb') as f:
            for _ in range(blocks_to_write):
                f.write(data_block)
        
        # Clear file cache by reopening
        # Note: True cache clearing requires OS-specific commands
        
        start_time = time.time()
        with open(filepath, 'rb') as f:
            while f.read(block_size):
                pass
        
        elapsed = time.time() - start_time
        speed = file_size / elapsed if elapsed > 0 else 0
        
        filepath.unlink()
        
        return {
            'duration_sec': elapsed,
            'speed_bytes_per_sec': speed,
            'speed_formatted': self._format_speed(speed)
        }
    
    def test_random_write(self, file_size: int, num_operations: int = 1000, 
                         block_size: int = 4096) -> Dict:
        """Test random write performance (IOPS)"""
        filepath = self.test_dir / "random_write_test.bin"
        
        # Pre-allocate file
        with open(filepath, 'wb') as f:
            f.seek(file_size - 1)
            f.write(b'\0')
        
        data_block = self._generate_data(block_size)
        max_offset = file_size - block_size
        
        start_time = time.time()
        with open(filepath, 'r+b') as f:
            for _ in range(num_operations):
                offset = random.randint(0, max_offset // block_size) * block_size
                f.seek(offset)
                f.write(data_block)
            f.flush()
            os.fsync(f.fileno())
        
        elapsed = time.time() - start_time
        iops = num_operations / elapsed if elapsed > 0 else 0
        latency_ms = (elapsed / num_operations * 1000) if num_operations > 0 else 0
        
        filepath.unlink()
        
        return {
            'duration_sec': elapsed,
            'iops': iops,
            'avg_latency_ms': latency_ms,
            'operations': num_operations
        }
    
    def test_random_read(self, file_size: int, num_operations: int = 1000,
                        block_size: int = 4096) -> Dict:
        """Test random read performance (IOPS)"""
        filepath = self.test_dir / "random_read_test.bin"
        
        # Create file with random data
        with open(filepath, 'wb') as f:
            data = self._generate_data(file_size)
            f.write(data)
        
        max_offset = file_size - block_size
        
        start_time = time.time()
        with open(filepath, 'rb') as f:
            for _ in range(num_operations):
                offset = random.randint(0, max_offset // block_size) * block_size
                f.seek(offset)
                f.read(block_size)
        
        elapsed = time.time() - start_time
        iops = num_operations / elapsed if elapsed > 0 else 0
        latency_ms = (elapsed / num_operations * 1000) if num_operations > 0 else 0
        
        filepath.unlink()
        
        return {
            'duration_sec': elapsed,
            'iops': iops,
            'avg_latency_ms': latency_ms,
            'operations': num_operations
        }
    
    def test_file_creation(self, num_files: int = 1000, file_size: int = 4096) -> Dict:
        """Test small file creation performance (metadata operations)"""
        data = self._generate_data(file_size)
        
        start_time = time.time()
        for i in range(num_files):
            filepath = self.test_dir / f"small_file_{i}.bin"
            with open(filepath, 'wb') as f:
                f.write(data)
        
        elapsed = time.time() - start_time
        files_per_sec = num_files / elapsed if elapsed > 0 else 0
        
        return {
            'duration_sec': elapsed,
            'files_created': num_files,
            'files_per_sec': files_per_sec,
            'avg_time_per_file_ms': (elapsed / num_files * 1000) if num_files > 0 else 0
        }
    
    def test_file_deletion(self, num_files: int = 1000) -> Dict:
        """Test file deletion performance"""
        # Files should already exist from creation test
        files = list(self.test_dir.glob("small_file_*.bin"))
        actual_count = len(files)
        
        start_time = time.time()
        for filepath in files:
            filepath.unlink()
        
        elapsed = time.time() - start_time
        files_per_sec = actual_count / elapsed if elapsed > 0 else 0
        
        return {
            'duration_sec': elapsed,
            'files_deleted': actual_count,
            'files_per_sec': files_per_sec,
            'avg_time_per_file_ms': (elapsed / actual_count * 1000) if actual_count > 0 else 0
        }
    
    def run_benchmark_suite(self):
        """Run complete benchmark suite"""
        print("=" * 70)
        print("FILE I/O PERFORMANCE BENCHMARK")
        print("=" * 70)
        print(f"Test Directory: {self.test_dir.absolute()}")
        print()
        
        self.results = {}  # Reset results for this run
        
        try:
            self.setup()
            
            # Define test configurations - all tests write the same total amount
            total_data_size = int(self.data_size_gb * 1024 * 1024 * 1024)
            test_configs = [
                ('Small Files (10 MB each)', 10 * 1024 * 1024, total_data_size // (10 * 1024 * 1024)),
                ('Medium Files (100 MB each)', 100 * 1024 * 1024, total_data_size // (100 * 1024 * 1024)),
                ('Large Files (500 MB each)', 500 * 1024 * 1024, total_data_size // (500 * 1024 * 1024)),
                ('Very Large Files (1 GB each)', 1024 * 1024 * 1024, total_data_size // (1024 * 1024 * 1024)),
            ]
            
            # Sequential Write Tests
            print("\n" + "=" * 70)
            print(f"SEQUENTIAL WRITE TESTS ({self.data_size_gb} GB total per test)")
            print("=" * 70)
            for name, size, num_files in test_configs:
                print(f"\nTesting {name} ({num_files} file(s))...")
                total_time = 0
                total_bytes = 0
                for i in range(num_files):
                    result = self.test_sequential_write(size)
                    total_time += result['duration_sec']
                    total_bytes += size
                
                avg_speed = total_bytes / total_time if total_time > 0 else 0
                self.results[f'seq_write_{size}'] = {
                    'duration_sec': total_time,
                    'speed_bytes_per_sec': avg_speed,
                    'speed_formatted': self._format_speed(avg_speed),
                    'num_files': num_files,
                    'total_bytes': total_bytes
                }
                print(f"  Total Duration: {total_time:.3f} seconds")
                print(f"  Average Speed: {self._format_speed(avg_speed)}")
                print(f"  Files Written: {num_files}")
            
            # Sequential Read Tests
            print("\n" + "=" * 70)
            print(f"SEQUENTIAL READ TESTS ({self.data_size_gb} GB total per test)")
            print("=" * 70)
            for name, size, num_files in test_configs:
                print(f"\nTesting {name} ({num_files} file(s))...")
                total_time = 0
                total_bytes = 0
                for i in range(num_files):
                    result = self.test_sequential_read(size)
                    total_time += result['duration_sec']
                    total_bytes += size
                
                avg_speed = total_bytes / total_time if total_time > 0 else 0
                self.results[f'seq_read_{size}'] = {
                    'duration_sec': total_time,
                    'speed_bytes_per_sec': avg_speed,
                    'speed_formatted': self._format_speed(avg_speed),
                    'num_files': num_files,
                    'total_bytes': total_bytes
                }
                print(f"  Total Duration: {total_time:.3f} seconds")
                print(f"  Average Speed: {self._format_speed(avg_speed)}")
                print(f"  Files Read: {num_files}")
            
            # Random Write Tests
            print("\n" + "=" * 70)
            print("RANDOM WRITE TESTS (4KB blocks)")
            print("=" * 70)
            random_test_configs = [
                ('100 MB file', 100 * 1024 * 1024, 5000),
                ('500 MB file', 500 * 1024 * 1024, 10000),
            ]
            for name, size, ops in random_test_configs:
                print(f"\nTesting {name} ({ops} operations)...")
                result = self.test_random_write(size, ops)
                self.results[f'rand_write_{size}'] = result
                print(f"  Duration: {result['duration_sec']:.3f} seconds")
                print(f"  IOPS: {result['iops']:.2f}")
                print(f"  Avg Latency: {result['avg_latency_ms']:.3f} ms")
            
            # Random Read Tests
            print("\n" + "=" * 70)
            print("RANDOM READ TESTS (4KB blocks)")
            print("=" * 70)
            for name, size, ops in random_test_configs:
                print(f"\nTesting {name} ({ops} operations)...")
                result = self.test_random_read(size, ops)
                self.results[f'rand_read_{size}'] = result
                print(f"  Duration: {result['duration_sec']:.3f} seconds")
                print(f"  IOPS: {result['iops']:.2f}")
                print(f"  Avg Latency: {result['avg_latency_ms']:.3f} ms")
            
            # Metadata Operations
            print("\n" + "=" * 70)
            print("METADATA OPERATIONS (Small File Tests)")
            print("=" * 70)
            
            print("\nTesting file creation (5000 files of 4KB each)...")
            result = self.test_file_creation(5000, 4096)
            self.results['file_creation'] = result
            print(f"  Duration: {result['duration_sec']:.3f} seconds")
            print(f"  Files per second: {result['files_per_sec']:.2f}")
            print(f"  Avg time per file: {result['avg_time_per_file_ms']:.3f} ms")
            
            print("\nTesting file deletion (5000 files)...")
            result = self.test_file_deletion(5000)
            self.results['file_deletion'] = result
            print(f"  Duration: {result['duration_sec']:.3f} seconds")
            print(f"  Files per second: {result['files_per_sec']:.2f}")
            print(f"  Avg time per file: {result['avg_time_per_file_ms']:.3f} ms")
            
            # Store results from this run
            return self.results
            
        finally:
            self.cleanup()
    
    def _print_summary(self):
        """Print summary of results"""
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        
        # Extract key metrics
        seq_write_speeds = [v['speed_bytes_per_sec'] for k, v in self.results.items() 
                           if k.startswith('seq_write_')]
        seq_read_speeds = [v['speed_bytes_per_sec'] for k, v in self.results.items() 
                          if k.startswith('seq_read_')]
        rand_write_iops = [v['iops'] for k, v in self.results.items() 
                          if k.startswith('rand_write_')]
        rand_read_iops = [v['iops'] for k, v in self.results.items() 
                         if k.startswith('rand_read_')]
        
        if seq_write_speeds:
            avg_write = statistics.mean(seq_write_speeds)
            print(f"\nAverage Sequential Write Speed: {self._format_speed(avg_write)}")
        
        if seq_read_speeds:
            avg_read = statistics.mean(seq_read_speeds)
            print(f"Average Sequential Read Speed: {self._format_speed(avg_read)}")
        
        if rand_write_iops:
            avg_write_iops = statistics.mean(rand_write_iops)
            print(f"\nAverage Random Write IOPS (4KB): {avg_write_iops:.2f}")
        
        if rand_read_iops:
            avg_read_iops = statistics.mean(rand_read_iops)
            print(f"Average Random Read IOPS (4KB): {avg_read_iops:.2f}")
        
        if 'file_creation' in self.results:
            print(f"\nFile Creation Rate: {self.results['file_creation']['files_per_sec']:.2f} files/sec")
        
        if 'file_deletion' in self.results:
            print(f"File Deletion Rate: {self.results['file_deletion']['files_per_sec']:.2f} files/sec")
    
    def _calculate_statistics(self, values: List[float]) -> Dict:
        """Calculate mean and standard deviation for a list of values"""
        if not values:
            return {'mean': 0, 'std_dev': 0}
        
        mean = statistics.mean(values)
        std_dev = statistics.stdev(values) if len(values) > 1 else 0
        
        return {'mean': mean, 'std_dev': std_dev}
    
    def _print_aggregated_results(self):
        """Print aggregated statistics across all runs"""
        print("\n" + "=" * 70)
        print("AGGREGATED RESULTS ACROSS ALL RUNS")
        print("=" * 70)
        
        if not self.all_runs:
            print("No results to aggregate.")
            return
        
        num_runs = len(self.all_runs)
        print(f"\nNumber of runs: {num_runs}")
        
        # Collect all metrics from all runs
        metrics = {}
        
        # Go through each run and collect values for each metric
        for run_results in self.all_runs:
            for test_name, test_data in run_results.items():
                if test_name not in metrics:
                    metrics[test_name] = {}
                
                for metric_name, value in test_data.items():
                    if isinstance(value, (int, float)):
                        if metric_name not in metrics[test_name]:
                            metrics[test_name][metric_name] = []
                        metrics[test_name][metric_name].append(value)
        
        # Print sequential write results
        print("\n" + "-" * 70)
        print("SEQUENTIAL WRITE PERFORMANCE")
        print("-" * 70)
        for test_name in sorted([k for k in metrics.keys() if k.startswith('seq_write_')]):
            file_size = int(test_name.split('_')[-1])
            print(f"\n{self._format_size(file_size)} Files:")
            
            if 'speed_bytes_per_sec' in metrics[test_name]:
                stats = self._calculate_statistics(metrics[test_name]['speed_bytes_per_sec'])
                print(f"  Speed: {self._format_speed(stats['mean'])} ± {self._format_speed(stats['std_dev'])}")
                print(f"  (Mean ± Std Dev)")
        
        # Print sequential read results
        print("\n" + "-" * 70)
        print("SEQUENTIAL READ PERFORMANCE")
        print("-" * 70)
        for test_name in sorted([k for k in metrics.keys() if k.startswith('seq_read_')]):
            file_size = int(test_name.split('_')[-1])
            print(f"\n{self._format_size(file_size)} Files:")
            
            if 'speed_bytes_per_sec' in metrics[test_name]:
                stats = self._calculate_statistics(metrics[test_name]['speed_bytes_per_sec'])
                print(f"  Speed: {self._format_speed(stats['mean'])} ± {self._format_speed(stats['std_dev'])}")
                print(f"  (Mean ± Std Dev)")
        
        # Print random write results
        print("\n" + "-" * 70)
        print("RANDOM WRITE PERFORMANCE (4KB blocks)")
        print("-" * 70)
        for test_name in sorted([k for k in metrics.keys() if k.startswith('rand_write_')]):
            file_size = int(test_name.split('_')[-1])
            print(f"\n{self._format_size(file_size)} Files:")
            
            if 'iops' in metrics[test_name]:
                stats = self._calculate_statistics(metrics[test_name]['iops'])
                print(f"  IOPS: {stats['mean']:.2f} ± {stats['std_dev']:.2f}")
            
            if 'avg_latency_ms' in metrics[test_name]:
                stats = self._calculate_statistics(metrics[test_name]['avg_latency_ms'])
                print(f"  Latency: {stats['mean']:.3f} ms ± {stats['std_dev']:.3f} ms")
        
        # Print random read results
        print("\n" + "-" * 70)
        print("RANDOM READ PERFORMANCE (4KB blocks)")
        print("-" * 70)
        for test_name in sorted([k for k in metrics.keys() if k.startswith('rand_read_')]):
            file_size = int(test_name.split('_')[-1])
            print(f"\n{self._format_size(file_size)} Files:")
            
            if 'iops' in metrics[test_name]:
                stats = self._calculate_statistics(metrics[test_name]['iops'])
                print(f"  IOPS: {stats['mean']:.2f} ± {stats['std_dev']:.2f}")
            
            if 'avg_latency_ms' in metrics[test_name]:
                stats = self._calculate_statistics(metrics[test_name]['avg_latency_ms'])
                print(f"  Latency: {stats['mean']:.3f} ms ± {stats['std_dev']:.3f} ms")
        
        # Print metadata operation results
        print("\n" + "-" * 70)
        print("METADATA OPERATIONS")
        print("-" * 70)
        
        if 'file_creation' in metrics:
            print(f"\nFile Creation:")
            if 'files_per_sec' in metrics['file_creation']:
                stats = self._calculate_statistics(metrics['file_creation']['files_per_sec'])
                print(f"  Rate: {stats['mean']:.2f} ± {stats['std_dev']:.2f} files/sec")
            if 'avg_time_per_file_ms' in metrics['file_creation']:
                stats = self._calculate_statistics(metrics['file_creation']['avg_time_per_file_ms'])
                print(f"  Avg Time: {stats['mean']:.3f} ms ± {stats['std_dev']:.3f} ms")
        
        if 'file_deletion' in metrics:
            print(f"\nFile Deletion:")
            if 'files_per_sec' in metrics['file_deletion']:
                stats = self._calculate_statistics(metrics['file_deletion']['files_per_sec'])
                print(f"  Rate: {stats['mean']:.2f} ± {stats['std_dev']:.2f} files/sec")
            if 'avg_time_per_file_ms' in metrics['file_deletion']:
                stats = self._calculate_statistics(metrics['file_deletion']['avg_time_per_file_ms'])
                print(f"  Avg Time: {stats['mean']:.3f} ms ± {stats['std_dev']:.3f} ms")
    
    def run_multiple_benchmarks(self, num_runs: int = 5):
        """Run benchmark suite multiple times and aggregate results"""
        print("\n" + "=" * 70)
        print(f"RUNNING {num_runs} BENCHMARK ITERATIONS")
        print("=" * 70)
        
        for i in range(num_runs):
            print(f"\n{'#' * 70}")
            print(f"# RUN {i + 1} of {num_runs}")
            print(f"{'#' * 70}\n")
            
            self.setup()
            run_results = self.run_benchmark_suite()
            self.all_runs.append(run_results)
            
            # Print summary for this run
            self._print_summary()
            
            print(f"\nCompleted run {i + 1}/{num_runs}")
        
        # Print aggregated statistics
        self._print_aggregated_results()
        
        # Save all results
        self._save_all_results()
    
    def _save_all_results(self):
        """Save all run results to JSON file"""
        output_file = "benchmark_results.json"
        
        # Calculate aggregated statistics
        aggregated_stats = {}
        
        if self.all_runs:
            # Collect all metrics from all runs
            metrics = {}
            
            for run_results in self.all_runs:
                for test_name, test_data in run_results.items():
                    if test_name not in metrics:
                        metrics[test_name] = {}
                    
                    for metric_name, value in test_data.items():
                        if isinstance(value, (int, float)):
                            if metric_name not in metrics[test_name]:
                                metrics[test_name][metric_name] = []
                            metrics[test_name][metric_name].append(value)
            
            # Calculate statistics for each metric
            for test_name, test_metrics in metrics.items():
                aggregated_stats[test_name] = {}
                for metric_name, values in test_metrics.items():
                    stats = self._calculate_statistics(values)
                    aggregated_stats[test_name][metric_name] = {
                        'mean': stats['mean'],
                        'std_dev': stats['std_dev'],
                        'min': min(values),
                        'max': max(values),
                        'values': values
                    }
        
        results_with_metadata = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'test_directory': str(self.test_dir.absolute()),
            'num_runs': len(self.all_runs),
            'aggregated_statistics': aggregated_stats,
            'all_runs': self.all_runs
        }
        
        with open(output_file, 'w') as f:
            json.dump(results_with_metadata, f, indent=2)
        
        print(f"\n\nDetailed results from all runs saved to: {output_file}")
    
def main():
    # Configure the amount of data per test (in GB)
    data_size_gb = 1.0
    num_runs = 5
    
    benchmark = FileIOBenchmark(data_size_gb=data_size_gb)
    benchmark.run_multiple_benchmarks(num_runs=num_runs)
    print("\n" + "=" * 70)
    print("All benchmarks complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
