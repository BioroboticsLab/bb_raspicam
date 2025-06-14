import time, datetime, configparser, os, numpy as np
from gpiozero import LED
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput


class Background:
    def __init__(self, alpha, diff_th, area_th, delay, w, h):
        self.alpha          = alpha
        self.diff_th        = diff_th      # per-pixel |bg – img| > diff_th
        self.area_th        = area_th      # fraction of pixels above that
        self.delay          = delay
        self.total          = w * h
        self.initialized    = False
        self.last_active    = time.time()

    def update_bg(self, img):
        """
        Blend in a new lo-res frame, compute the changed-pixel fraction,
        return True if changed >= area_th (i.e. frame_motion).
        """
        if not self.initialized:
            self.bg = img.astype(np.float32)
            self.initialized = True
            print(f"[BG INIT] waiting for next frame…")
            return False

        # 1) which pixels moved?
        diff = np.abs(self.bg - img) > self.diff_th
        changed = diff.sum() / self.total

        # 2) diagnostic print
        print(f"Changed ratio: {changed:.4f}   "
              f"(diff_th={self.diff_th}, area_th={self.area_th:.4f})")

        # 3) update background model
        self.bg = self.bg * self.alpha + img * (1 - self.alpha)

        # 4) did this frame count as motion?
        if changed >= self.area_th:
            self.last_active = time.time()
            return True
        return False

    def is_active(self):
        """Still ‘active’ if we saw motion within the last `delay` seconds."""
        return (time.time() - self.last_active) < self.delay

def run_camera(cfg_path):
    cfg = configparser.ConfigParser()
    cfg.read(cfg_path)

    # -- Background params --
    alpha = float(cfg['Background']['alpha'])
    diff_th = int(cfg['Background']['diff_threshold'])
    area_th = float(cfg['Background']['area_threshold'])
    delay   = int(cfg['Background']['delay'])
    bg_time = float(cfg['Background']['bg_time'])
    scale   = float(cfg['Background']['scale_factor'])

    # --- Picamera2 setup ---
    # apply sensor mode _first_
    picam2 = Picamera2()
    # 1. Create the video configuration (no framerate or controls here)
    cam_mode = int(cfg['Recording']['sensor_mode'])
    mode = picam2.sensor_modes[cam_mode]   

    # -- Recording params --
    fr = int(cfg['Recording']['framerate'])
    sw, sh = mode["size"]
    zx, zy = float(cfg['Recording']['zoom_x']), float(cfg['Recording']['zoom_y'])
    zw, zh = float(cfg['Recording']['zoom_w']), float(cfg['Recording']['zoom_h'])
    vid_len = int(cfg['Recording']['video_length'])
    vid_dir = cfg['Recording']['video_dir']
    exp_mode = cfg['Recording']['exposure_mode']
    exp_comp = int(cfg['Recording']['exposure_compensation'])
    awb_mode = cfg['Recording']['awb_mode']
    shutter_spd = int(cfg['Recording']['shutter_speed'])
    iso = int(cfg['Recording']['iso'])
    lensposition = float(cfg['Recording']['lens_focus_position'])

    # compute crop & lores sizes
    cam_w = round(sw * zw / 32) * 32
    cam_h = round(sh * zh / 16) * 16
    aspect = cam_w / cam_h

    # clamp max width to 1920, then derive height from the same AR
    out_w = min(cfg.getint("Recording", "output_width"), 1920)
    out_h = int(out_w / aspect)            # keeps the same cam_w/cam_h ratio
    if out_h > 1080:                       # if that overshoots max height…
        out_h = 1080
        out_w = int(out_h * aspect)

    bg_w  = (round((cam_w * scale) / 32) * 32)
    bg_h  = (round((cam_h * scale) / 16) * 16)

    frame_us = int(1e6 / fr)  # e.g. fr=15 gives ~66667 µs per frame    

    bg = Background(alpha, diff_th, area_th, delay, bg_w, bg_h)

    feeder = cfg['General']['feeder_id']
    out_dir = os.path.join(vid_dir, feeder)
    os.makedirs(out_dir, exist_ok=True)

    video_config = picam2.create_video_configuration(
        main  = {"size": (out_w,  out_h), "format": "YUV420"},
        lores = {"size": (bg_w,   bg_h), "format": "YUV420"},
        buffer_count = 4,
        sensor = {
            "output_size": mode["size"],                   # e.g. (2304, 1296)
            "bit_depth":   mode["bit_depth"]               # e.g. 10 or 12
        },
        controls     = {
            # clamp frame times to exactly 100 ms => 10 fps
            "FrameDurationLimits": (frame_us, frame_us)
        }        
    )
    # 2. Configure the camera
    picam2.configure(video_config)

    # 4. Set runtime controls 
    x0 = int(zx * sw)
    y0 = int(zy * sh)
    controls = {
        "ScalerCrop": (x0, y0, cam_w, cam_h),
        "FrameRate": fr,
        "FrameDurationLimits": (frame_us, frame_us),
        "AeEnable":    (exp_mode.lower() != "off"),
        "ExposureTime":   shutter_spd,
        "AnalogueGain":   iso / 100.0,
        "AwbEnable":   (awb_mode.lower() != "off"),
        "AfMode": 0,                 # manual focus mode
        "LensPosition": lensposition
    }
    if "ExposureValue" in picam2.camera_controls:
        controls["ExposureValue"] = exp_comp
    picam2.set_controls(controls)    
    # Try to read user-defined bitrate from config (optional param)
    bitrate = cfg['Recording'].getint('bitrate', fallback=-1)

    # Auto-select bitrate based on sensor mode if not specified
    if bitrate <= 0:
        sensor_mode = int(cfg['Recording']['sensor_mode'])
        if sensor_mode == 0:
            bitrate = 4_000_000
        elif sensor_mode == 1:
            bitrate = 8_000_000
        elif sensor_mode == 2:
            bitrate = 15_000_000
        else:
            bitrate = 6_000_000  # Default fallback

    recording = False
    filename = None
    last_split = time.time()

    led_green  = LED(16)
    led_yellow = LED(20)

    def new_filename():
        return os.path.join(
            out_dir,
            f"{feeder}_{datetime.datetime.now():%Y-%m-%d-%H-%M-%S}.h264"
        )

    # —– warm up & kick off first recording —–
    picam2.start()
    time.sleep(2)

    # … after your picam2.start() and warmup …

    segment_motion = False
    filename       = new_filename()
    encoder = H264Encoder(bitrate=bitrate, framerate=fr, repeat=True, enable_sps_framerate=True)
    picam2.start_recording(encoder, FileOutput(filename))

    target_frames = fr * vid_len   # e.g. 10 fps × 30 s = 300 frames
    frame_counter = 0

    while True:
        # 1) grab & update BG
        job = picam2.capture_buffer("lores", wait=False)
        if job is None:
            time.sleep(0.01)
            continue
        buf     = picam2.wait(job)
        arr     = np.frombuffer(buf, np.uint8)
        y_plane = arr[: bg_w*bg_h].reshape((bg_h, bg_w))

        # get per-frame motion flag
        frame_motion = bg.update_bg(y_plane)
        active       = bg.is_active()

        # if *this* frame had motion, mark the segment
        if frame_motion or active:
            segment_motion = True

        print(f"frame_motion={frame_motion}, segment_active={segment_motion}")

        # after you process each frame (and before your LED toggle)
        frame_counter += 1

        # 2) rollover chunk if too long.  do it based on number of frames
        if frame_counter >= target_frames:
            picam2.stop_recording()

            if not segment_motion:
                os.remove(filename)
                print(f"— deleted (no motion): {filename}")
            else:
                print(f"— saved   (motion): {filename}")

            # reset for the next segment
            filename       = new_filename()
            encoder        = H264Encoder(
                bitrate=bitrate,
                framerate=fr,
                repeat=True,
                enable_sps_framerate=True
            )
            picam2.start_recording(encoder, FileOutput(filename))

            frame_counter  = 0
            segment_motion = False

        # 3) LEDs
        led_green.toggle()
        led_yellow.value = active




if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("config_path", default="feedercam.cfg")
    run_camera(p.parse_args().config_path)
