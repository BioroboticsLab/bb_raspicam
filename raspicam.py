import time, datetime, configparser, os, shutil, numpy as np
from gpiozero import LED
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput


class Background:
    def __init__(self, alpha, diff_th, area_th, delay, w, h):
        self.alpha       = alpha
        self.diff_th     = diff_th      # per-pixel |bg – img| > diff_th
        self.area_th     = area_th      # fraction of pixels above that
        self.delay       = delay
        self.total       = w * h
        self.initialized = False
        self.last_active = time.time()

    def update_bg(self, img):
        """
        Blend in a new lo-res frame, compute changed-pixel fraction,
        return True if changed >= area_th (frame motion).
        """
        if not self.initialized:
            self.bg = img.astype(np.float32)
            self.initialized = True
            print("[BG INIT] waiting for next frame…")
            return False

        diff    = np.abs(self.bg - img) > self.diff_th
        changed = diff.sum() / self.total
        print(f"Changed ratio: {changed:.4f}   (diff_th={self.diff_th}, area_th={self.area_th:.4f})")
        self.bg = self.bg * self.alpha + img * (1 - self.alpha)

        if changed >= self.area_th:
            self.last_active = time.time()
            return True
        return False

    def is_active(self):
        """Still active if motion within last `delay` secs."""
        return (time.time() - self.last_active) < self.delay


def run_camera(cfg_path):
    cfg = configparser.ConfigParser()
    cfg.read(cfg_path)

    # Background params
    alpha   = float(cfg['Background']['alpha'])
    diff_th = int(cfg['Background']['diff_threshold'])
    area_th = float(cfg['Background']['area_threshold'])
    delay   = int(cfg['Background']['delay'])
    scale   = float(cfg['Background']['scale_factor'])

    # Recording params
    fr      = int(cfg['Recording']['framerate'])
    vid_len = int(cfg['Recording']['video_length'])
    vid_dir = cfg['Recording']['video_dir']
    feeder  = cfg['General']['feeder_id']

    # Picamera2 setup
    picam2   = Picamera2()
    cam_mode = int(cfg['Recording']['sensor_mode'])
    mode     = picam2.sensor_modes[cam_mode]
    sw, sh   = mode['size']
    zx, zy   = float(cfg['Recording']['zoom_x']), float(cfg['Recording']['zoom_y'])
    zw, zh   = float(cfg['Recording']['zoom_w']), float(cfg['Recording']['zoom_h'])

    # Compute crop sizes
    cam_w  = round(sw * zw / 32) * 32
    cam_h  = round(sh * zh / 16) * 16
    aspect = cam_w / cam_h

    # Output resolution clamp
    out_w = min(cfg.getint('Recording','output_width'), 1920)
    out_h = int(out_w / aspect)
    if out_h > 1080:
        out_h = 1080
        out_w = int(out_h * aspect)

    # Low-res buffer size
    bg_w     = round((cam_w * scale) / 32) * 32
    bg_h     = round((cam_h * scale) / 16) * 16
    frame_us = int(1e6 / fr)

    bg = Background(alpha, diff_th, area_th, delay, bg_w, bg_h)

    # Directory layout
    # tmp directory as sibling to Videos (parent of vid_dir)
    parent = os.path.dirname(os.path.abspath(vid_dir))
    tmp_dir = os.path.join(parent, 'tmp')
    out_dir = os.path.join(vid_dir, feeder)
    os.makedirs(tmp_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    # Video configuration
    video_config = picam2.create_video_configuration(
        main         = {'size': (out_w, out_h), 'format': 'YUV420'},
        lores        = {'size': (bg_w, bg_h), 'format': 'YUV420'},
        buffer_count = 4,
        sensor       = {'output_size': mode['size'], 'bit_depth': mode['bit_depth']},
        controls     = {'FrameDurationLimits': (frame_us, frame_us)}
    )
    picam2.configure(video_config)

    # Runtime controls
    x0 = int(zx * sw)
    y0 = int(zy * sh)
    controls = {
        'ScalerCrop':           (x0, y0, cam_w, cam_h),
        'FrameRate':            fr,
        'FrameDurationLimits':  (frame_us, frame_us),
        'AeEnable':             cfg['Recording']['exposure_mode'].lower() != 'off',
        'ExposureTime':         int(cfg['Recording']['shutter_speed']),
        'AnalogueGain':         int(cfg['Recording']['iso']) / 100.0,
        'AwbEnable':            cfg['Recording']['awb_mode'].lower() != 'off',
        'AfMode':               0,
        'LensPosition':         float(cfg['Recording']['lens_focus_position'])
    }
    if 'ExposureValue' in picam2.camera_controls:
        controls['ExposureValue'] = int(cfg['Recording']['exposure_compensation'])
    picam2.set_controls(controls)

    # Warm up
    picam2.start()
    time.sleep(2)

    # Prepare first segment
    def new_filename(dir_):
        return os.path.join(dir_, f"{feeder}_{datetime.datetime.now():%Y-%m-%d-%H-%M-%S}.h264")

    target_frames = fr * vid_len
    frame_counter = 0
    segment_motion = False

    filename = new_filename(tmp_dir)
    encoder  = H264Encoder(
        bitrate             = cfg['Recording'].getint('bitrate', fallback=-1) or 8_000_000,
        framerate           = fr,
        repeat              = True,
        enable_sps_framerate= True
    )
    picam2.start_recording(encoder, FileOutput(filename))

    led_green  = LED(16)
    led_yellow = LED(20)

    # Main loop
    while True:
        job = picam2.capture_buffer('lores', wait=False)
        if job is None:
            time.sleep(0.01)
            continue
        buf     = picam2.wait(job)
        arr     = np.frombuffer(buf, np.uint8)
        y_plane = arr[:bg_w*bg_h].reshape((bg_h, bg_w))

        # Background update
        frame_motion = bg.update_bg(y_plane)
        if frame_motion or bg.is_active():
            segment_motion = True
        print(f"frame_motion={frame_motion}, segment_active={segment_motion}")

        # Frame count split
        frame_counter += 1
        if frame_counter >= target_frames:
            picam2.stop_recording()
            if segment_motion:
                dest = os.path.join(out_dir, os.path.basename(filename))
                shutil.move(filename, dest)
                print(f"— saved   (motion): {dest}")
            else:
                os.remove(filename)
                print(f"— deleted (no motion): {filename}")

            # Reset for next segment
            filename = new_filename(tmp_dir)
            encoder  = H264Encoder(
                bitrate             = cfg['Recording'].getint('bitrate', fallback=-1) or 8_000_000,
                framerate           = fr,
                repeat              = True,
                enable_sps_framerate= True
            )
            picam2.start_recording(encoder, FileOutput(filename))
            frame_counter  = 0
            segment_motion = False

        # LEDs
        led_green.toggle()
        led_yellow.value = bg.is_active()


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('config_path', default='feedercam.cfg')
    run_camera(p.parse_args().config_path)