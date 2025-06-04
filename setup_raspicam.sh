#!/bin/bash

# ===================================================================
# setup_raspicam.sh
#
# Sets up a Raspberry Pi 4 with Camera Module 3 (IMX708) for:
#   • Picamera2 (libcamera) with Python bindings
#   • Chrony NTP synchronization
#   • OpenBox-based desktop + XRDP for remote desktop
#   • Necessary networking and utility packages
#   • ‘bb_imgstorage_nfs’ repository clone
#
# Run this script as root (or via sudo). It will:
#   1. Update/upgrade APT and install libcamera‐apps + Picamera2 Python
#   2. Install OpenBox desktop components and XRDP
#   3. Install Chrony and configure NTP servers
#   4. Enable Chrony, XRDP services
#   5. Add the IMX708 Device Tree Overlay if not already present
#   6. Clone the bb_imgstorage_nfs GitHub repo
#   7. Set default boot behavior to desktop (B4)
# ===================================================================

set -e

## 1. Update & upgrade system 
apt update
apt full-upgrade -y

## 2. Install libcamera-apps and Picamera2 Python bindings ===
apt install -y libcamera-apps python3-picamera2

## 3. Install desktop (OpenBox) + XRDP ===
# The OpenBox-based UI (“raspberrypi-ui-mods” pulls in the Pi’s default desktop environment)
apt install -y raspberrypi-ui-mods lxsession lxterminal lxpanel openbox
apt install -y xrdp
systemctl enable --now xrdp

## 4. Install networking & utility packages
apt install -y chrony vim tmux openconnect network-manager-openconnect-gnome

## 5. Configure Chrony NTP server 
# Comment out default pool lines, then append FU Berlin NTP server
sed -i '/^pool /s/^/#/' /etc/chrony/chrony.conf
echo "server time.fu-berlin.de iburst minpoll 3 maxpoll 8" >> /etc/chrony/chrony.conf
systemctl enable --now chrony

## 6. Ensure IMX708 overlay is set
if grep -q '^dtoverlay=imx708' /boot/config.txt; then
  echo "IMX708 overlay already present in /boot/config.txt"
else
  echo "dtoverlay=imx708" >> /boot/config.txt
  echo "Added 'dtoverlay=imx708' to /boot/config.txt"
fi

## 7. Clone the bb_imgstorage_nfs repository
cd /home/pi || cd ~
if [ ! -d "bb_imgstorage_nfs" ]; then
  git clone https://github.com/BioroboticsLab/bb_imgstorage_nfs.git
else
  echo "Repository 'bb_imgstorage_nfs' already exists; skipping clone"
fi

# 8. Set default boot to desktop (GUI)
raspi-config nonint do_boot_behaviour B4

echo "Setup complete. Please reboot the Pi to apply changes."