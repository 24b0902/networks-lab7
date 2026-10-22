#!/bin/bash

ARG1="172.30.48.140"
ARG2="5000"

THIRD_ARGS=(
    "172.30.48.140"
    "172.30.48.140"
    "172.30.48.140"
)

for i in {0..2}
do
    PORT=$((5001 + i))
    THIRD_ARG="${THIRD_ARGS[$i]}"
    LOG_FILE="vn_port_${PORT}.log"

    echo "Starting VN $((i + 1)) on port $PORT (logging to $LOG_FILE)..."
    python3 vn.py "$ARG1" "$ARG2" "$THIRD_ARG" "$PORT" > "$LOG_FILE" 2>&1 &
done

echo "All 3 VN processes are running in the background."
echo "Tip: You can open the log files in VS Code or run 'tail -f vn_port_*.log' to monitor them."

wait