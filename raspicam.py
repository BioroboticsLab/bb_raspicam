import time
from picamera import PiCamera, array
import datetime
import configparser
import os
import numpy as np
from gpiozero import LED

# background accumulation via exponential average
class Background:
    # parameters:
    # ------------------
    # alpha     : 
    # threshold :
    # delay     :
    def __init__(self, alpha, threshold, area_threshold, delay, background_width, background_height):
        self.alpha = alpha
        self.active = False
        self.threshold = threshold
        self.area_threshold = area_threshold
        self.initialized = False
        self.last_active = time.time()
        self.delay = delay
        self.total_background_pixels = background_width * background_height
    
    # called every frame to update background hypothesis
    def update_bg(self,img):
        if not self.initialized:
            self.background = img
            self.initialized = True
        else:
            # total amount of image difference to background
            #changedpx = np.sum( np.abs(self.background - img) ) / bg_pixels
            
            # count the number of pixels whose difference to the background is greater than the threshold
            # this is supposed to be more stable with varying lighting conditions
            changedpx = np.sum( np.where( np.abs(self.background - img) > self.threshold) ) / self.total_background_pixels
            
            print(changedpx)
            
            if changedpx < self.area_threshold:
                self.active = False
            else:
                self.active = True
                self.last_active = time.time()
                
            self.background = self.background * self.alpha + img * (1-self.alpha)
        
    def is_active(self):
        return time.time() - self.last_active < self.delay

def run_camera(config_file_name):
    config = configparser.ConfigParser()
    config.read(config_file_name)

    cam_mode = int(config['Recording']['sensor_mode'])
    print(cam_mode)
    MAX_WIDTH = float(config['Recording']['sensor_width'])	
    MAX_HEIGHT = float(config['Recording']['sensor_height'])
    cam_width = float(config['Recording']['zoom_w']) * MAX_WIDTH
    cam_height = float(config['Recording']['zoom_h']) * MAX_HEIGHT
    bg_scale_factor = float(config['Background']['scale_factor'])
    bg_width = round((cam_width*bg_scale_factor)/32)*32
    bg_height = round((cam_height*bg_scale_factor)/16)*16

    bg = Background(float(config['Background']['alpha']),
                    int(config['Background']['diff_threshold']),
                    float(config['Background']['area_threshold']),
                    int(config['Background']['delay']),
                    bg_width, bg_height)

    led_green = LED(16)
    led_yellow = LED(20)
    
    
    with PiCamera(sensor_mode=cam_mode,
                    resolution=(int(MAX_WIDTH), int(MAX_HEIGHT))
                    ) as cam:
        cam.framerate = int(config['Recording']['framerate'])
        cam.iso = int(config['Recording']['iso'])
        cam.zoom = (float(config['Recording']['zoom_x']),float(config['Recording']['zoom_y']),float(config['Recording']['zoom_w']),float(config['Recording']['zoom_h']))
        cam.exposure_compensation = int(config['Recording']['exposure_compensation'])
        
        cam.color_effects=(128,128)
        
        # window parameter doesnt work as API says. window remains small and position is changed with different widths and heights
        #cam.start_preview(fullscreen=False, window=(0, 0, int(cam_width/2), int(cam_height/2)))
        preview = cam.start_preview(fullscreen=False,
                    window=(0, 10, int(cam_width), int(cam_height)))
        
        print('auto', config['Recording']['exposure_mode'])
        cam.exposure_mode = str(config['Recording']['exposure_mode'])
        #str(config['Recording']['exposure_mode'])
        cam.awb_mode = config['Recording']['awb_mode']
        cam.shutter_speed = int(config['Recording']['shutter_speed'])
        
        #time.sleep(20)
        print("Exposure : {}".format(cam.exposure_speed))
        recording = False
        #cam.wait_recording(5)
        last_split=time.time()
        still=None
        filename=""
        with array.PiRGBArray(cam,size=(int(bg_width),int(bg_height))) as output:
            cam.capture(output, 'rgb', use_video_port=True, resize=(int(bg_width),int(bg_height)))
            still = output.array[:,:,0]
            time.sleep(5)
            output.truncate(0)
            while True:
                cam.capture(output, 'rgb', use_video_port=True, resize=(int(bg_width),int(bg_height)))
                
                # tell world we're still alive
                led_green.toggle() 
                
                still = output.array[:,:,0]
                bg.update_bg(still)
                output.truncate(0)
                if (not bg.is_active()) and recording:
                    led_yellow.off()
                    print('move file')
                    os.rename(filename, config['Recording']['video_dir']+"/"+filename)
                    cam.stop_recording()
                    recording=False
                elif bg.is_active() and not recording:
                    led_yellow.on()
                    print('start recording')
                    filename=config['General']['feeder_id']+'_'+datetime.datetime.utcnow().strftime("%Y-%m-%d-%H-%M-%S")+'.h264'
                    cam.start_recording(filename, resize=(int(cam_width),int(cam_height)), quality=20)
                    recording=True
                    last_split=time.time()
                elif time.time()-last_split>int(config['Recording']['video_length']) and recording:
                    print('split recording')
                    filename_new=config['General']['feeder_id']+'_'+datetime.datetime.utcnow().strftime("%Y-%m-%d-%H-%M-%S")+'.h264'
                    cam.split_recording(filename_new)
                    last_split=time.time()
                    os.rename(filename, config['Recording']['video_dir']+"/"+filename)
                    filename=filename_new
                if recording:
                    cam.wait_recording(float(config['Background']['bg_time']))
                else:
                    time.sleep(float(config['Background']['bg_time']))
            cam.stop_recording()
        cam.stop_preview()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("config_path", default="raspicam.cfg")
    args = parser.parse_args()

    run_camera(args.config_path)

