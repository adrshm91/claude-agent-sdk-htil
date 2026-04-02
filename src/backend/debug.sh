#! /usr/bin/env bash

set -e
set -x

PORT="${PORT:-6060}"
HOST="${HOST:-0.0.0.0}"

# Activate the virtual environment created during docker build
source .venv/bin/activate

# Set Python path for the entire script
export PYTHONPATH=/backend

exec uvicorn app.main:app --host "$HOST" --port "$PORT" --reload