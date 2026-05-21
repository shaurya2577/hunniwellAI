#!/bin/bash
set -u
cd "$(dirname "$0")"
for ev in "apacspotlight2" "apacVirtual2(2)" "RESI" "Innovator" "OpenRounds2"; do
  echo "============================================================"
  echo "STARTING EVENT: $ev  ($(date '+%H:%M:%S'))"
  echo "============================================================"
  .venv/bin/python -u ingest.py \
    --event "$ev" \
    --state-file .processed_b.json \
    --log-file run_log_b.csv
  echo ""
done
echo "============================================================"
echo "SECONDARY RUN COMPLETE  ($(date '+%H:%M:%S'))"
echo "============================================================"
