# macOS System Telemetry for HyperDX

Collects real system metrics, logs, and traces from your macOS host and sends them to HyperDX via OTLP.

## Components

| Component | Service Name | Signal Types |
|-----------|-------------|--------------|
| OTel Collector (native binary) | `macos-host-telemetry` | Metrics (hostmetrics), Logs (filelog) |
| Python trace generator | `macos-system-monitor` | Traces (synthetic spans from psutil) |

## Prerequisites

- HyperDX running via `docker compose up -d` (ports 4317, 4318, 8080, 8123)
- Python 3.9+ with venv activated and dependencies installed:
  ```bash
  pip install -r requirements.txt
  ```
- Internet access (first run downloads the OTel Collector binary ~250 MB)

## Quick Start

```bash
# Start everything (downloads collector on first run)
./system-telemetry/start-telemetry.sh start

# Check status
./system-telemetry/start-telemetry.sh status

# Verify data is flowing into ClickHouse
./system-telemetry/verify-telemetry.sh

# View logs
./system-telemetry/start-telemetry.sh logs

# Stop everything
./system-telemetry/start-telemetry.sh stop
```

## Running the Trace Generator Standalone

```bash
python system-telemetry/generate_system_traces.py                   # Continuous (30s interval)
python system-telemetry/generate_system_traces.py --interval 10     # 10s interval
python system-telemetry/generate_system_traces.py --once            # Single sample
python system-telemetry/generate_system_traces.py --count 50        # 50 samples
python system-telemetry/generate_system_traces.py --verbose         # Print to stdout
```

## What Data to Expect

### Traces (in `log_stream`, type=span)

Root span `system-health-check` with child spans:

- `cpu-load-sample` — CPU %, load averages, per-mode percentages
- `memory-pressure-check` — total/available/used GB, percent, swap
- `disk-io-sample` — total/used/free GB, percent, mount point
- `network-connections-scan` — TCP connection counts by state
- `top-processes-snapshot` — process counts, top 5 by CPU and memory
- `battery-status-check` — battery %, plugged status (laptops only)

All numeric values are stored as span number attributes for dashboard aggregation.

### Metrics (in `metric_stream`)

Standard `hostmetrics` receiver metrics: `system.cpu.time`, `system.memory.usage`, `system.disk.io`, `system.network.io`, `system.filesystem.usage`, etc.

### Logs (in `log_stream`, type=log)

Parsed entries from `/var/log/system.log` and `/var/log/install.log`.

> **Note:** Log collection may require elevated permissions on recent macOS. If logs don't appear, run the collector with `sudo` or comment out the `filelog` receiver in the config. Metrics and traces work without elevated permissions.

## File Structure

```
system-telemetry/
├── otel-collector-config.yaml    # OTel Collector configuration
├── generate_system_traces.py     # Python trace generator (psutil)
├── start-telemetry.sh            # Management script (start/stop/status)
├── verify-telemetry.sh           # ClickHouse data verification
├── README.md                     # This file
├── bin/                          # Downloaded otelcol-contrib (gitignored)
├── .pids/                        # PID files (gitignored)
└── logs/                         # Runtime logs (gitignored)
```
