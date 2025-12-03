# File I/O Performance Benchmark

A Python script to test file system I/O performance with various file sizes and operations.

## Usage

```bash
python3 file_io_benchmark.py
```

## What It Tests

- **Sequential Read/Write**: Throughput with different file sizes (10MB to 1GB)
- **Random Read/Write**: IOPS and latency with 4KB blocks
- **Metadata Operations**: File creation and deletion speed

## Configuration

Edit `main()` in `file_io_benchmark.py`:

```python
data_size_gb = 2.0  # Total data per test
num_runs = 5        # Number of iterations
```

## Output

- Console output with per-run and aggregated statistics (mean ± std dev)
- `benchmark_results.json` with detailed results from all runs
