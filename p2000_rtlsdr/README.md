# Home Assistant Add-on: P2000 RTL-SDR

_Receive P2000 events using Home Assistant and your RTL-SDR dongle._

![Supports aarch64 Architecture][aarch64-shield]
![Supports amd64 Architecture][amd64-shield]
![Supports armhf Architecture][armhf-shield]
![Supports armv7 Architecture][armv7-shield]
![Supports i386 Architecture][i386-shield]

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
[armhf-shield]: https://img.shields.io/badge/armhf-yes-green.svg
[armv7-shield]: https://img.shields.io/badge/armv7-yes-green.svg
[i386-shield]: https://img.shields.io/badge/i386-yes-green.svg

## About

An all-in-one add-on for receiving P2000 events from the air, filter them as you like and update sensors with detailed information.

## Features

This add-on is based on my standalone project called 'RTL-SDR-P2000Receiver-HA' which had been created to run on a seperate Linux device,  it was rewritten as an Hassio add-on, I left out unneeded code, added MQTT autoconfigure and optimized it.

It comes out of the box with the following features:

 - Standalone P2000 messages receiver using a local RTL-SDR compatible receiver
 - Support for a large number of RTL-SDR dongles models
 - Automatic MQTT sender configuration and device discovery/creation
 - Global text and capcode filter options
 - Unlimited number of sensors and filters (as long as hardware resources can handle it)
 - Includes detailed capcode and city names database created from data on https://www.tomzulu10capcodes.nl and http://p2000.bommel.net
 - Code to guess and complete as much address data as possible
 - Geocode functionality using https://opencagedata.com to get rough lat/long location and maps links, fetched data is stored for future use.

