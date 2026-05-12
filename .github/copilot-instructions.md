# wsl_benchmarks — Copilot instructions

Cross-platform performance benchmarks comparing container technologies:
**`wslc` (Windows)**, **`container`/Apple Virtualization (macOS)**, and
**`docker` (Linux)**. All benchmarks are written in Python 3 with no
external dependencies in the host scripts (each benchmark builds its own
container image for the workload).

## Running benchmarks

There is no test suite, lint config, or CI in this repo — benchmarks
*are* the workload.

```bash
# Run every benchmark with the TUI progress ribbon
python run-all-benchmarks.py

# Run a single benchmark (each is standalone)
python startup-time/run-benchmark.py
python ram-overhead/run-benchmark.py --cpu 2 --memory 4g
python network-speed/run-benchmark.py --wsl   # only network-speed has --wsl
python file-perf/run-benchmark.py my-run --tests pip npm --runs 3
```

Common flags via `add_common_args` (in `bench_helpers.py`): `--cpu` and
`--memory` map to `--cpus` and `--memory` on the underlying container CLI.

Prerequisites are checked at runtime and the script `sys.exit`s with a
clear message if missing (e.g., `iperf3` on the host for `network-speed`,
`wslc`/`container`/`docker` on `PATH`).

## Architecture: the "benchmark module" pattern

Every benchmark lives in its own top-level directory and follows the
same shape — copy an existing one when adding a new benchmark:

```
<benchmark>/
  Dockerfile            # workload image, usually alpine-based
  run-benchmark.py      # orchestrator: build → measure → cleanup
  <platform>-<bench>-<YYYY-MM-DD>.json   # output, gitignored by pattern
```

`run-benchmark.py` always:

1. Inserts the repo root on `sys.path` and imports from `bench_helpers`.
2. Defines a `PLATFORM_CONFIG` dict that overrides the default container
   binary per OS (notably **Windows uses `wslc`**, not `docker`; macOS
   uses `container`).
3. Calls `get_container_bin(PLATFORM_CONFIG)` and
   `get_platform_name(PLATFORM_CONFIG)` to dispatch.
4. Builds with `<bin> build -t <IMAGE_TAG> <script_dir>`.
5. Runs the workload via `build_container_run_cmd(...)` so `--cpu` /
   `--memory` propagate uniformly.
6. Wraps everything in `try/finally` that calls
   `<bin> rm -f <CONTAINER_NAME>` (and often `rmi`) for cleanup.
7. Writes `<platform>-<bench>-<today_iso()>.json` next to the script
   and ends with `print_success(output_file, results)`.

`run-all-benchmarks.py` discovers benchmarks from a hard-coded
`BENCHMARKS` list — **add new benchmarks there** to include them in the
suite run. It launches each `run-benchmark.py` as a subprocess and
renders an ANSI ribbon (Windows VT mode is enabled via ctypes).

## Platform-specific gotchas

- **VM RAM measurement** (`ram-overhead`, `startup-time`): the host-side
  VM process name differs per platform. `get_vm_process_name()` returns
  `vmmemwslc-cli-{username}` on Windows, the Apple
  `com.apple.Virtualization.VirtualMachine` process on macOS, and `None`
  on Linux (where memory comes from `docker stats` / cgroups instead).
  `WorkingSet64` of `vmmemwslc-cli-{user}` is the source of truth for
  wslc VM RAM.
- **Cold-start timing** requires stopping the VM first.
  `stop_container_system(bin_name)` runs `wslc session terminate` on
  Windows, `container system stop` on macOS, and is a no-op on Linux.
  Always follow with `wait_for_vm_exit()` before measuring.
- **Disk space** (`disk-space`): on Windows it stats the wslc VHDX at
  `C:/Users/<user>/AppData/Local/wslc/sessions/wslc-cli-<user>/storage.vhdx`
  and resets storage by deleting the VHDX before each run (Windows-only
  step 0); on macOS it walks
  `~/Library/Application Support/com.apple.container` using
  `st_blocks * 512` (matches `du`); on Linux it walks `/var/lib/docker`.

## Conventions

- **Paths in subprocess calls** are built as lists, not shell strings;
  `run()` and `run_capture()` in `bench_helpers.py` print the command
  before executing, so prefer them over raw `subprocess.run`.
- **Result JSON** always includes `platform`, `date`, `container_tool`,
  and a units field on every numeric block (e.g.,
  `{"value": 384.5, "units": "MB"}` or a sibling `"units": "seconds"`
  inside the metric object). Follow this when adding new metrics.
- **`bytes_to_mb()`** is the standard conversion helper; don't reinvent
  it inline.
- **`file-perf`** is the only benchmark with its own Python dependencies
  (`pyproject.toml` declaring `matplotlib`, `numpy`) — those are
  installed *inside* the container by its Dockerfile, not on the host.
  The host-side `run-benchmark.py` only forwards CLI args into the
  container. **What it actually measures:** I/O against a bind-mounted
  host directory (`-v <script_dir>/out:/out`, with the in-container
  `--working-folder /out`), so the workload exercises the
  container-runtime's volume mount path, not the container's overlay
  filesystem. The result JSON is then copied out of that mount.
- **Output file naming** is `{platform}-{benchmark_label}-{YYYY-MM-DD}.json`
  (e.g., `linux-file-perf-2026-05-11.json`). The `benchmark_label` is
  *not* always the directory name: `cpu-test/` writes `*-cpu-stress-*.json`,
  and `network-speed --wsl` writes `*-network-speed-wsl-*.json`. All
  variants are covered by the existing `*.json` patterns in `.gitignore` —
  do not commit result files.
- **Do not commit** `benchmark_cache/`, `benchmark_temp/`, `out/`,
  `graph_data/`, `graph_output/`, or `.venv/` (all in `.gitignore`).
