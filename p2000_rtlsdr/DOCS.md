# Home Assistant Add-on: P2000 RTL-SDR

## WARNING

Even though this add-on was created and is maintained with care and with security in mind, it maybe damage your system. Use at your own risk.


## How does it work?

When the program starts the configuration data is read and parsed.  
It then tries to find the usb port that your RTL-SDR dongle is connected to, and performs a port reset.  

It loads the database data like capcodes and city information, next the MQTT sender is initialized and the add-on is announced on the MQTT availability topic.  

A thread is started to start receiving data from the dongle, this is done by starting a rtl_fm process tunes to the exact frequency of the P2000 waves, rtl_fm pipes the data through multimon-ng to decode FLEX data, every line which starts with 'FLEX' is parsed.  

As much data as possible is extracted, other data is added like lat/long and a mapurl for openstreetmap, all is put in the message queue, another data parse thread is checking new messages against the configured filters and sensors.  

When a message data matches the filters, the sensor values are updated through MQTT publish. If the sensor publishes it's first data after a restart the sensor is announced on the MQTT bus as well so home-assistant creates it automatically for you.


## Installation
The installation of this add-on is pretty straightforward and not different in comparison to installing any other add-on.

1. Add my add-ons repository to your home assistant instance  
   (in supervisor addons store at top right, or click button below if you have configured my HA)  
   [![Open your Home Assistant instance and show the add add-on repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fcyberjunky%2Faddon-p2000_rtlsdr)
1. Install this add-on.
1. Click the `Save` button to store your configuration.
1. Set the add-on options to your preferences (see below)
1. Start the add-on.
1. Check the logs of the add-on to see if everything went well.


Make sure your RTL-SDR dongle is inserted in the Home assistant device.  
Place your antenna in a good location near the window, or even outside.

If you don't see the wanted result, consider setting verbosity to 'debug' and restart.  
Don't leave verbosity debug enabled for a long time, since it logs a lot of data, and can wear out your storage devices.

## Configuration
Note: Remember to restart the add-on when the configuration is changed.

P2000 RTL-SDR add-on configuration:

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
  token: cf33174a89f041a7831db5383c41334d30
rtlsdr:
  cmd: rtl_fm -f 169.65M -M fm -s 22050 | multimon-ng -a FLEX -t raw -
p2000_global_filters:
  ignore_text: "*Test*,*test*,*TEST*"
  ignore_capcode: 123456789,987654321
p2000_sensors:
  - id: 2001
    name: P2000 Dordrecht e.o
    icon: mdi:sheep
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
    capcode: "*001420059*,*000923993*,*000923995*,*000320591*"
  - id: 2004
    name: P2000 Amsterdam
    icon: mdi:map-marker-radius-outline
    region: Amsterdam-Amstelland
  - id: 2005
    name: P2000 Rotterdam-Rijnmond
    icon: mdi:map-marker-radius-outline
    region: Rotterdam-Rijnmond
tts_replacements:
  - pattern: P 1
    replacement: Prio 1
  - pattern: P 2
    replacement: Prio 2
  - pattern: BOB\-[0-9][0-9]\s
    replacement: ""      
```

Note: This is just an example, don't copy and paste it! Create your own!

### Option: `general`: `verbosity`
The verbosity option controls the level of log output by the addon and can be changed to be more or less verbose, which might be useful when you are dealing with an unknown issue.  
Default: `normal`

Possible values are:  
 - normal: Only show startup info and sensor update notices.
 - debug: Shows very detailed debug information.

### Option: `mqtt`: `ha_autodiscovery`
Enable or disable ha autodiscovery, when enabled each sensor is automatically added to the home-assistance device database.  
Default: `true`
 - true: Enabled
 - false: Disabled

### Option `mqtt`: `ha_autodiscovery_topic`
The MQTT topic used to sent autodiscovery message to, don't change.  
Default: `homeassistant`

### Option `mqtt`: `base_topic`
The MQTT topic used to sent device messages to, no need to change.  
Default: `p2000_rtlsdr`

### Option `mqtt`: `tls_enabled`
Enabled or disable TLS support, only need to enable if your MQTT broker uses certificates and you want to use manual MQTT configuration instead of automatic config supplied by the Supervisor.  
Default: `false`

 - true: Enabled
 - false: Disabled

### Option `mqtt`: `tls_ca`
The certificate to use if `tls_enabled` is true  
Example: '/etc/ssl/certs/ca-certificates.crt'

Default: not specified

### Option `mqtt`: `tls_insecure`    
Ignore self-signed certificates if set to true, only used in a manual MQTT configuration

 - true: Enabled
 - false: Disabled

Default: not specified

### Option `mqtt`: `host`
### Option `mqtt`: `port`
The hostname and port your MQTT broker runs on, don't specify them to use built-in auto configuration via the supervisor.  
Default: not specified

### Option `mqtt`: `username`
### Option `mqtt`: `password`
The username and password for authentication with your MQTT broker runs, don't specify them to use built-in authentication mechanism for addons.  
Default: not specified

### Option `opencage`: `enabled`
Enabled or disable OpenCage support, this service will try to get lat/long data from an address, including a maplink, enable if you created an account at https://opencagedata.com and created an API token.  
Default: `false`

 - true: Enabled
 - false: Disabled

### Option `rtlsdr`: `cmd`
The command options for the `rtl_fm` command, responsible for tuning in to the P2000 radio signals.  
Default `"rtl_fm -f 169.65M -M fm -s 22050 | multimon-ng -a FLEX -t raw -"`

NOTE: If you don't receive any messages or corrupt ones -even though you have a good antenna setup- you may have to tweak the -s parameter slightly.

### Option `opencage`: `token`
Your API token for OpenCage.  
Default: bogus string

You can create a free account here https://opencagedata.com/users/sign_up it has a limitation on API calls per day (2500), even though this is sufficient most of the times, the add-on will detect ratelimits and pause opencage functionality until midnight.  It also stores query results in the database to limit the number of calls.

### Option `p2000_global_filters`: `ignore_text`
Keywords you want to filter all incoming message with even before they hit the device filters, separated them using comma's.  
Default: `"*Test*,*test*,*TEST*"`

If any keyword matches the message text it will be discarded.
NOTE: Filter command used is `fnmatch` you may want to look up it's syntax for special cases.

### Option `p2000_global_filters`: `ignore_capcode`
Capcodes you want to filter all incoming message with even before they hit the device filters, separated the using comma's.  
Default: `123456789,987654321`

NOTE: Capcodes used are 9 digits long, add zero's on the left is the ones you found are shorter.

### Option `p2000_sensors`: `id`
This section specifies one or more P2000_sensors with their filter criteria.
`id` is a mandatory setting, specify an unique value without spaces or special characters, numbers are convenient.

### Option `p2000_sensors`: `name`
`name` is a mandatory setting, names are allowed to have spaces, this is the 'device name' in home-assistant, but you can override it manually using the GUI if needed.

### Option `p2000_sensors`: `icon`
`icon` is an optional setting, if not specifed the 'mdi:fire-truck' icon is used.

Thee following filters are 'matching filters' opposed to the global filter which are 'ignore values'.

### Option `p2000_sensors`: `zone_radius` `zone_longitude` `zone_latitude`
These are optional (but they are a set and belong to each other)  
You can combine them _but this is optional as well_ with one or more of the criteria settings below.

### Option `p2000_sensors`: `keyword`
This setting is optional. You can specify one or more keyword seperated by comma's, if at least one of them matches the text in the message received -and any other criteria (if any) for this sensor matches- the message text and it's attributes are applied to the sensor.

NOTE: The function used to match this filter is called `fnmatch`.

### Option `p2000_sensors`: `capcode`
This setting is optional. You can specify one or more capcodes seperated by comma's, if at least one of them matches the capcodes in the message received -and any other criteria (if any) for this sensor matches- the message text it's attributes are applied to the sensor.
NOTE: Capcodes used in this add-on are 9 positions long, if you found one shorter append 0's from the left.

### Option `p2000_sensors`: `region`
This setting is optional. You can specify one or more regions seperated by comma's, if at least one of them matches the region in the message received -and any other criteria (if any) for this sensor matches- the message text and it's attributes are applied to the sensor.
Available regions are:  
`Groningen`  
`Friesland`  
`Drenthe`  
`IJsselland`  
`Twente`  
`Noord-Oost Gelderland` (needs to be merged with below)  
`Noord- en Oost-Gelderland`  
`Gelderland Midden`  
`Gelderland Zuid`  
`Utrecht`  
`Noord-Holland Noord`  
`Zaanstreek-Waterland`  
`Kennemerland`  
`Amsterdam-Amstelland`  
`Gooi en Vechtstreek`  
`Haaglanden`  
`Hollands-Midden`  
`Rotterdam-Rijnmond`  
`Zuid-Holland Zuid`  
`Zeeland`  
`Midden- en West-Brabant`  
`Brabant Noord`  
`Brabant Zuid-Oost`  
`Limburg Noord`  
`Limburg Zuid`  
`Flevoland`  
`Landelijk`


### Option `p2000_sensors`: `discipline`
This one is optional too. You can specify one or more disciplines seperated by comma's, if at least one of them matches the discipline linked to the capcode in the message received -and any other criteria (if any) for this sensor matches- the message text and it's attributes are applied to the sensor.
Available disciplines are:  

`Ambulance`  
`Brandweer`  
`Politie`  
`Reddingsbrigade`  
`KNRM`  
`KWC`  
`Dares`  
`Gemeente`

### Option `p2000_sensors`: `location`
This one is optional too. You can specify one or more locations seperated by comma's, if at least one of them matches the location data linked to the capcode in the message received -and any other criteria (if any) for this sensor matches- the message text and it's attributes are applied to the sensor.
This is a free text field, not all of them are known/filled in.

NOTE: `location` data comes from the local database and is not the same as address or city (which are extracted from the messages)


### Option `p2000_sensors`: `remark`
This one is optional too. You can specify one or more remark texts seperated by comma's, if at least one of them matches the remark data linked to the capcode in the message received -and any other criteria (if any) for this sensor matches- the message text and it's attributes are applied to the sensor.
This is a free text field, only a few are filled-in but these are often specific ones like `Narcotica team`, `Onderhandelaar`, `First-Responders`

### Option `tts_replacements`
TTS replacements can be used to change the message to a string which can be used to speak the alarm message. It can be used for example to change the firefighter designations to a text better suitable for speaking (e.g. 224541 to 45 41) or remove the incident channel from the message (e.g. BOB-02).

### Option `tts_replacements`: `pattern`
The pattern to search for in the message

### Option `tts_replacements`: `replacement`
The replacement, use an empty string to completely remove part of the message (e.g. the incident channel)


NOTE: `region`, `discipline`, `location` and `remark` information is looked-up in a local database using the `capcodes` retrieved from the messages. It's not available in the over-the-air traffic, so it can be incomplete, outdated and incorrect.
