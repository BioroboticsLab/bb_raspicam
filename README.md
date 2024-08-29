# bb_raspicam
python code for automatic feeder and hive entrance cams. automatically detects bees and stores short videos to be decoded by bb_pipeline

#
Raspberry Pi install:
## RPi OS and options
- Download and install [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on your computer.
- Enable SSH and hostname identification in the install options. Note the hostname (e.g. 'exitcam0' - this can then be used to connect via ssh on the local network)
- Flash the OS with appropriate version to the SD card

##  On RPi:
### Clone repo and run install script:
```
git clone https://github.com/jacobdavidson/bb_raspicam.git
cd bb_raspicam
git fetch origin updates_2024
git checkout updates_2024
bash setup_raspicam.sh
```

### Enable camera and restart
```
sudo raspi-config
```
-- Go to ‘Interfacing options’ and enable camera.
-- reboot

### Check that the date/time is correct:
```
date --iso-8601=ns
```

### Setup SSH key for server
```
ssh-keygen -t rsa -b 2048
ssh-copy-id pi@SERVERNAME
```

### Create user_config.py file for file transfer:
```
cd bb_imgstorage_nfs
vim user_config.py
```
Fill in settings


### Edit config files
Update local copies of **exitcam.cfg** or **feedercam.cfg** with appropriate device number and settings

### 

# Workflow on RPi
1) Connect to Rpi via SSH and verify the time is updated.  Example if the RPi is named 'exitcam0'
```
ssh pi@exitcam0.local
date --iso-8601=ns
```

2) If needed - connect to VPN network
```
sudo openconnect -u USERNAME -b vpn.fu-berlin.de
```

3) Start camera program on RPi.  Use either exitcam.cfg or feedercam.cfg as input
```
tmux new -s cam
cd bb_raspicam
## Exitcam:
python3 raspicam.py exitcam.cfg 
## Feedercam:
python3 raspicam.py feedercam.cfg 

```

4) Start file transfer on RPi
```
tmux new -s txfr
cd bb_imgstorage_nfs
python imgstorage.py
```

## Auto-start configuration
Use the included script to setup raspicam and imgstorage as system services that start automatically when the RPi is restarted:
```
# Usage: setup_autostart.sh /path/to/bb_raspicam raspicam_cfg_filename /path/to/bb_imgstorage_nfs
# Example:
bash setup_autostart.sh /home/pi/bb_raspicam exitcam.cfg /home/pi/bb_imgstorage_nfs
```
Reboot and then both will start automatically
