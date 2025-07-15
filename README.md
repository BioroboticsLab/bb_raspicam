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
git clone https://github.com/BioroboticsLab/bb_raspicam.git
cd bb_raspicam
sudo bash setup_raspicam.sh
```

### (Optional) To enable remote desktop connections via RDP, use X11 desktop
```
sudo raspi-config
```
-- Go to ‘Advanced Options’ then select Wayland
-- Select X11
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
# Usage: ./setup_autostart.sh /path/to/raspicam raspicam_cfg_filename /path/to/imgstorage txfr_cfg_filename
# Example:
bash setup_autostart.sh /home/pi/bb_raspicam exitcam.cfg /home/pi/bb_imgstorage_nfs txfr_exitcam.py
```
Reboot and then both will start automatically

# Hardware

- [Raspberry Pi 4 / 2 GB](https://www.mouser.de/ProductDetail/358-SC01939)
- [Camera module 3, regular (for feeder cams or general use)](https://www.mouser.de/ProductDetail/358-SC0872)
- [Camera module 3 NoIR (for exit cams)](https://www.mouser.de/ProductDetail/358-SC0873)
- [Raspberry pi power supply](https://www.mouser.de/ProductDetail/358-SC1411)
- [Mouser project: bb exitcam lighting](https://www.mouser.de/api/CrossDomain/GetContext?syncDomains=www&returnUrl=https%3a%2f%2fwww.mouser.com%2fTools%2fProject%2fShare%3fAccessID%3d3c2e08f937&async=False&setPrefSub=False&clearPrefSub=False)
