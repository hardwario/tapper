# TAPPER

A simple NFC reader built with the RPi Zero 2 W and the Adafruit PN532.
This repository provides a python module with the Tapper class and a simple threaded implementation.

## Features

### Module

- MQTT Communication
- MIFARE Classic reading
- TAMPER switch
- RGB LED

### Implementation

- Threaded
- TAMPER Detection

## Installation

1. Flash RPi OS Lite (Raspberry Pi Imager)
2. Update RPi with `sudo apt update && sudo apt upgrade -y`
3. Install packages: `sudo apt install cmake git libdbus-1-dev libglib2.0-dev pipx python3-dev`
    - add pipx binaries to path: `pipx esurepath`
      > [!INFO]
      > This adds an entry into your `~/.bashrc`
4. Enable serial port and SPI in `sudo raspi-config`
5. Install TAPPER: `pipx install 'git+ssh://git@github.com/hardwario/tapper.git@main#egg=tapper'`
    - To install the bleeding-edge version, use
      `pipx install 'git+ssh://git@github.com/hardwario/tapper.git@dev#egg=tapper'`
6. Test TAPPER
    - Run Mosquitto on another machine
    - Run TAPPER:
        - `tapper run -d -h <you_mqtt_host>`

> [!NOTE]
> `-d` enables debug output  
> `-h` specifies the MQTT host

```bash
# For easy copy
sudo apt update && sudo apt upgrade
sudo reboot
# reconnect
sudo apt install git pipx python3-dev cmake libdbus-1-dev libglib2.0-dev
pipx ensurepath
sudo raspi-config # enable serial port and SPI
pipx install 'git+ssh://git@github.com/hardwario/tapper.git@main#egg=tapper' # stable
tapper run -h <your_mqtt_host>
```

## Contributing

For new features, create a branch starting with `feat/` and then rebase your changes into `dev`.
From `dev` changes are merged into `main`.
