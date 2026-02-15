#!/usr/bin/env bash
#
# Manage macOS system telemetry collection for HyperDX.
# Usage: ./start-telemetry.sh {start|stop|status|restart|logs}
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BIN_DIR="$SCRIPT_DIR/bin"
PID_DIR="$SCRIPT_DIR/.pids"
LOG_DIR="$SCRIPT_DIR/logs"
CONFIG="$SCRIPT_DIR/otel-collector-config.yaml"
TRACES_SCRIPT="$SCRIPT_DIR/generate_system_traces.py"

OTEL_PID_FILE="$PID_DIR/otel-collector.pid"
TRACES_PID_FILE="$PID_DIR/system-traces.pid"
OTEL_LOG="$LOG_DIR/otel-collector.log"
TRACES_LOG="$LOG_DIR/system-traces.log"

HEALTH_PORT=13134
COLLECTOR_VERSION="0.120.0"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

info()  { echo "  [INFO]  $*"; }
warn()  { echo "  [WARN]  $*" >&2; }
error() { echo "  [ERROR] $*" >&2; }

is_running() {
    local pid_file="$1"
    if [[ -f "$pid_file" ]]; then
        local pid
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
        # Stale PID file
        rm -f "$pid_file"
    fi
    return 1
}

ensure_dirs() {
    mkdir -p "$BIN_DIR" "$PID_DIR" "$LOG_DIR"
}

# ---------------------------------------------------------------------------
# Download OTel Collector binary
# ---------------------------------------------------------------------------

download_collector() {
    local binary="$BIN_DIR/otelcol-contrib"
    if [[ -x "$binary" ]]; then
        info "OTel Collector binary already present"
        return 0
    fi

    local arch
    arch=$(uname -m)
    case "$arch" in
        arm64|aarch64) arch="arm64" ;;
        x86_64|amd64)  arch="amd64" ;;
        *) error "Unsupported architecture: $arch"; exit 1 ;;
    esac

    local os_name="darwin"
    local url="https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v${COLLECTOR_VERSION}/otelcol-contrib_${COLLECTOR_VERSION}_${os_name}_${arch}.tar.gz"

    info "Downloading otelcol-contrib v${COLLECTOR_VERSION} for ${os_name}/${arch}..."
    info "URL: $url"

    local tmp_tar
    tmp_tar=$(mktemp /tmp/otelcol-contrib.XXXXXX.tar.gz)

    if ! curl -fSL --progress-bar -o "$tmp_tar" "$url"; then
        rm -f "$tmp_tar"
        error "Failed to download OTel Collector. Check your internet connection."
        exit 1
    fi

    info "Extracting..."
    tar -xzf "$tmp_tar" -C "$BIN_DIR" otelcol-contrib
    rm -f "$tmp_tar"
    chmod +x "$binary"
    info "OTel Collector installed at $binary"
}

# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------

do_start() {
    echo "=== Starting macOS System Telemetry ==="
    echo

    # 1. Check HyperDX is running
    info "Checking HyperDX availability..."
    if ! curl -sf -o /dev/null http://localhost:8080; then
        error "HyperDX is not running on localhost:8080"
        error "Start it first: docker compose up -d"
        exit 1
    fi
    info "HyperDX is running"

    ensure_dirs

    # 2. Download collector if needed
    download_collector

    # 3. Start OTel Collector
    if is_running "$OTEL_PID_FILE"; then
        info "OTel Collector already running (PID $(cat "$OTEL_PID_FILE"))"
    else
        info "Starting OTel Collector..."
        nohup "$BIN_DIR/otelcol-contrib" --config "$CONFIG" \
            > "$OTEL_LOG" 2>&1 &
        local otel_pid=$!
        echo "$otel_pid" > "$OTEL_PID_FILE"
        info "OTel Collector started (PID $otel_pid)"

        # 4. Wait for health check
        info "Waiting for health check on port $HEALTH_PORT..."
        local retries=10
        while (( retries > 0 )); do
            if curl -sf -o /dev/null "http://localhost:$HEALTH_PORT"; then
                info "Health check passed"
                break
            fi
            retries=$((retries - 1))
            sleep 1
        done
        if (( retries == 0 )); then
            warn "Health check did not respond within 10s. Check $OTEL_LOG"
        fi
    fi

    # 5. Start Python trace generator
    if is_running "$TRACES_PID_FILE"; then
        info "System traces generator already running (PID $(cat "$TRACES_PID_FILE"))"
    else
        info "Starting system traces generator..."

        # Activate venv if available
        local python_cmd="python3"
        if [[ -f "$PROJECT_DIR/.venv/bin/python" ]]; then
            python_cmd="$PROJECT_DIR/.venv/bin/python"
        elif [[ -f "$PROJECT_DIR/venv/bin/python" ]]; then
            python_cmd="$PROJECT_DIR/venv/bin/python"
        fi

        nohup "$python_cmd" "$TRACES_SCRIPT" --interval 30 --verbose \
            > "$TRACES_LOG" 2>&1 &
        local traces_pid=$!
        echo "$traces_pid" > "$TRACES_PID_FILE"
        info "System traces generator started (PID $traces_pid)"
    fi

    echo
    do_status
}

# ---------------------------------------------------------------------------
# Stop
# ---------------------------------------------------------------------------

do_stop() {
    echo "=== Stopping macOS System Telemetry ==="
    echo

    local stopped=0

    for name_pid in "OTel Collector:$OTEL_PID_FILE" "System traces:$TRACES_PID_FILE"; do
        local name="${name_pid%%:*}"
        local pid_file="${name_pid#*:}"

        if [[ -f "$pid_file" ]]; then
            local pid
            pid=$(cat "$pid_file")
            if kill -0 "$pid" 2>/dev/null; then
                info "Stopping $name (PID $pid)..."
                kill "$pid"

                # Wait up to 10s for graceful shutdown
                local wait=100
                while (( wait > 0 )) && kill -0 "$pid" 2>/dev/null; do
                    sleep 0.1
                    wait=$((wait - 1))
                done

                if kill -0 "$pid" 2>/dev/null; then
                    warn "$name didn't stop gracefully, sending SIGKILL"
                    kill -9 "$pid" 2>/dev/null || true
                fi
                info "$name stopped"
                stopped=$((stopped + 1))
            else
                info "$name not running (stale PID file)"
            fi
            rm -f "$pid_file"
        else
            info "$name not running"
        fi
    done

    echo
    if (( stopped > 0 )); then
        info "Stopped $stopped process(es)"
    else
        info "Nothing was running"
    fi
}

# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

do_status() {
    echo "=== System Telemetry Status ==="
    echo

    # OTel Collector
    if is_running "$OTEL_PID_FILE"; then
        local pid
        pid=$(cat "$OTEL_PID_FILE")
        echo "  OTel Collector:    RUNNING  (PID $pid)"
        if curl -sf -o /dev/null "http://localhost:$HEALTH_PORT" 2>/dev/null; then
            echo "  Health check:      OK (port $HEALTH_PORT)"
        else
            echo "  Health check:      FAILED (port $HEALTH_PORT)"
        fi
    else
        echo "  OTel Collector:    STOPPED"
    fi

    # Python traces
    if is_running "$TRACES_PID_FILE"; then
        local pid
        pid=$(cat "$TRACES_PID_FILE")
        echo "  System traces:     RUNNING  (PID $pid)"
    else
        echo "  System traces:     STOPPED"
    fi

    echo
    echo "  Logs: $LOG_DIR/"
}

# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------

do_logs() {
    local component="${1:-all}"
    case "$component" in
        collector|otel)
            if [[ -f "$OTEL_LOG" ]]; then
                tail -f "$OTEL_LOG"
            else
                error "No collector log found at $OTEL_LOG"
            fi
            ;;
        traces|python)
            if [[ -f "$TRACES_LOG" ]]; then
                tail -f "$TRACES_LOG"
            else
                error "No traces log found at $TRACES_LOG"
            fi
            ;;
        all)
            echo "=== Recent OTel Collector logs ==="
            if [[ -f "$OTEL_LOG" ]]; then
                tail -20 "$OTEL_LOG"
            else
                echo "  (no log file)"
            fi
            echo
            echo "=== Recent System Traces logs ==="
            if [[ -f "$TRACES_LOG" ]]; then
                tail -20 "$TRACES_LOG"
            else
                echo "  (no log file)"
            fi
            ;;
        *)
            error "Unknown component: $component (use: collector, traces, or all)"
            exit 1
            ;;
    esac
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

case "${1:-}" in
    start)
        do_start
        ;;
    stop)
        do_stop
        ;;
    restart)
        do_stop
        echo
        sleep 2
        do_start
        ;;
    status)
        do_status
        ;;
    logs)
        do_logs "${2:-all}"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs [collector|traces|all]}"
        exit 1
        ;;
esac
