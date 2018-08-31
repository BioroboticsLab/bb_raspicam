#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

rsync --remove-source-files -vrhe ssh /home/pi/bb_raspicam/Videos/* --include="*/" --include="*.h264" --exclude="*" feedercams@tonic.imp.fu-berlin.de:/mnt/storage/beesbook/2018/data_cams_autobackup/
