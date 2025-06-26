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
2. Update RPi with `sudo apt update && sudo apt upgrade`
3. Install packages:
    - `pipx`
        - To add all tools to PATH: `pipx ensurepath`
    - `git`
    - `python3-dev`
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
sudo apt install git pipx python3-dev
pipx ensurepath
sudo raspi-config
pipx install 'git+ssh://git@github.com/hardwario/tapper.git@main#egg=tapper'
tapper run -h <your_mqtt_host>
```

## Contributing

For new features, create a branch starting with `feat/` and then rebase your changes into `dev`.
From `dev` changes are merged into `main`.
