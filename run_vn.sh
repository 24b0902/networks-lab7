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

    echo "Starting VN $((i + 1)): port=$PORT"

    python3 vn.py "$ARG1" "$ARG2" "${THIRD_ARGS[$i]}" "$PORT" &
done

wait

echo "All 3 VN processes have finished."