# TAPPER

---

A simple NFC reader built with the RPi Zero 2 W and the Adafruit PN532.
This repository provides a python module with the Tapper class and a simple threaded implementation.

---

## Features

### Module

- MQTT Communication
- MIFARE Classic reading
- TAMPER switch
- RGB LED

### Implementation

- Threaded
- TAMPER Detection

---

## Installation

1. Flash RPi OS Lite (Raspberry Pi Imager)
2. Update RPi with `sudo apt update && sudo apt upgrade`
3. Install packages:
    - `pipx`
    - `git`
4. Install TAPPER: `pipx install 'git+ssh://git@github.com/hardwario/tapper.git/#egg=tapper'`
5. Enable serial port and SPI in `sudo raspi-config`
6. Test TAPPER
    - Run Mosquitto on another machine
    - Run TAPPER:
        - `tapper run -d -h {you_mqtt_host}`

> [!NOTE]
> `-d` enables debug output  
> `-h` specifies the MQTT host
