#!/usr/bin/env python3
import time
import datetime
import argparse
import configparser
import os
from picamera2 import Picamera2


def main():
    p = argparse.ArgumentParser(
        description="Take a single snapshot using picamera2 based on config (with optional overrides)"
    )
    p.add_argument('config', help='Path to INI config file')
    p.add_argument('--zoom-y', type=float, help='Override zoom_y fraction')
    p.add_argument('--zoom-h', type=float, help='Override zoom_h fraction')
    p.add_argument('--focus', type=float, help='Override lens_focus_position')
    p.add_argument('--out', help='Output image path (default: ./snapshot_<ts>.jpg)')
    args = p.parse_args()

    # Read config
    cfg = configparser.ConfigParser()
    cfg.read(args.config)
    feeder = cfg['General'].get('feeder_id', 'feedercam')
    # Recording params for ROI
    zoom_x = cfg.getfloat('Recording','zoom_x')
    zoom_y = args.zoom_y if args.zoom_y is not None else cfg.getfloat('Recording','zoom_y')
    zoom_w = cfg.getfloat('Recording','zoom_w')
    zoom_h = args.zoom_h if args.zoom_h is not None else cfg.getfloat('Recording','zoom_h')

    focus_pos = args.focus if args.focus is not None else cfg.getfloat('Recording','lens_focus_position')

    sensor_mode = cfg.getint('Recording','sensor_mode')

    # Setup camera
    picam2 = Picamera2()
    mode = picam2.sensor_modes[sensor_mode]
    sw, sh = mode['size']

    # Compute crop
    cam_w = round(sw * zoom_w / 32) * 32
    cam_h = round(sh * zoom_h / 16) * 16
    x0 = int(zoom_x * sw)
    y0 = int(zoom_y * sh)

    # Create still config
    still_config = picam2.create_still_configuration(
        main={'size': (cam_w, cam_h), 'format': 'RGB888'}
    )
    picam2.configure(still_config)

    # Start and warm up
    picam2.start()
    time.sleep(2)

    # Apply crop & focus
    picam2.set_controls({
        'ScalerCrop': (x0, y0, cam_w, cam_h),
        'AfMode': 0,  # manual focus
        'LensPosition': focus_pos
    })
    time.sleep(0.5)  # let focus settle

    # Output path
    ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    out_path = args.out or f"snapshot_{feeder}_{ts}.jpg"
    out_dir = os.path.dirname(out_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    # Capture
    picam2.capture_file(out_path)
    print(f"Saved snapshot to {out_path}")

    picam2.close()


if __name__ == '__main__':
    main()