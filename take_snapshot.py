#!/usr/bin/env python3
import time
import datetime
import argparse
import configparser
import os
from picamera2 import Picamera2
from PIL import Image


def main():
    p = argparse.ArgumentParser(
        description="Take a single snapshot using picamera2 based on config (with optional overrides)"
    )
    p.add_argument('--config', help='Path to INI config file')
    p.add_argument('--zoom-y', type=float, help='Override zoom_y fraction')
    p.add_argument('--zoom-h', type=float, help='Override zoom_h fraction')
    p.add_argument('--focus', type=float, help='Override lens_focus_position (dioptres; 0=infinity)')
    p.add_argument('--af', action='store_true',
                   help='Run autofocus instead of manual focus; prints the resulting LensPosition')
    p.add_argument('--shutter-speed', type=int, help='Override shutter speed in microseconds')
    p.add_argument('--iso', type=int, help='Override ISO (analogue gain, e.g. 100, 200, 400)')
    p.add_argument('--greyscale', action='store_true', help='Also save a greyscale version of the snapshot')
    p.add_argument('--out', help='Output image path (default: ./snapshot_<ts>.jpg)')
    args = p.parse_args()

    # Read config
    cfg = configparser.ConfigParser()
    cfg.read(args.config)
    feeder = cfg['General'].get('feeder_id', 'feedercam')

    # Recording params for ROI
    zoom_x = cfg.getfloat('Recording', 'zoom_x')
    zoom_y = args.zoom_y if args.zoom_y is not None else cfg.getfloat('Recording', 'zoom_y')
    zoom_w = cfg.getfloat('Recording', 'zoom_w')
    zoom_h = args.zoom_h if args.zoom_h is not None else cfg.getfloat('Recording', 'zoom_h')

    focus_pos = args.focus if args.focus is not None else cfg.getfloat('Recording', 'lens_focus_position', fallback=10.0)

    sensor_mode = cfg.getint('Recording', 'sensor_mode')

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

    # Start and apply focus mode BEFORE warm-up so the lens has time to move
    picam2.start()
    if args.af:
        # Continuous AF + one-shot trigger; we'll read back the settled LensPosition after capture
        picam2.set_controls({'AfMode': 1, 'AfTrigger': 0})
    else:
        picam2.set_controls({'AfMode': 0, 'LensPosition': focus_pos})

    # Apply exposure controls alongside focus so they settle during warm-up
    exposure_controls = {}
    if args.shutter_speed is not None:
        exposure_controls['ExposureTime'] = args.shutter_speed
    else:
        shutter = cfg.getint('Recording', 'shutter_speed', fallback=0)
        if shutter > 0:
            exposure_controls['ExposureTime'] = shutter

    if args.iso is not None:
        exposure_controls['AnalogueGain'] = args.iso / 100.0
    else:
        iso = cfg.getint('Recording', 'iso', fallback=0)
        if iso > 0:
            exposure_controls['AnalogueGain'] = iso / 100.0

    if exposure_controls:
        picam2.set_controls(exposure_controls)

    time.sleep(2)  # warm-up AND lens/exposure settle

    # Apply crop (focus and exposure already set above)
    picam2.set_controls({'ScalerCrop': (x0, y0, cam_w, cam_h)})
    time.sleep(0.3)

    # Output path
    ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    out_path = args.out or f"snapshot_{feeder}_{ts}.jpg"
    out_dir = os.path.dirname(out_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    # Capture
    picam2.capture_file(out_path)
    print(f"Saved snapshot to {out_path}")

    # In AF mode, report the dioptre value the camera settled on
    if args.af:
        md = picam2.capture_metadata()
        lp = md.get('LensPosition')
        if lp is not None:
            print(f"Autofocus settled at LensPosition = {lp:.3f} dioptres "
                  f"(~{1.0/lp*100:.1f} cm)" if lp > 0 else
                  f"Autofocus settled at LensPosition = {lp:.3f} (infinity)")
        else:
            print("Autofocus settled, but LensPosition not in metadata")

    # Greyscale version
    if args.greyscale:
        base, ext = os.path.splitext(out_path)
        grey_path = f"{base}_grey{ext}"
        img = Image.open(out_path).convert('L')
        img.save(grey_path)
        print(f"Saved greyscale snapshot to {grey_path}")

    picam2.close()


if __name__ == '__main__':
    main()
