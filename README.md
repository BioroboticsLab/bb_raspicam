# bb_raspicam
python code for automatic feeder and hive entrance cams. automatically detects bees and stores short videos to be decoded by bb_pipeline

#
Raspberry Pi install:
## RPi OS and options
- Download and install [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on your computer.
- Enable SSH and hostname identification in the install options.  Note hostnames that are used - these are needed to setup nfs access on the lab server computer
- Flash the OS with appropriate version to the SD card

##  On RPi: update and install requirements and useful packages
sudo apt update
sudo apt upgrade
sudo apt install xrdp realvnc-vnc-server realvnc-vnc-viewer ntp vim tmux openconnect network-manager-openconnect-gnome

## configure time server
sudo vim /etc/ntp.conf
-- Comment out the lines starting with “pool”
-- Add:  
server time.fu-berlin.de minpoll 3 maxpoll 8

## enable services to start automatically on reboot
sudo systemctl enable vncserver-x11-serviced.service
sudo systemctl enable ntp.service
sudo raspi-config
-- Go to ‘Interfacing options’ and enable camera.
-- reboot

## download/install needed repositories
cd ~
git clone https://github.com/jacobdavidson/bb_raspicam.git
cd bb_raspicam
git fetch origin updates_2024
git checkout updates_2024
cd ..
git clone https://github.com/jacobdavidson/bb_imgstorage_nfs.git
cd bb_imgstorage_nfs
git fetch origin updates_2024
git checkout updates_2024
cd ..
pip3 install --user --upgrade git+https://github.com/waveform80/picamera.git

## Check that the date/time is correct:
date --iso-8601=ns


# Workflow on RPi and associated server
1) Connect to Rpi via SSH and verify the time is updated
ssh pi@exitcam0.local
date --iso-8601=ns

2) If needed - connect to VPN network
sudo openconnect -u USERNAME -b vpn.fu-berlin.de

3) Start camera program on RPi.  Use either exitcam.cfg or feedercam.cfg as input
tmux new -s cam
cd bb_raspicam
python3 raspicam.py exitcam.cfg 

tmux new -s txfr
cd bb_imgstorage_nfs
