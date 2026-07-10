# bb_raspicam
python code for automatic feeder and hive entrance cams. automatically detects bees and stores short videos to be decoded by bb_pipeline

#
Raspberry Pi install:
## RPi OS and options
- Download and install [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on your computer.
- Enable SSH and hostname identification in the install options. Note the hostname (e.g. 'exitcam0' - this can then be used to connect via ssh on the local network)
- Flash the OS with appropriate version to the SD card

##  On RPi:
### 1) Clone repo and run install script:
```
git clone https://github.com/BioroboticsLab/bb_raspicam.git
cd bb_raspicam
sudo bash setup_raspicam.sh
```

### 2) Time sync (Chrony): Internet vs. local server

#### Option A — Pi has Internet (default)
Already configured by `setup_raspicam.sh`:
```bash
# Verify it’s syncing
chronyc sources -v
chronyc tracking
```

#### Option B — Pi has NO Internet (use a local time server)
See [Time server sync setup](time_server_sync_setup.md) for more information; shown here are the main steps

1) Setup a time server on a local computer (see [Time server sync setup](time_server_sync_setup.md)).

2) Ensure the server (here using the name 'roadking') is reachable by name (or use its IP):
```bash
sudo apt install -y avahi-utils libnss-mdns
getent ahosts roadking.local   # should show an IP; otherwise use the IP directly
```

3) Repoint Chrony to your local server and restart:
```bash
# Comment out any existing pool/server lines
sudo sed -i '/^[[:space:]]*\(pool\|server\|sourcedir\)[[:space:]]/s/^/#/' /etc/chrony/chrony.conf

# Add your local server (choose one)
echo "server roadking.local iburst minpoll 3 maxpoll 8" | sudo tee -a /etc/chrony/chrony.conf

sudo systemctl restart chrony
```

4) Verify:
```bash
chronyc sources -v
chronyc tracking
```
You should see `roadking.local` (or `cirrus.local`) once synchronized.


### 3) Check that the date/time is correct:
```
date --iso-8601=ns
```

### 4) Setup SSH key for server
```
ssh-keygen -t rsa -b 2048
ssh-copy-id pi@SERVERNAME
```

### 5) Create user_config.py file for file transfer:
```
cd bb_imgstorage_nfs
vim user_config.py
```
Fill in settings


### 6) Edit config files
Update local copies of **exitcam.cfg** or **feedercam.cfg** with appropriate device number and settings


### 7) (Optional) To enable remote desktop connections via RDP, use X11 desktop
```
sudo raspi-config
```
-- Go to ‘Advanced Options’ then select Wayland
-- Select X11
-- reboot

### 

# Workflow on RPi
1) Connect to Rpi via SSH and verify the time is updated.  Example if the RPi is named 'exitcam0'
```
ssh pi@exitcam0.local
date --iso-8601=ns
```

2) Start camera program on RPi.  Use either exitcam.cfg or feedercam.cfg as input
```
tmux new -s cam
cd bb_raspicam
## Exitcam:
python3 raspicam.py exitcam.cfg 
## Feedercam:
python3 raspicam.py feedercam.cfg 

```

3) Start file transfer on RPi
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

**Re-run this on every Pi after pulling this repo.** The generated units changed: they now use
`Restart=always` (`on-failure` will not restart a service that was sent a SIGTERM, because systemd
counts that as a clean exit), disable systemd's "give up after 5 starts in 10s" limit, and wait for
chrony to sync the clock before recording starts. Existing Pis keep their old units until
`setup_autostart.sh` is run again.

## Monitoring and self-healing

`raspicam.py` touches a heartbeat file (default `/tmp/raspicam_heartbeat`) every 30 captured frames.
[bb_monitor](https://github.com/BioroboticsLab/bb_monitor)'s system check reads its mtime to tell
"the service is running" apart from "the service is running but the camera is silently delivering no
frames" — a failure mode systemd cannot see, because the process stays alive.

Two layers handle that wedge:

1. **Locally**, if no frame arrives for `watchdog_seconds` (default 60) the process exits and
   systemd restarts it within `RestartSec`.
2. **Remotely**, if the process is hung inside a blocking libcamera call and cannot notice, the
   monitor SIGKILLs it over SSH once the stale heartbeat has been seen on two consecutive checks.

Override the defaults with an optional `[Monitoring]` section in your camera config:

```ini
[Monitoring]
heartbeat_path         = /tmp/raspicam_heartbeat
heartbeat_every_frames = 30
watchdog_seconds       = 60      ; 0 disables the local watchdog
```

Because the Pi has no real-time clock, the boot clock is whatever `fake-hwclock` saved until chrony
steps it forward. The service therefore waits (up to 30s) for chrony to sync before recording, so
video filenames and heartbeat mtimes are not stamped with a bogus time.

# Hardware

- [Raspberry Pi 4 / 2 GB](https://www.mouser.de/ProductDetail/358-SC01939)
- [Camera module 3, regular (for feeder cams or general use)](https://www.mouser.de/ProductDetail/358-SC0872)
- [Camera module 3 NoIR (for exit cams)](https://www.mouser.de/ProductDetail/358-SC0873)
- [Raspberry pi power supply](https://www.mouser.de/ProductDetail/358-SC1411)
- [Mouser project: bb exitcam lighting](https://www.mouser.de/api/CrossDomain/GetContext?syncDomains=www&returnUrl=https%3a%2f%2fwww.mouser.com%2fTools%2fProject%2fShare%3fAccessID%3d3c2e08f937&async=False&setPrefSub=False&clearPrefSub=False)
