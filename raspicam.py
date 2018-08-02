import time
from picamera import PiCamera, array
import datetime
import configparser
import os
import numpy as np

# background accumulation via exponential average
class Background:
    # parameters:
    # ------------------
    # alpha     : 
    # threshold :
    # delay     :
    def __init__(self, alpha, threshold, delay):
        self.alpha = alpha
        self.active = False
        self.threshold = threshold
        self.initialized = False
        self.last_active = time.time()
        self.delay = delay
    
    # called every frame to update background hypothesis
    def update_bg(self,img):
        if not self.initialized:
            self.background = img
            self.initialized = True
        else:
            # total amount of image difference to background
            changedpx=np.sum(np.abs(self.background - img))
            #print(self.background)
            print(changedpx)
            if changedpx < self.threshold:
                self.active = False
            else:
                self.active = True
                self.last_active = time.time()
                
            self.background = self.background * self.alpha + img * (1-self.alpha)
        
    def is_active(self):
        return time.time() - self.last_active < self.delay

config = configparser.ConfigParser()
config.read("raspicam.cfg")

bg = Background(float(config['Background']['alpha']), int(config['Background']['threshold']),int(config['Background']['delay']))

MAX_WIDTH = 2592	
MAX_HEIGHT = 1944
cam_width = float(config['Recording']['zoom_w']) * MAX_WIDTH
cam_height = float(config['Recording']['zoom_h']) * MAX_HEIGHT


with PiCamera(sensor_mode = 2) as cam:
    cam.framerate = int(config['Recording']['framerate'])
    cam.zoom = (float(config['Recording']['zoom_x']),float(config['Recording']['zoom_y']),float(config['Recording']['zoom_w']),float(config['Recording']['zoom_h']))
    cam.exposure_compensation = int(config['Recording']['exposure_compensation'])
    #cam.resolution=(1920,1080)
    cam.color_effects=(128,128)
    
    # window parameter doesnt work as API says. window remains small and position is changed with different widths and heights
    #cam.start_preview(fullscreen=False, window=(0, 0, int(cam_width/2), int(cam_height/2)))
    cam.start_preview(fullscreen=False, window=(0, 0, 640, 480))
    cam.exposure_mode = 'off'
    cam.awb_mode = 'off'
    cam.shutter_speed = 5*1000
    
    #time.sleep(20)
    recording = False
    #cam.wait_recording(5)
    last_split=time.time()
    still=None
    filename=""
    with array.PiRGBArray(cam,size=(int(cam_width),int(cam_height))) as output:
        cam.capture(output, 'rgb', use_video_port=True, resize=(int(cam_width),int(cam_height)))
        still = output.array[:,:,0]
        time.sleep(5)
        output.truncate(0)
        while True:
            cam.capture(output, 'rgb', use_video_port=True, resize=(int(cam_width),int(cam_height)))
            still = output.array[:,:,0]
            bg.update_bg(still)
            output.truncate(0)
            if (not bg.is_active()) and recording:
                print('move file')
                os.rename(filename, config['Recording']['video_dir']+"/"+filename)
                cam.stop_recording()
                recording=False
            elif bg.is_active() and not recording:
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
                cam.wait_recording(int(config['Background']['bg_time']))
            else:
                time.sleep(int(config['Background']['bg_time']))
        cam.stop_recording()
    cam.stop_preview()
