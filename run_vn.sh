#!/bin/bash

ARG1="common_arg1"
ARG2="common_arg2"

THIRD_ARGS=(
    "1"
    "2"
    "3"
)

for i in {0..25}
do
    PORT=$((5001 + i))

    echo "Starting VN $((i + 1)): port=$PORT"

    python3 vn.py "$ARG1" "$ARG2" "${THIRD_ARGS[$i]}" "$PORT" &
done

wait

echo "All 26 VN processes have finished."