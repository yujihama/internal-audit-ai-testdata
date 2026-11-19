#!/bin/bash
cd "$(dirname "$0")"; m=$1; shift
for spec in "$@"; do ${PYTHON:-../.venv/bin/python} run.py $m $spec & done; wait
