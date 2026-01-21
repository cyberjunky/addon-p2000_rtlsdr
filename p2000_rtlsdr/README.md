[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
![Project Maintenance][maintenance-shield]

[![Donate via PayPal](https://img.shields.io/badge/Donate-PayPal-blue.svg?style=for-the-badge&logo=paypal)](https://www.paypal.me/cyberjunkynl/)
[![Sponsor on GitHub](https://img.shields.io/badge/Sponsor-GitHub-red.svg?style=for-the-badge&logo=github)](https://github.com/sponsors/cyberjunky)

# P2000 RTL-SDR Add-on for Home Assistant

_Receive P2000 emergency services events using Home Assistant and your RTL-SDR dongle._

![Supports aarch64 Architecture][aarch64-shield]
![Supports amd64 Architecture][amd64-shield]
![Supports armhf Architecture][armhf-shield]
![Supports armv7 Architecture][armv7-shield]
![Supports i386 Architecture][i386-shield]

![Example dashboard in Home Assistant Frontend](images/screenshot.png)

## About

An all-in-one Home Assistant add-on for receiving P2000 emergency services pager messages directly from the air using an RTL-SDR dongle. Filter messages by region, discipline, capcode, or location and create detailed sensors with geocoded location data.

## ⚠️ Warning

Even though this add-on was created and is maintained with care and security in mind, it may damage your system. Use at your own risk.

## ✨ Features

- **📡 Live P2000 Reception** - Receive emergency services messages in real-time using RTL-SDR
- **🔌 Wide Hardware Support** - Compatible with many RTL-SDR dongle models
- **🔧 Auto Configuration** - Automatic MQTT and Home Assistant device discovery
- **🎯 Advanced Filtering** - Filter by text, capcode, region, discipline, or location
- **📍 Geocoding** - Optional OpenCage integration for coordinates and map links
- **📚 Comprehensive Database** - Detailed capcode and city names database included
- **🗣️ TTS Ready** - Configurable text-to-speech replacements

## 🔄 How It Works

1. The add-on detects your RTL-SDR dongle and performs a port reset
2. Loads the capcode and city database, initializes the MQTT sender
3. Starts `rtl_fm` tuned to 169.65 MHz (P2000 frequency) and pipes data through `multimon-ng`
4. Parses FLEX messages, enriches with geocoding data, and queues for processing
5. Matches messages against your sensor filters and updates Home Assistant via MQTT

## 🛠️ Requirements

- Home Assistant OS or Supervised installation
- RTL-SDR compatible USB dongle
- MQTT broker (Mosquitto add-on recommended)
- P2000 antenna (place near a window or outside for best results)

## 📦 Installation

1. Add this repository to your Home Assistant add-on store:

   [![Open your Home Assistant instance and show the add add-on repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fcyberjunky%2Faddon-p2000_rtlsdr)

   Or manually add: `https://github.com/cyberjunky/addon-p2000_rtlsdr`

2. Install the **P2000 RTL-SDR** add-on
3. Configure the add-on options (see Configuration below)
4. Start the add-on
5. Check the logs to verify everything is working

![Example setup](images/setup.png)

## ⚙️ Configuration

> **Note:** Restart the add-on after changing configuration.

### Example Configuration

```yaml
general:
  verbosity: normal
mqtt:
  ha_autodiscovery: true
  ha_autodiscovery_topic: homeassistant
  base_topic: p2000_rtlsdr
  tls_enabled: false
opencage:
  enabled: false
  token: your_api_token_here
rtlsdr:
  cmd: rtl_fm -f 169.65M -M fm -s 22050 | multimon-ng -a FLEX -t raw -
p2000_global_filters:
  ignore_text: "*Test*,*test*,*TEST*"
  ignore_capcode: 123456789,987654321
p2000_sensors:
  - id: 2001
    name: P2000 Dordrecht e.o
    icon: mdi:ambulance
    zone_radius: 10
    zone_latitude: 51.8133
    zone_longitude: 4.6685
  - id: 2002
    name: P2000 GRIP meldingen
    icon: mdi:magnify
    keyword: "*GRIP*,*Grip*,*grip*"
  - id: 2003
    name: P2000 Lifeliners
    icon: mdi:helicopter
    capcode: "*001420059*,*000923993*"
  - id: 2004
    name: P2000 Amsterdam
    icon: mdi:map-marker-radius-outline
    region: Amsterdam-Amstelland
tts_replacements:
  - pattern: P 1
    replacement: Prio 1
  - pattern: BOB\-[0-9][0-9]\s
    replacement: ""
```

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `general.verbosity` | Log level: `normal` or `debug` | `normal` |
| `mqtt.ha_autodiscovery` | Auto-register sensors in Home Assistant | `true` |
| `mqtt.host/port` | MQTT broker (leave empty for auto-config) | Auto |
| `opencage.enabled` | Enable geocoding via OpenCage | `false` |
| `opencage.token` | Your [OpenCage API token](https://opencagedata.com/users/sign_up) | - |
| `rtlsdr.cmd` | RTL-SDR command (tweak `-s` if reception is poor) | See above |

### Sensor Filter Options

Each sensor requires `id` and `name`. All filters below are optional and can be combined:

| Filter | Description |
|--------|-------------|
| `zone_radius/latitude/longitude` | Only match events within X km of coordinates |
| `keyword` | Match text patterns (uses `fnmatch` syntax) |
| `capcode` | Match specific capcodes (9 digits, zero-pad if shorter) |
| `region` | Match by region (see list below) |
| `discipline` | Match by service type |
| `location` | Match by location from capcode database |
| `remark` | Match by remark from capcode database |

### Available Regions

`Groningen`, `Friesland`, `Drenthe`, `IJsselland`, `Twente`, `Noord- en Oost-Gelderland`, `Gelderland Midden`, `Gelderland Zuid`, `Utrecht`, `Noord-Holland Noord`, `Zaanstreek-Waterland`, `Kennemerland`, `Amsterdam-Amstelland`, `Gooi en Vechtstreek`, `Haaglanden`, `Hollands-Midden`, `Rotterdam-Rijnmond`, `Zuid-Holland Zuid`, `Zeeland`, `Midden- en West-Brabant`, `Brabant Noord`, `Brabant Zuid-Oost`, `Limburg Noord`, `Limburg Zuid`, `Flevoland`, `Landelijk`

### Available Disciplines

`Ambulance`, `Brandweer`, `Politie`, `Reddingsbrigade`, `KNRM`, `KWC`, `Dares`, `Gemeente`

### TTS Replacements

Use `pattern` (regex) and `replacement` to modify message text for text-to-speech. Set `replacement` to empty string to remove patterns.

## 🔧 Troubleshooting

### Enable Debug Logging

1. Set `verbosity` to `debug` in configuration
2. Restart the add-on
3. Check logs for detailed information

> **⚠️ Warning:** Debug mode generates large log files. Don't leave it enabled long-term.

### Common Issues

| Problem | Solution |
|---------|----------|
| No messages received | Check antenna placement, verify RTL-SDR is detected |
| Corrupt messages | Try adjusting the `-s` parameter in `rtlsdr.cmd` |
| MQTT connection failed | Verify MQTT broker is running, check credentials |
| No sensors appearing | Ensure at least one sensor with valid filters is configured |

## 💖 Support This Project

### 🌟 Ways to Support

- **⭐ Star this repository** - Help others discover the project
- **💰 Financial Support** - Contribute to development costs
- **🐛 Report Issues** - Help improve stability
- **📖 Spread the Word** - Share with other Home Assistant users

### 💳 Financial Support

[![Donate via PayPal](https://img.shields.io/badge/Donate-PayPal-blue.svg?style=for-the-badge&logo=paypal)](https://www.paypal.me/cyberjunkynl/)
[![Sponsor on GitHub](https://img.shields.io/badge/Sponsor-GitHub-red.svg?style=for-the-badge&logo=github)](https://github.com/sponsors/cyberjunky)

Every contribution, no matter the size, is greatly appreciated! 🙏

## 👤 Authors & Contributors

Created by [cyberjunky](https://github.com/cyberjunky)

Got questions or found a bug? [Open an issue on GitHub](https://github.com/cyberjunky/addon-p2000_rtlsdr/issues)

## 📄 License

MIT License - see the [LICENSE](LICENSE) file for details.

---

[releases-shield]: https://img.shields.io/github/release/cyberjunky/addon-p2000_rtlsdr.svg?style=for-the-badge
[releases]: https://github.com/cyberjunky/addon-p2000_rtlsdr/releases
[commits-shield]: https://img.shields.io/github/commit-activity/y/cyberjunky/addon-p2000_rtlsdr.svg?style=for-the-badge
[commits]: https://github.com/cyberjunky/addon-p2000_rtlsdr/commits/main
[license-shield]: https://img.shields.io/github/license/cyberjunky/addon-p2000_rtlsdr.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-cyberjunky-blue.svg?style=for-the-badge
[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
[armhf-shield]: https://img.shields.io/badge/armhf-yes-green.svg
[armv7-shield]: https://img.shields.io/badge/armv7-yes-green.svg
[i386-shield]: https://img.shields.io/badge/i386-yes-green.svg
