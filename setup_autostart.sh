#!/bin/bash

# Usage: ./setup_autostart.sh /path/to/raspicam raspicam_cfg_filename /path/to/imgstorage txfr_cfg_filename

# Check if all parameters are provided
if [ "$#" -ne 4 ]; then
    echo "Usage: $0 workingdirectory_for_raspicam raspicam_cfg_filename workingdirectory_for_imgstorage txfr_cfg_filename"
    exit 1
fi

# Assign parameters to variables
WORKINGDIR_RASPICAM=$1
RASPICAM_CFG_FILENAME=$2
WORKINGDIR_IMGSTORAGE=$3
TXFR_CFG_FILENAME=$4

# Create systemd service file for raspicam
RASPICAM_SERVICE=/etc/systemd/system/raspicam.service
echo "Creating systemd service file for raspicam at $RASPICAM_SERVICE"
sudo bash -c "cat > $RASPICAM_SERVICE" << EOF
[Unit]
Description=bb_raspicam
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=$WORKINGDIR_RASPICAM
ExecStart=/usr/bin/python3 raspicam.py $RASPICAM_CFG_FILENAME
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# Create systemd service file for imgstorage
IMGSTORAGE_SERVICE=/etc/systemd/system/imgstorage.service
echo "Creating systemd service file for imgstorage at $IMGSTORAGE_SERVICE"
sudo bash -c "cat > $IMGSTORAGE_SERVICE" << EOF
[Unit]
Description=bb_imgstorage_nfs
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=$WORKINGDIR_IMGSTORAGE
ExecStart=/usr/bin/python3 imgstorage.py $TXFR_CFG_FILENAME
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd to recognize new services
echo "Reloading systemd daemon"
sudo systemctl daemon-reload

# Enable services
echo "Enabling services to start at boot"
sudo systemctl enable raspicam.service
sudo systemctl enable imgstorage.service

echo ""
echo "Setup complete!  raspicam and imgstorage will start on boot."
echo "To start manually, use these commands:"
echo "sudo systemctl start raspicam.service"
echo "sudo systemctl start imgstorage.service"
echo ""
echo "To stop:"
echo "sudo systemctl stop raspicam.service"
echo "sudo systemctl stop imgstorage.service"
