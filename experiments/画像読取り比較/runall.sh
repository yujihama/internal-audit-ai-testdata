#!/bin/bash
# 使い方: runall.sh モデル "加工名 [detail=..] [effort=..]" ...
cd "$(dirname "$0")"; m=$1; shift
for spec in "$@"; do ${PYTHON:-python3} run.py $m $spec & done; wait
