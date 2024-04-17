#!/bin/bash

# Update and upgrade the system
echo "Updating and upgrading..."
sudo apt update && sudo apt upgrade -y

# Install necessary packages
echo "Installing necessary packages..."
sudo apt install -y xrdp realvnc-vnc-server realvnc-vnc-viewer ntp vim tmux openconnect network-manager-openconnect-gnome

# Configure NTP server
echo "Configuring the NTP time server..."
# comment out lines that start with pool
sudo sed -i '/^pool/s/^/#/' /etc/ntp.conf
echo "server time.fu-berlin.de minpoll 3 maxpoll 8" | sudo tee -a /etc/ntp.conf

# Enable services
echo "Enabling NTP time and vnc servers to start at boot..."
sudo systemctl enable vncserver-x11-serviced.service
sudo systemctl enable ntp.service

# Clone necessary repositories and check out updates
echo "Cloning necessary repositories..."
cd ~
git clone https://github.com/jacobdavidson/bb_imgstorage_nfs.git
cd bb_imgstorage_nfs
git fetch origin updates_2024
git checkout updates_2024
cd ..

# Install Python packages
echo "Installing Python packages..."
pip3 install --user --upgrade git+https://github.com/waveform80/picamera.git

echo 'Install done.'

# Raspberry Pi configuration
echo "Please run 'sudo raspi-config', enable the camera under 'Interfacing Options' and reboot system"