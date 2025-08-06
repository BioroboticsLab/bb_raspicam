# Local NTP (Chrony) over Hotspot / LAN
_A step-by-step guide to use a laptop/PC as a time server and Raspberry Pis as clients, with or without Internet._

## Overview

You can keep your Raspberry Pis in sync by running **Chrony** on a computer (the “server”) and pointing the Pis (the “clients”) at it. This works even with **no Internet** (server serves its own clock), and across **hotspots** (NetworkManager shared AP or phone hotspot) or normal Wi-Fi LANs.

This guide covers:

- Server setup (Ubuntu 24/25+ or similar)
- Raspberry Pi client setup (Raspberry Pi OS Bookworm+)
- Hotspot/LAN subnet rules
- Verification & troubleshooting

---

## Network assumptions

- **Server hostname** (example): `roadking` → reachable as `roadking.local` via mDNS.
- **Hotspot/LAN subnets** (pick what you actually use):
  - NetworkManager Wi-Fi Hotspot: typically `10.42.0.0/24` (server IP often `10.42.0.1`)
  - Android phone hotspot: often `192.168.43.0/24`
  - Any other router: check with `ip -4 addr`

Find your active subnet on the **server**:

```bash
ip -4 addr show             # identify the Wi-Fi interface (e.g., wlp… or wlan0)
ip -4 addr show <iface>     # look for: inet X.Y.Z.W/24 → your subnet is X.Y.Z.0/24
```

---

## 1) Server setup (Ubuntu 24/25+)
Note: in this example the server is called 'roadking'.

### 1.1 Set hostname & enable mDNS (so `roadking.local` resolves).  This may already be enabled on the computer, so if it already resolves (ping), then can skip this and go to 1.2.

```bash
sudo hostnamectl set-hostname roadking
sudo apt update
sudo apt install -y avahi-daemon libnss-mdns
sudo systemctl enable --now avahi-daemon
```

Test from another machine on the same Wi-Fi:
```bash
ping -c1 roadking.local
```

### 1.2 Install Chrony

```bash
sudo apt install -y chrony
```

### 1.3 Configure Chrony

Back up and edit the main config:
```bash
sudo cp /etc/chrony/chrony.conf /etc/chrony/chrony.conf.bak.$(date +%s)
sudo nano /etc/chrony/chrony.conf
```

If you are on **Ubuntu 25+**, Chrony may include extra snippets via:
```
sourcedir /etc/chrony/chrony.d
```
Comment that out if you want a minimal, explicit config:
```
#sourcedir /etc/chrony/chrony.d
```

**A) If the server HAS Internet and you want it to sync upstream:**
- Keep a couple of `pool` lines or add your preferred NTP servers.
- Add **allow** for your hotspot/LAN subnet so Pis can query you.
- (Optional) `cmdallow` if you want to run `chronyc clients` from other hosts without sudo.

Example:
```
# Upstream time (keep 1–2 pools)
pool 0.pool.ntp.org iburst
pool 1.pool.ntp.org iburst

# Allow clients on my subnet to use me as NTP server
allow 10.42.0.0/24
# or: allow 192.168.43.0/24

# (Optional) allow chronyc control commands from subnet (e.g., 'chronyc clients')
cmdallow 10.42.0.0/24
```

**B) If the server has NO Internet and should serve its own clock:**
- **Remove/comment** any `pool`/`server` lines.
- Add `local stratum 10` so Chrony serves its own clock.
- Add **allow** for your subnet.
- (Optional) `cmdallow`.

Example (standalone):
```
# Act as a standalone local time source (no upstream)
local stratum 10

# Allow clients on hotspot/LAN
allow 10.42.0.0/24
# or: allow 192.168.43.0/24

# Optional control channel permissions
cmdallow 10.42.0.0/24
```

Save & exit.

### 1.4 Restart & enable Chrony
```bash
sudo systemctl restart chrony
sudo systemctl enable chrony
```

### 1.5 (Optional) Open firewall for NTP/UDP 123
If UFW is enabled:
```bash
sudo ufw allow proto udp to any port 123
sudo ufw reload
```

### 1.6 Verify on the server
```bash
chronyc sources -v      # shows upstream (case A) or local clock (case B)
sudo chronyc clients    # shows clients once Pis start querying
journalctl -u chrony --no-pager | grep -i denied   # check for refused requests
```

---

## 2) Raspberry Pi client setup (Bookworm+)

### 2.1 Ensure mDNS (so `roadking.local` resolves quickly)
```bash
sudo apt update
sudo apt install -y avahi-utils libnss-mdns
getent ahosts roadking.local   # should print an IP
```

> Tip: If mDNS lookups feel slow or your hotspot renumbers, you can pin a static entry in `/etc/hosts` on each Pi:
> ```bash
> echo "10.42.0.1 roadking.local roadking" | sudo tee -a /etc/hosts
> ```
> (Replace `10.42.0.1` with Roadking’s current hotspot IP.)

### 2.2 Install Chrony
```bash
sudo apt install -y chrony
```

### 2.3 Point at the server
```bash
sudo cp /etc/chrony/chrony.conf /etc/chrony/chrony.conf.bak.$(date +%s)
sudo nano /etc/chrony/chrony.conf
```

Comment out default pools/servers and add your server:

```
# Comment out any defaults:
# pool ...
# server ...

# Use the local server (by name)
server roadking.local iburst minpoll 3 maxpoll 8

# (Optional) add a fallback server if Roadking is sometimes unavailable:
# server thria.local iburst minpoll 3 maxpoll 8
```

Save & exit.

### 2.4 Restart & enable Chrony
```bash
sudo systemctl restart chrony
sudo systemctl enable chrony
```

### 2.5 Verify on the Pi
Immediately:
```bash
chronyc sources -v
chronyc tracking
```
After ~30–60s you should see `^* roadking.local` in `sources` and a sensible offset/skew in `tracking`.

Quick one-shot query (also tests UDP 123 reachability):
```bash
sudo apt install -y ntpdate
ntpdate -q roadking.local
```

---

## 3) Hotspot notes

- **NetworkManager Wi-Fi Hotspot (Linux)** defaults to `10.42.0.0/24`, server IP `10.42.0.1`.
- **Phone hotspots** often use `192.168.43.0/24` (Android) or other `192.168.x.0/24`.
- Always match the **server’s** active subnet in `allow` (and `cmdallow` if you use it).
- If you change hotspot types, update `allow` and restart Chrony on the server.

---

## 4) Troubleshooting

**Symptom:** `chronyc clients` on server says `501 Not authorised`  
- That message refers to Chrony’s **control channel**, not NTP service.  
- Run as root: `sudo chronyc clients`  
- Or add `cmdallow <your-subnet>/24` to server’s `chrony.conf` and restart.

**Symptom:** Pi shows:
```
chronyc sources
^? roadking.local ...
chronyc tracking → Stratum: 0 / Not synchronised
```
- Give it 30–60 seconds after the first query.
- Verify name resolution: `getent ahosts roadking.local`
- Try direct IP: `server 10.42.0.1 iburst ...` (replace with server IP).
- On server, confirm `allow <subnet>/24` matches the Pi’s actual IP subnet.
- Check firewall: allow UDP/123 on server.

**Symptom:** “Refusing NTP request” or “denied” in server logs  
- `journalctl -u chrony | grep -i denied`  
- Fix `allow` subnet (e.g., `allow 10.42.0.0/24`) and restart Chrony.

**Symptom:** Name resolution slow (mDNS delay)  
- Ensure `libnss-mdns` is installed and `/etc/nsswitch.conf` has:
  ```
  hosts: files mdns4_minimal [NOTFOUND=return] dns myhostname
  ```
- Optionally add static `/etc/hosts` lines for instant lookups.

**Symptom:** Server has no Internet but must still serve time  
- Use the **standalone** config (remove pools; add `local stratum 10`).

---

## 5) Quick automation snippets

**Server (standalone, hotspot 10.42.0.0/24):**
```bash
sudo apt update
sudo apt install -y avahi-daemon libnss-mdns chrony
sudo cp /etc/chrony/chrony.conf /etc/chrony/chrony.conf.bak.$(date +%s)
sudo bash -c 'cat >/etc/chrony/chrony.conf' <<'CONF'
#sourcedir /etc/chrony/chrony.d
local stratum 10
allow 10.42.0.0/24
#cmdallow 10.42.0.0/24
CONF
sudo systemctl restart chrony
sudo systemctl enable chrony
```

**Client (Pi → roadking.local):**
```bash
sudo apt update
sudo apt install -y avahi-utils libnss-mdns chrony
sudo cp /etc/chrony/chrony.conf /etc/chrony/chrony.conf.bak.$(date +%s)
sudo bash -c 'cat >/etc/chrony/chrony.conf' <<'CONF'
server roadking.local iburst minpoll 3 maxpoll 8
CONF
sudo systemctl restart chrony
sudo systemctl enable chrony
chronyc sources -v
chronyc tracking
```

---

## 6) Summary

- Install **Chrony** on the server and Pis.
- On the server: use **`allow <subnet>/24`** (and `local stratum 10` if offline). Comment out `sourcedir` on Ubuntu 25+ if you want a minimal config.
- On the Pis: set **`server roadking.local iburst`** (or the server IP).
- Enable mDNS or add `/etc/hosts` entries for instant resolution.
- Verify with `chronyc sources/tracking` (Pi) and `chronyc clients` (server).