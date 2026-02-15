#!/usr/bin/env python3
"""
Generate trace spans from real macOS system measurements via psutil.

Each collection cycle produces a root span (system-health-check) with child
spans for CPU, memory, disk, network, and top processes.  All numeric values
are stored as span number attributes so they can be aggregated in HyperDX
dashboard tiles via _number_attributes['...'].

Usage:
    python generate_system_traces.py                   # Run continuously (30s)
    python generate_system_traces.py --interval 10     # 10s interval
    python generate_system_traces.py --once            # Single sample, exit
    python generate_system_traces.py --count 50        # 50 samples, exit
    python generate_system_traces.py --verbose         # Print each sample
"""

import argparse
import os
import platform
import signal
import socket
import sys
import time

import psutil
from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import StatusCode

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SERVICE_NAME = "macos-system-monitor"

# Thresholds for health status
CPU_WARNING = 70.0
CPU_CRITICAL = 90.0
MEMORY_WARNING = 80.0
MEMORY_CRITICAL = 90.0
DISK_WARNING = 85.0
DISK_CRITICAL = 95.0

# ---------------------------------------------------------------------------
# OTel setup
# ---------------------------------------------------------------------------

_provider = None
_tracer = None


def get_tracer() -> trace.Tracer:
    global _provider, _tracer
    if _tracer is None:
        resource = Resource.create({
            "service.name": SERVICE_NAME,
            "service.version": "1.0.0",
            "deployment.environment": "local",
        })
        _provider = TracerProvider(resource=resource)
        endpoint = os.getenv("OTLP_ENDPOINT", "http://localhost:4318") + "/v1/traces"
        exporter = OTLPSpanExporter(endpoint=endpoint)
        _provider.add_span_processor(BatchSpanProcessor(exporter, max_export_batch_size=512))
        _tracer = _provider.get_tracer(SERVICE_NAME)
    return _tracer

# ---------------------------------------------------------------------------
# Delta tracker for bytes-per-second calculations
# ---------------------------------------------------------------------------


class DeltaTracker:
    """Compute per-second deltas between samples."""

    def __init__(self):
        self._prev_disk_read = 0
        self._prev_disk_write = 0
        self._prev_net_sent = 0
        self._prev_net_recv = 0
        self._prev_time = 0.0
        self._initialized = False

    def update(self, disk_counters, net_counters):
        now = time.monotonic()
        if not self._initialized:
            self._prev_disk_read = disk_counters.read_bytes
            self._prev_disk_write = disk_counters.write_bytes
            self._prev_net_sent = net_counters.bytes_sent
            self._prev_net_recv = net_counters.bytes_recv
            self._prev_time = now
            self._initialized = True
            return 0.0, 0.0, 0.0, 0.0

        elapsed = now - self._prev_time
        if elapsed <= 0:
            return 0.0, 0.0, 0.0, 0.0

        disk_read_sec = (disk_counters.read_bytes - self._prev_disk_read) / elapsed
        disk_write_sec = (disk_counters.write_bytes - self._prev_disk_write) / elapsed
        net_sent_sec = (net_counters.bytes_sent - self._prev_net_sent) / elapsed
        net_recv_sec = (net_counters.bytes_recv - self._prev_net_recv) / elapsed

        self._prev_disk_read = disk_counters.read_bytes
        self._prev_disk_write = disk_counters.write_bytes
        self._prev_net_sent = net_counters.bytes_sent
        self._prev_net_recv = net_counters.bytes_recv
        self._prev_time = now

        return disk_read_sec, disk_write_sec, net_sent_sec, net_recv_sec

# ---------------------------------------------------------------------------
# Health status helpers
# ---------------------------------------------------------------------------


def health_status(value: float, warning: float, critical: float) -> str:
    if value >= critical:
        return "critical"
    if value >= warning:
        return "warning"
    return "healthy"

# ---------------------------------------------------------------------------
# Collection functions
# ---------------------------------------------------------------------------


def collect_cpu(tracer: trace.Tracer, verbose: bool) -> None:
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_times = psutil.cpu_times_percent(interval=0)
    load_1, load_5, load_15 = psutil.getloadavg()
    status = health_status(cpu_percent, CPU_WARNING, CPU_CRITICAL)

    with tracer.start_as_current_span("cpu-load-sample") as span:
        span.set_attribute("system.cpu.percent", cpu_percent)
        span.set_attribute("system.load.1m", round(load_1, 2))
        span.set_attribute("system.load.5m", round(load_5, 2))
        span.set_attribute("system.load.15m", round(load_15, 2))
        span.set_attribute("system.cpu.user_percent", round(cpu_times.user, 2))
        span.set_attribute("system.cpu.system_percent", round(cpu_times.system, 2))
        span.set_attribute("system.cpu.idle_percent", round(cpu_times.idle, 2))
        span.set_attribute("health.status", status)
        if status == "critical":
            span.set_status(StatusCode.ERROR, f"CPU usage critical: {cpu_percent}%")
        else:
            span.set_status(StatusCode.OK)

    if verbose:
        print(f"  CPU: {cpu_percent}% (load {load_1}/{load_5}/{load_15}) [{status}]")


def collect_memory(tracer: trace.Tracer, verbose: bool) -> None:
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    status = health_status(mem.percent, MEMORY_WARNING, MEMORY_CRITICAL)

    with tracer.start_as_current_span("memory-pressure-check") as span:
        span.set_attribute("system.memory.total_gb", round(mem.total / (1024 ** 3), 2))
        span.set_attribute("system.memory.available_gb", round(mem.available / (1024 ** 3), 2))
        span.set_attribute("system.memory.used_gb", round(mem.used / (1024 ** 3), 2))
        span.set_attribute("system.memory.percent", mem.percent)
        span.set_attribute("system.memory.swap_percent", swap.percent)
        span.set_attribute("health.status", status)
        if status == "critical":
            span.set_status(StatusCode.ERROR, f"Memory usage critical: {mem.percent}%")
        else:
            span.set_status(StatusCode.OK)

    if verbose:
        print(f"  Memory: {mem.percent}% ({round(mem.used / (1024**3), 1)}/"
              f"{round(mem.total / (1024**3), 1)} GB) [{status}]")


def collect_disk(tracer: trace.Tracer, delta: DeltaTracker, verbose: bool) -> None:
    disk_io = psutil.disk_io_counters()
    usage = psutil.disk_usage("/")
    status = health_status(usage.percent, DISK_WARNING, DISK_CRITICAL)

    # delta tracker is updated in the main loop, but we need read/write per sec
    # The delta is computed from the overall counters in collect_sample
    # We pass it in from collect_sample
    with tracer.start_as_current_span("disk-io-sample") as span:
        span.set_attribute("system.disk.total_gb", round(usage.total / (1024 ** 3), 2))
        span.set_attribute("system.disk.used_gb", round(usage.used / (1024 ** 3), 2))
        span.set_attribute("system.disk.free_gb", round(usage.free / (1024 ** 3), 2))
        span.set_attribute("system.disk.percent", usage.percent)
        span.set_attribute("disk.mount_point", "/")
        span.set_attribute("health.status", status)
        if status == "critical":
            span.set_status(StatusCode.ERROR, f"Disk usage critical: {usage.percent}%")
        else:
            span.set_status(StatusCode.OK)

    if verbose:
        print(f"  Disk: {usage.percent}% ({round(usage.used / (1024**3), 1)}/"
              f"{round(usage.total / (1024**3), 1)} GB) [{status}]")

    return disk_io


def collect_network(tracer: trace.Tracer, verbose: bool) -> None:
    net_io = psutil.net_io_counters()

    # net_connections requires elevated permissions on macOS
    try:
        connections = psutil.net_connections(kind="tcp")
        established = sum(1 for c in connections if c.status == "ESTABLISHED")
        listen = sum(1 for c in connections if c.status == "LISTEN")
        time_wait = sum(1 for c in connections if c.status == "TIME_WAIT")
        total = len(connections)
    except (psutil.AccessDenied, PermissionError):
        established = listen = time_wait = total = -1
    # Network health: high TIME_WAIT can indicate issues
    status = "warning" if time_wait > 500 else "healthy"

    with tracer.start_as_current_span("network-connections-scan") as span:
        span.set_attribute("system.network.bytes_sent_sec", 0.0)  # Updated in collect_sample
        span.set_attribute("system.network.bytes_recv_sec", 0.0)
        span.set_attribute("system.network.tcp_established", established)
        span.set_attribute("system.network.tcp_listen", listen)
        span.set_attribute("system.network.tcp_time_wait", time_wait)
        span.set_attribute("system.network.total_connections", total)
        span.set_attribute("health.status", status)
        span.set_status(StatusCode.OK)

    if verbose:
        print(f"  Network: {established} established, {listen} listening, "
              f"{time_wait} TIME_WAIT [{status}]")

    return net_io


def collect_processes(tracer: trace.Tracer, verbose: bool) -> None:
    procs = list(psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]))
    total_count = len(procs)
    running_count = sum(1 for p in procs if p.info.get("status") == psutil.STATUS_RUNNING)

    # Top 5 by CPU
    by_cpu = sorted(procs, key=lambda p: p.info.get("cpu_percent") or 0, reverse=True)[:5]
    # Top 5 by memory
    by_mem = sorted(procs, key=lambda p: p.info.get("memory_percent") or 0, reverse=True)[:5]

    status = "warning" if total_count > 500 else "healthy"

    with tracer.start_as_current_span("top-processes-snapshot") as span:
        span.set_attribute("process.total_count", total_count)
        span.set_attribute("process.running_count", running_count)

        for i, p in enumerate(by_cpu, 1):
            name = p.info.get("name") or "unknown"
            span.set_attribute(f"process.top_cpu.{i}.name", name)
            span.set_attribute(f"process.top_cpu.{i}.percent", p.info.get("cpu_percent") or 0.0)

        for i, p in enumerate(by_mem, 1):
            name = p.info.get("name") or "unknown"
            span.set_attribute(f"process.top_memory.{i}.name", name)
            span.set_attribute(f"process.top_memory.{i}.percent", round(p.info.get("memory_percent") or 0.0, 2))

        span.set_attribute("health.status", status)
        span.set_status(StatusCode.OK)

    if verbose:
        top_cpu_names = [p.info.get("name", "?") for p in by_cpu[:3]]
        print(f"  Processes: {total_count} total, {running_count} running, "
              f"top CPU: {', '.join(top_cpu_names)} [{status}]")


def collect_battery(tracer: trace.Tracer, verbose: bool) -> bool:
    """Collect battery info. Returns False if no battery is present."""
    battery = psutil.sensors_battery()
    if battery is None:
        return False

    with tracer.start_as_current_span("battery-status-check") as span:
        span.set_attribute("battery.percent", battery.percent)
        span.set_attribute("battery.power_plugged", battery.power_plugged)
        remaining = battery.secsleft
        if remaining != psutil.POWER_TIME_UNLIMITED and remaining != psutil.POWER_TIME_UNKNOWN:
            span.set_attribute("battery.time_remaining_minutes", round(remaining / 60, 1))
        else:
            span.set_attribute("battery.time_remaining_minutes", -1.0)

        status = health_status(100 - battery.percent, 80, 95)  # invert: low battery = high concern
        span.set_attribute("health.status", status)
        if status == "critical":
            span.set_status(StatusCode.ERROR, f"Battery critically low: {battery.percent}%")
        else:
            span.set_status(StatusCode.OK)

    if verbose:
        plugged = "plugged in" if battery.power_plugged else "on battery"
        print(f"  Battery: {battery.percent}% ({plugged}) [{status}]")

    return True

# ---------------------------------------------------------------------------
# Main collection cycle
# ---------------------------------------------------------------------------


def collect_sample(tracer: trace.Tracer, delta: DeltaTracker, verbose: bool) -> None:
    """Collect one full system health sample as a trace."""
    hostname = socket.gethostname()
    cpu_count = psutil.cpu_count()

    with tracer.start_as_current_span("system-health-check") as root:
        root.set_attribute("host.name", hostname)
        root.set_attribute("host.os.type", platform.system().lower())
        root.set_attribute("host.cpu.count", cpu_count)

        collect_cpu(tracer, verbose)
        collect_memory(tracer, verbose)
        disk_io = collect_disk(tracer, delta, verbose)
        net_io = collect_network(tracer, verbose)
        collect_processes(tracer, verbose)
        collect_battery(tracer, verbose)

        # Compute deltas and update the disk/network spans retroactively
        # Since spans are already ended, we set the delta values on the root span
        disk_read_sec, disk_write_sec, net_sent_sec, net_recv_sec = delta.update(disk_io, net_io)
        root.set_attribute("system.disk.read_bytes_sec", round(disk_read_sec, 2))
        root.set_attribute("system.disk.write_bytes_sec", round(disk_write_sec, 2))
        root.set_attribute("system.network.bytes_sent_sec", round(net_sent_sec, 2))
        root.set_attribute("system.network.bytes_recv_sec", round(net_recv_sec, 2))

    if verbose:
        print(f"  Disk I/O: {round(disk_read_sec / 1024, 1)} KB/s read, "
              f"{round(disk_write_sec / 1024, 1)} KB/s write")
        print(f"  Network: {round(net_sent_sec / 1024, 1)} KB/s sent, "
              f"{round(net_recv_sec / 1024, 1)} KB/s recv")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

_running = True


def _signal_handler(sig, frame):
    global _running
    _running = False
    print("\nShutting down...")


def main():
    global _running

    parser = argparse.ArgumentParser(
        description="Generate system telemetry trace spans from macOS host metrics"
    )
    parser.add_argument("--interval", type=int, default=30,
                        help="Collection interval in seconds (default: 30)")
    parser.add_argument("--once", action="store_true",
                        help="Collect a single sample and exit")
    parser.add_argument("--count", type=int, default=0,
                        help="Number of samples to collect (0 = unlimited)")
    parser.add_argument("--verbose", action="store_true",
                        help="Print each sample to stdout")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    tracer = get_tracer()
    delta = DeltaTracker()

    endpoint = os.getenv("OTLP_ENDPOINT", "http://localhost:4318")
    print(f"System telemetry tracer started")
    print(f"  Service:  {SERVICE_NAME}")
    print(f"  Endpoint: {endpoint}")
    print(f"  Interval: {args.interval}s")
    if args.once:
        print(f"  Mode:     single sample")
    elif args.count > 0:
        print(f"  Mode:     {args.count} samples")
    else:
        print(f"  Mode:     continuous (Ctrl+C to stop)")
    print()

    sample_num = 0
    while _running:
        sample_num += 1
        if args.verbose:
            print(f"--- Sample #{sample_num} ---")

        collect_sample(tracer, delta, args.verbose)

        if args.verbose:
            print()

        if args.once:
            break
        if args.count > 0 and sample_num >= args.count:
            break

        # Sleep in small increments so SIGTERM is responsive
        for _ in range(args.interval * 10):
            if not _running:
                break
            time.sleep(0.1)

    # Flush remaining spans
    if _provider:
        _provider.force_flush(timeout_millis=5000)

    print(f"Done. Collected {sample_num} sample(s).")


if __name__ == "__main__":
    main()
