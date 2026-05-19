# WSL Benchmarks

Cross-platform performance benchmarks comparing container technologies:
**wslc** (Windows), **container** / Apple Virtualization (macOS), and
**docker** (Linux).

## Prerequisites

- Python 3.10+
- One of the supported container runtimes on your `PATH`:
  - **Windows:** `wslc`
  - **macOS:** `container`
  - **Linux:** `docker`
- Benchmark-specific requirements are checked at runtime and will print
  a clear error if missing (e.g., `iperf3` for `network-speed`).

## Quick Start

### Run all benchmarks

```bash
python run-all-benchmarks.py
```

This launches each benchmark in sequence and displays a coloured TUI
progress ribbon. A pass/fail summary is printed at the end.

### Run a single benchmark

Each benchmark is standalone — just run its `run-benchmark.py`:

```bash
python startup-time/run-benchmark.py
python cpu-test/run-benchmark.py
python ram-overhead/run-benchmark.py
python disk-space/run-benchmark.py
python network-speed/run-benchmark.py
python file-perf/run-benchmark.py
```

### Common flags

All benchmarks accept these options (via `bench_helpers.add_common_args`):

| Flag       | Description                              | Example    |
|------------|------------------------------------------|------------|
| `--cpu`    | CPU limit for the container runtime      | `--cpu 2`  |
| `--memory` | Memory limit for the container runtime   | `--memory 4g` |

### Benchmark-specific flags

| Benchmark        | Extra flags                                        |
|------------------|----------------------------------------------------|
| `startup-time`   | `--runs N` (default 5)                             |
| `network-speed`  | `--wsl` (test default WSL distro instead of container) |
| `file-perf`      | positional `name`, `--tests`, `--runs` (see below) |

#### file-perf examples

```bash
# Run all I/O tests with defaults
python file-perf/run-benchmark.py

# Run only pip and npm tests, 3 iterations, named "my-run"
python file-perf/run-benchmark.py my-run --tests pip npm --runs 3
```

`file-perf` requires a one-time internet connection to populate its
offline caches (pip wheels, npm packages, git repos). This happens
automatically during the Docker image build.

## Benchmarks

| Directory        | What it measures                                    |
|------------------|-----------------------------------------------------|
| `startup-time/`  | Cold-start wall-clock time from stopped VM state    |
| `cpu-test/`      | CPU throughput (Phoronix smallpt ray-tracer)        |
| `network-speed/` | TCP throughput between host and container (iperf3)  |
| `ram-overhead/`  | Host-side RAM cost of running an idle container     |
| `disk-space/`    | Host disk impact of building the Linux kernel       |
| `file-perf/`     | Volume-mount I/O: sequential/random, pip/npm/git    |

## How it works

Each benchmark follows the same pattern:

1. Build a container image (`Dockerfile` in the benchmark directory)
2. Run the workload inside the container
3. Collect measurements (timing, memory, disk, throughput)
4. Write results to `<platform>-<benchmark>-<YYYY-MM-DD>.json`
5. Clean up (remove container and optionally the image)

The correct container binary is selected automatically based on your OS.
On Windows it uses `wslc`, on macOS it uses `container`, and on Linux it
uses `docker`.

## Output

Results are written as JSON files next to each benchmark script:

```
windows-startup-time-2026-05-19.json
mac-cpu-stress-2026-05-19.json
linux-file-perf-2026-05-19.json
```

These files are gitignored — do not commit them.

## Project structure

```
├── run-all-benchmarks.py   # Suite runner with TUI ribbon
├── bench_helpers.py        # Shared utilities (run, build, platform dispatch)
├── startup-time/           # Cold start benchmark
├── cpu-test/               # CPU stress benchmark
├── network-speed/          # Network throughput benchmark
├── ram-overhead/           # Memory overhead benchmark
├── disk-space/             # Disk usage benchmark
└── file-perf/              # File I/O benchmark
    ├── run-benchmark.py    # Orchestrator
    ├── Dockerfile          # Image with benchmark + caches
    ├── file_io_benchmark.py # Core benchmark logic
    └── setup_caches.py     # Offline cache builder
```
