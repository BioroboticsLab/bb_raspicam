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
sudo apt install xrdp realvnc-vnc-server realvnc-vnc-viewer ntp vim tmux network-manager-vpnc vpnc 

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
git clone https://github.com/BioroboticsLab/bb_raspicam.git
pip3 install --user --upgrade git+https://github.com/waveform80/picamera.git

## Check that the date/time is correct:
date --iso-8601=ns

## Setup the VPN connection (if needed)
sudo apt install openconnect network-manager-openconnect-gnome

connect with:
sudo openconnect -u USERNAME -b vpn.fu-berlin.de

## Setup to mount lab server computer using nfs (this host computer needs to already be configured)
sudo apt install nfs-common
sudo mkdir /mnt/cirruspi
sudo mount cirrus:/pi /mnt/cirruspi

or add to /etc/fstab mount automatically

cirrus:/pi    /mnt/cirruspi   nfs auto,nofail,noatime,nolock,intr,tcp,actimeo=1800 0 0


# Workflow on RPi and associated server
1) Connect to Rpi via SSH and verify the time is updated
ssh pi@exitcam0.local
date --iso-8601=ns

2) If needed - connect to VPN network
sudo openconnect -u jdavidson -b vpn.fu-berlin.de


3) Mount

3) Start camera program on RPi.  Use either exitcam.cfg or feedercam.cfg as input
tmux
cd bb_raspicam
python3 raspicam.py exitcam.cfg 

