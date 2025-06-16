#!/usr/bin/env bash

# parameter_sweep.sh
# Run take_snapshot.py over ranges of zoom-y, zoom-h, and focus values
# Configuration file for snapshots

CONFIG=“feedercamD.cfg”

Output directory for snapshots

OUTDIR=“/home/pi/snapshots/”
mkdir -p “${OUTDIR}”

Define your parameter lists here

zoom_ys=(0.00 0.05 0.10 0.15)
zoom_hs=(0.6)
focuses=(10.0 12.5 15.0)

Path to the snapshot script

SNAPSHOT_SCRIPT=”./take_snapshot.py”

Iterate over all combinations

for zy in “${zoom_ys[@]}”; do
for zh in “${zoom_hs[@]}”; do
for f in “${focuses[@]}”; do
# Format filename to reflect parameters (replace dot with underscore for safety)
zy_fmt=$(printf “%.2f” “$zy” | tr ‘.’ ‘’)
zh_fmt=$(printf “%.2f” “$zh” | tr ‘.’ ’’)
f_fmt=$(printf “%.1f” “$f” | tr ‘.’ ‘_’)
OUTFILE=”${OUTDIR}/snapshot_zy${zy_fmt}_zh${zh_fmt}_f${f_fmt}.jpg”

  echo "Capturing: zoom_y=$zy, zoom_h=$zh, focus=$f -> ${OUTFILE}"
  "$SNAPSHOT_SCRIPT" "$CONFIG" \
    --zoom-y "$zy" --zoom-h "$zh" --focus "$f" --out "$OUTFILE"
done

done
done