#!/usr/bin/env bash

# parameter_sweep.sh
# Run take_snapshot.py over ranges of zoom-y, zoom-h, and focus values

# Configuration file for snapshots
CONFIG="feedercam.cfg"

# Output directory for snapshots
OUTDIR="/home/pi/snapshots"
mkdir -p "$OUTDIR"

# Parameter lists
zoom_ys=(0.00 0.05 0.10 0.15)
zoom_hs=(0.6)
focuses=(10.0 12.5 15.0)

# Path to the snapshot command
SNAPSHOT_CMD="python3 take_snapshot.py"

# Iterate
for zy in "${zoom_ys[@]}"; do
  for zh in "${zoom_hs[@]}"; do
    for f in "${focuses[@]}"; do

      # Format filename (replace '.' with '_' for safety)
      zy_fmt=$(printf "%.2f" "$zy" | tr '.' '_')
      zh_fmt=$(printf "%.2f" "$zh" | tr '.' '_')
      f_fmt=$(printf "%.1f" "$f" | tr '.' '_')

      OUTFILE="${OUTDIR}/snapshot_zy${zy_fmt}_zh${zh_fmt}_f${f_fmt}.jpg"

      echo "Capturing: zoom_y=$zy, zoom_h=$zh, focus=$f → $OUTFILE"
      $SNAPSHOT_CMD "$CONFIG" \
        --zoom-y "$zy" \
        --zoom-h "$zh" \
        --focus "$f" \
        --out "$OUTFILE"

    done
  done
done