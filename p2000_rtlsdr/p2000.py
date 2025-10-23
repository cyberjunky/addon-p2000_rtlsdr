#!/usr/bin/env python3
import os
import sys
import re
import json
import signal
import subprocess
import ssl
import calendar
import fnmatch
import threading
from datetime import timezone, datetime
from json.decoder import JSONDecodeError
import time
from fcntl import ioctl
from stat import S_ISCHR
import requests
import usb.core
import paho.mqtt.publish as publish
from geopy.distance import geodesic
from paho.mqtt import MQTTException
import sqlite3


class Database:
    """Contains all the database stuff."""

    def __init__(self):
        """Initialize database."""

        self.db = self.open_database()
        if not self.db:
            log_message('Cannot open the database, exiting.')
            # Stop the add-on
            sys.exit(1)
        self.cursor = self.db.cursor()
        
    def open_database(self):
        """Open the database."""

        dbpath = f"/data/p2000.sqlite3"

        if not os.path.exists(dbpath):
            log_message(f"Installing the database '{dbpath}'")
            proc = subprocess.Popen('cp /p2000.sqlite3 /data/p2000.sqlite3', shell=True, stdin=None, stdout=None, stderr=None, executable="/bin/bash")
            proc.wait()

        try:
            dbconnection = sqlite3.connect(f"file:{dbpath}?mode=rw", uri=True)
            dbconnection.row_factory = sqlite3.Row
            log_message(f"Database '{dbpath}' opened successfully")

        except sqlite3.OperationalError:
            log_message(f"Error while trying to open database '{dbpath}'")
            return False

        return dbconnection

    def database_stats(self):
        """Display some database statistics."""

        info = "Containing:"
        for tablename in ['places','capcodes', 'geocodes']:
            cnt = self.cursor.execute(f"SELECT count() FROM '{tablename}'").fetchone()[0]
            info += f" {cnt} {tablename}"
        log_message(info)

    def check_plaatsnaam(self, plaatsnaam):
        """Return True if plaatsnaam is in table."""

        query = f"SELECT EXISTS(SELECT 1 FROM places WHERE city = '{plaatsnaam}')"

        return self.cursor.execute(query).fetchone()[0]

    def find_plaatsnaam(self, abbreviation):
        """Return full location name for abbreviated one."""

        query = f"SELECT city FROM places WHERE abbreviation = '{abbreviation}'"

        return self.cursor.execute(query).fetchone()[0]

    def check_pltsnm(self, pltsnm):
        """Return True if pltsnm is in table."""

        query = f"SELECT EXISTS(SELECT 1 FROM places WHERE abbreviation = '{pltsnm}')"

        return self.cursor.execute(query).fetchone()[0]

    def find_capcode(self, capcode):
        """Return all info we have for a capcode."""

        query = f"SELECT discipline, region, location, description, remark FROM capcodes WHERE capcode = '{capcode}'"

        return self.cursor.execute(query).fetchone()

    def find_geocode(self, address):
        """Return all info we have for an address."""

        return self.cursor.execute(f"SELECT latitude, longitude, address, mapurl FROM geocodes WHERE query = '{address}'").fetchone()

    def store_geocode(self, query, datatype, latitude, longitude, postalcode, street, city, address, mapurl):
        """Save all info we have for an address."""

        values = (query, datatype, latitude, longitude, postalcode, street, city, address, mapurl)
        query = "INSERT INTO geocodes VALUES (?,?,?,?,?,?,?,?,?)"

        self.cursor.execute(query, values)
        self.db.commit()


class MessageItem:
    """Contains all the Message data."""

    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.message_raw = ""
        self.timestamp = ""
        self.timereceived = time.monotonic()
        self.groupid = ""
        self.receivers = ""
        self.capcodes = []
        self.body = ""
        self.location = ""
        self.postalcode = ""
        self.city = ""
        self.address = ""
        self.street = ""
        self.region = ""
        self.priority = 0
        self.disciplines = ""
        self.remarks = ""
        self.longitude = ""
        self.latitude = ""
        self.opencage = ""
        self.mapurl = ""
        self.distance = ""
        self.tts = ""


class OpenCageGeocodeError(Exception):
    """Base class for all errors/exceptions that can happen when geocoding."""


class InvalidInputError(OpenCageGeocodeError):
    """There was a problem with the input you provided."""

    def __init__(self, bad_value):
        super().__init__()
        self.bad_value = bad_value

    def __unicode__(self):
        return "Input must be a unicode string, not "+repr(self.bad_value)[:100]

    __str__ = __unicode__


class UnknownError(OpenCageGeocodeError):
    """There was a problem with the OpenCage server."""


class RateLimitExceededError(OpenCageGeocodeError):
    """
    Exception raised when account has exceeded it's limit.

    :var datetime reset_time: When your account limit will be reset.
    :var int reset_to: What your account will be reset to.
    """

    def __init__(self, reset_time, reset_to):
        """Constructor."""
        super().__init__()
        self.reset_time = reset_time
        self.reset_to = reset_to

    def __unicode__(self):
        """Convert exception to a string."""
        return ("Your rate limit has expired. "
                f"It will reset to {self.reset_to} on {self.reset_time.isoformat()}"
                )

    __str__ = __unicode__


class NotAuthorizedError(OpenCageGeocodeError):
    """Exception raised when an unautorized API key is used."""

    def __unicode__(self):
        """Convert exception to a string."""
        return "Your API key is not authorized. You may have entered it incorrectly."

    __str__ = __unicode__


class ForbiddenError(OpenCageGeocodeError):
    """Exception raised when a blocked or suspended API key is used."""

    def __unicode__(self):
        """Convert exception to a string."""
        return "Your API key has been blocked or suspended."

    __str__ = __unicode__

def OpenCageGeocode(query, key):

        params =  { 'q': query, 'key': key, 'limit': 1, 'country': 'nl', 'language': 'nl' }
        response_json = {}

        try:
            response = requests.get('https://api.opencagedata.com/geocode/v1/json', params=params, timeout=5)
            response_json = response.json()
        except requests.exceptions.Timeout:
            log_message("Timeout occurred while fetching data from OpenCage")
        except requests.exceptions.ConnectionError:
            log_message("Connection error occurred while fetching data from OpenCage")
        except requests.exceptions.HTTPError:
            if response.status_code == 401:
                raise NotAuthorizedError()
    
            if response.status_code == 403:
                raise ForbiddenError()
    
            if response.status_code in (402, 429):
                # Rate limit exceeded
                reset_time = datetime.utcfromtimestamp(response.json()['rate']['reset'])
                raise RateLimitExceededError(
                    reset_to=int(response.json()['rate']['limit']),
                    reset_time=reset_time
                )
    
            if response.status_code == 500:
                raise UnknownError("500 status code from API")

        except ValueError as excinfo:
            raise UnknownError("Non-JSON result from server") from excinfo

        if 'results' not in response_json:
            raise UnknownError("JSON from API doesn't have a 'results' key")

        return response_json


def check_filter(mylist, text):
    """Check filter data."""

    # If list is not loaded or empty allow all
    if len(mylist) == 0:
        return True

    # Check if text applied matches at least one filter
    for f_str in mylist:
        if fnmatch.fnmatch(text, f_str):
            return True

    return False


def check_filter_with_list(searchlist, list_to_be_searched):
    """Check filter data with list."""

    # If list is not loaded or empty allow all
    if len(searchlist) == 0:
        return True

    # Check every text in the searchedlist
    for searchedtext in list_to_be_searched:
        if check_filter(searchlist, searchedtext) == True:
            return True

    return False


def to_local_datetime(utc_dt):
    """Convert UTC to local time."""

    time_tuple = time.strptime(utc_dt, "%Y-%m-%d %H:%M:%S")
    return time.ctime(calendar.timegm(time_tuple))


def p2000_get_prio(message):
    """Look for priority strings and return level."""

    priority = 0
    regex_prio1 = r"^A\s?1|\s?A\s?1|PRIO\s?1|^P\s?1"
    regex_prio2 = r"^A\s?2|\s?A\s?2|PRIO\s?2|^P\s?2"
    regex_prio3 = r"^B\s?1|^B\s?2|^B\s?3|PRIO\s?3|^P\s?3"
    regex_prio4 = r"^PRIO\s?4|^P\s?4"

    if re.search(regex_prio1, message, re.IGNORECASE):
        priority = 1
    elif re.search(regex_prio2, message, re.IGNORECASE):
        priority = 2
    elif re.search(regex_prio3, message, re.IGNORECASE):
        priority = 3
    elif re.search(regex_prio4, message, re.IGNORECASE):
        priority = 4

    return priority


def reset_usb_device(usbdev):
    """Reset USB device."""

    if usbdev is not None and ':' in usbdev:
        busnum, devnum = usbdev.split(':')
        filename = "/dev/bus/usb/{:03d}/{:03d}".format(int(busnum), int(devnum))
        if os.path.exists(filename) and S_ISCHR(os.stat(filename).st_mode):
            USBDEVFS_RESET = ord('U') << (4*2) | 20
            fd = open(filename, "wb")
            if int(ioctl(fd, USBDEVFS_RESET, 0)) != 0:
                log_message(f"Error resetting USB device '{filename}'!")
            else:
                log_message(f"Reset of USB device '{filename}' successful")
            fd.close()


def load_id_file(sdl_ids_file):
    """Load USB device id's."""

    device_ids = []
    with open(sdl_ids_file) as f:
        for line in f:
            li = line.strip()
            if re.match(r"(^(0[xX])?[A-Fa-f0-9]+:(0[xX])?[A-Fa-f0-9]+$)", li) is not None:
                # device_ids.append(line.rstrip().lstrip().lower())
                device_ids.append(line.strip().lower())
    return device_ids


def find_rtl_sdr_devices():
    """Find RTL-SDR device."""

    # Load the list of all supported device ids
    DEVICE_IDS = load_id_file('/var/lib/sdl_ids.txt')
    devices_found = {}
    index = -1
    for dev in usb.core.find(find_all = True):
        for known_dev in DEVICE_IDS:
            usb_id, usb_vendor = known_dev.split(':')
            if dev.idVendor == int(usb_id, 16) and dev.idProduct == int(usb_vendor, 16):
                index += 1
                devices_found[known_dev] = { 'bus_address': '{:03d}:{:03d}'.format(dev.bus, dev.address), 'index': index}
                log_message('RTL-SDR device {} found on USB port {:03d}:{:03d} - Index: {}'.format(known_dev, dev.bus, dev.address, index))
                break
    return devices_found


def log_message(message, log=True):
    """Function to log messages to STDERR."""

    if log == True:
        now = datetime.now()
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
        print(f'{dt_string}: {message}', file=sys.stderr)


class MqttSender:
    """MQTT sender class."""

    def __init__(self, mqtt_config, debug):
        """Initialize class."""

        log_message('Configured MQTT sender:')
        self.d = {}
        self.d['hostname'] = mqtt_config.get('host', 'localhost')
        self.d['port'] = int(mqtt_config.get('port', 1883))
        self.d['username'] = mqtt_config.get('user', None)
        self.d['password'] = mqtt_config.get('password', None)
        self.d['client_id'] = mqtt_config.get('client_id', 'p2000_rtlsdr')
        self.d['base_topic'] = mqtt_config.get('base_topic', 'p2000_rtlsdr')
        self.d['availability_topic'] = '{}/status'.format(self.d['base_topic'])
        tls_enabled = mqtt_config.get('tls_enabled', False)
        tls_ca = mqtt_config.get('tls_ca', '/etc/ssl/certs/ca-certificates.crt')
        tls_cert = mqtt_config.get('tls_cert', None)
        cert_reqs = ssl.CERT_NONE if mqtt_config.get('tls_insecure', True) else ssl.CERT_REQUIRED
        tls_keyfile = mqtt_config.get('tls_keyfile', None)
        self.d['tls'] = None
        self.debug = debug

        if tls_enabled:
            self.d['tls'] = { 'ca_certs': tls_ca, 'certfile': tls_cert, 'keyfile': tls_keyfile, 'cert_reqs': cert_reqs }
        self.__log_mqtt_params(**self.d)

    def __get_auth(self):
        """Handle auth config."""

        if self.d['username'] and self.d['password']:
            return { 'username':self.d['username'], 'password': self.d['password'] }
        return None

    def publish(self, **kwargs):
        """Publish MQTT data."""

        if self.debug:
            log_message('Sending message to MQTT:')
            self.__log_mqtt_params(**kwargs)
        topic = kwargs.get('topic')
        payload = kwargs.get('payload', None)
        qos = int(kwargs.get('qos', 0))
        retain = kwargs.get('retain', False)
        will = { 'topic': self.d['availability_topic'], 'payload': 'offline', 'qos': 1, 'retain': True }
        try:
            publish.single(
                topic=topic, payload=payload, qos=qos, retain=retain, hostname=self.d['hostname'], port=self.d['port'],
                client_id=self.d['client_id'], keepalive=60, will=will, auth=self.__get_auth(), tls=self.d['tls']
            )
        except MQTTException as e:
            log_message('MQTTException connecting to MQTT broker: {}'.format(e), True)
            return False
        except Exception as e:
            log_message('Unknown exception connecting to MQTT broker: {}'.format(e), True)
            return False
        return True

    def __log_mqtt_params(self, **kwargs):
        """Log MQTT data."""

        for k, v in ((k, v) for (k, v) in kwargs.items() if k not in ['password']):
            log_message(' > {} => {}'.format(k, v))


def shutdown(signum, frame):
    """Use signal to shutdown and hard kill opened processes and self."""

    if signum == frame == 0:
        log_message('Kill process called.')
    else:
        log_message('Shutdown detected, killing process.')

    if signum != 0 and frame != 0:
        log_message('Graceful shutdown.')
        # Graceful termination
        sys.exit(0)


def load_config():
    """Load config from options file."""

    # Load config from options file
    config = json.load(open(os.path.join('/data/options.json')))

    # Add sensors to config
    if len(config['p2000_sensors']) < 1:
        log_message('No P2000 sensors defined. Exiting...')
        sys.exit(-1)

    # Ask supervisor for MQTT config if host is empty
    if config['mqtt'].get('host', None) is None:
        api_url = "http://supervisor/services/mqtt"
        headers = {"Authorization": "Bearer " + os.getenv("SUPERVISOR_TOKEN")}
        log_message(f"Fetching MQTT configuration from '{api_url}'")
        try:
            resp = requests.get(api_url, headers=headers)
            resp.raise_for_status()

            d = resp.json()['data']
            config['mqtt']['host'] = d.get('host')
            config['mqtt']['port'] = d.get('port')
            config['mqtt']['user'] = d.get('username', None)
            config['mqtt']['password'] = d.get('password', None)
            config['mqtt']['tls_enabled'] = d.get('ssl', False)
            if config['mqtt']['tls_enabled']:
                config['mqtt']['tls_ca'] = '/etc/ssl/certs/ca-certificates.crt'
                config['mqtt']['tls_insecure'] = True
        except Exception as err:
            log_message("Could not fetch default MQTT configuration: {err}")
    else:
        log_message("MQTT Host defined in config file. Ignoring Supervisor's MQTT Configuration...")

    return config

# Create signal handlers/call back
signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)


class Main:
    """Main loop."""

    def __init__(self):
        """Main class, start of application."""

        self.running = True
        self.messages = []

        log_message('P2000 RTL-SDR starting...')

        # Load configuration
        self.config = load_config()

        # Find and reset USB device
        usb_device_index = ''
        usb_devices = find_rtl_sdr_devices()
        if len(usb_devices) < 1:
            log_message('No RTL-SDR USB devices found. Exiting...')
            sys.exit(1)

        usb_device_id = list(usb_devices.keys())[0]
        usb_port = str(usb_devices[usb_device_id]['bus_address'])
        reset_usb_device(usb_port)

        # Read config variables
        self.debug = False
        if self.config['general']['verbosity'] == 'debug':
            self.debug = True

        # RTLSDR parameters
        self.rtlfm_cmd = 'rtl_fm -f 169.65M -M fm -s 22050 | multimon-ng -a FLEX -t raw -'
        if 'rtlsdr' in self.config:
            if 'cmd' in self.config['rtlsdr']:
                self.rtlfm_cmd = self.config['rtlsdr']['cmd']

        # opencage parameters
        self.use_opencage = False
        self.opencage_disabled = False
        self.opencagetoken = ''
        if 'opencage' in self.config:
            if 'enabled' in self.config['opencage']:
                self.use_opencage = self.config['opencage']['enabled']

            if 'token' in self.config['opencage']:
                self.opencagetoken = self.config['opencage']['token']

        # Load capcodes ignore data
        self.ignorecapcodes = ''
        if 'p2000_global_filters' in self.config:
            if 'ignore_capcode' in self.config['p2000_global_filters']:
                self.ignorecapcodes = self.config['p2000_global_filters']['ignore_capcode'].split(',')

        # Load text ignore data
        self.ignoretext = ''
        if 'p2000_global_filters' in self.config:
            if 'ignore_text' in self.config['p2000_global_filters']:
                self.ignoretext = self.config['p2000_global_filters']['ignore_text'].split(',')

        # Set current folder so we can find the config files
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

        # Build dict of sensor configs
        self.sensors = {}
        sensor_names = set()

        # Load all sensors from config
        for sensor in self.config['p2000_sensors']:
            sensor_id = str(sensor['id']).strip()
            sensor_name = str(sensor.get('name', 'meter_{}'.format(sensor_id)))

            if sensor_id in self.sensors or sensor_name in sensor_names:
                log_message('Error: Duplicate sensor name ({}) or id ({}) found in config. Exiting.'.format(sensor_name, sensor_id), True)
                sys.exit(1)

            self.sensors[sensor_id] = sensor.copy()
            sensor_names.add(sensor_name)

            self.sensors[sensor_id]['state_topic'] = '{}/{}/state'.format(self.config['mqtt']['base_topic'], sensor_id)
            self.sensors[sensor_id]['attribute_topic'] = '{}/{}/attributes'.format(self.config['mqtt']['base_topic'], sensor_id)
            self.sensors[sensor_id]['name'] = sensor_name
            self.sensors[sensor_id]['icon'] = str(sensor.get('icon', 'mdi:fire-truck'))
            self.sensors[sensor_id]['sent_HA_discovery'] = False

        # Build dict of TTS settings config
        self.tts_replacements = list()

        # Load all TTS settings
        for tts_replacement in self.config['tts_replacements']:
            self.tts_replacements.append(tts_replacement.copy())

        log_message('{} TTS replacements loaded from config.'.format(len(self.tts_replacements)), True)

        for tts in self.tts_replacements:
            log_message('    Pattern: {}, Replacement: {}'.format(tts['pattern'], tts['replacement']), True)

        # Init MQTT
        self.mqtt_sender = MqttSender(self.config['mqtt'], self.debug)
        availability_topic = '{}/status'.format(self.config['mqtt']['base_topic'])

        # Report ourselves 'online'
        self.mqtt_sender.publish(topic=availability_topic, payload='online', retain=True)

        # Start thread to get data from RTL-SDR stick
        receive_thread = threading.Thread(name="ReceiveThread", target=self.receive_thread_call)
        receive_thread.start()

        # Start thread to update sensors in Home Assistant
        process_thread = threading.Thread(name="ProcessThread", target=self.process_thread_call)
        process_thread.start()

        # Run the wait loop
        while True:
            time.sleep(1)

        # Application is interrupted and is stopping
        self.running = False
        log_message("Application stopped")


    def post_data(self, msg):
        """Filter and post sensor data."""

        log_message(
            f"Message '{msg.body}' received, checking criterias:", self.debug
        )
        
        # Loop through all sensors
        for id in self.sensors:

            self.name = ''
            self.icon = ''
            self.zone_radius = ''
            self.zone_coordinates = ''
            self.searchkeyword = ''
            self.searchcapcode = ''
            self.searchregion = ''
            self.searchdiscipline = ''
            self.searchlocation = ''
            self.searchremark = ''
            post = False

            if 'name' in self.sensors[id]:
                self.name = self.sensors[id]['name']

            if 'icon' in self.sensors[id]:
                self.icon = self.sensors[id]['icon']
            
            if "zone_latitude" in self.sensors[id] and "zone_longitude" in self.sensors[id] and "zone_radius" in self.sensors[id]:
                self.zone_coordinates = (
                    float(self.sensors[id]['zone_latitude']),
                    float(self.sensors[id]['zone_longitude'])
                )
                self.zone_radius = self.sensors[id]['zone_radius']

            if 'keyword' in self.sensors[id]:
                self.searchkeyword = self.sensors[id]['keyword'].split(',')

            if 'capcode' in self.sensors[id]:
                self.searchcapcode = self.sensors[id]['capcode'].split(',')

            if 'region' in self.sensors[id]:
                self.searchregion = self.sensors[id]['region'].split(',')

            if 'discipline' in self.sensors[id]:
                self.searchdiscipline = self.sensors[id]['discipline'].split(',')

            if 'location' in self.sensors[id]:
                self.searchlocation = self.sensors[id]['location'].split(',')

            if 'remark' in self.sensors[id]:
                self.searchremark = self.sensors[id]['remark'].split(',')

            # If location is known and radius is specified in config calculate distance and check radius
            if msg.latitude and msg.longitude and self.zone_radius:
                event_coordinates = (msg.latitude, msg.longitude)
                msg.distance = round(
                    geodesic(
                        self.zone_coordinates, event_coordinates
                    ).km,
                    2,
                )
                if msg.distance <= float(self.zone_radius):
                    log_message(
                        f"Distance MATCHED {msg.distance} km, inside {self.zone_radius} km radius", self.debug
                    )
                else:
                    log_message(
                        f"Distance UNMATCHED {msg.distance} km, outside {self.zone_radius} km radius", self.debug
                    )
                    msg.is_posted = True
                    continue
                post = True

            # Check for matched text/keyword
            if len(self.searchkeyword):
                if not check_filter(self.searchkeyword, msg.body):
                    log_message(
                        f"Keywords UNMATCHED '{', '.join(self.searchkeyword)}'", self.debug
                    )
                    msg.is_posted = True
                    continue
                log_message(
                    f"Keywords MATCHED '{', '.join(self.searchkeyword)}'", self.debug
                )
                post = True

            # Check for matched regions
            if len(self.searchregion):
                if not check_filter(self.searchregion, msg.region):
                    log_message(
                        f"Regions UNMATCHED '{', '.join(self.searchregion)}'", self.debug
                    )
                    msg.is_posted = True
                    continue
                log_message(
                    f"Regions MATCHED '{', '.join(self.searchregion)}'", self.debug
                )
                post = True

            # Check for matched location
            if len(self.searchlocation):
                if not check_filter(self.searchlocation, msg.location):
                    log_message(
                        f"Locations UNMATCHED '{', '.join(self.searchlocation)}'", self.debug
                    )
                    msg.is_posted = True
                    continue
                log_message(
                    f"Locations MATCHED '{', '.join(self.searchlocation)}'", self.debug
                )
                post = True

            # Check for matched remark
            if len(self.searchremark):
                if not check_filter(self.searchregion, msg.region):
                    log_message(
                        f"Remarks UNMATCHED '{', '.join(self.searchremark)}'", self.debug
                    )
                    msg.is_posted = True
                    continue
                log_message(
                    f"Remarks MATCHED '{', '.join(self.searchremark)}'", self.debug
                )
                post = True

            # Check for matched regions
            if len(self.searchregion):
                if not check_filter(self.searchregion, msg.region):
                    log_message(
                        f"Regions UNMATCHED '{', '.join(self.searchregion)}'", self.debug
                    )
                    msg.is_posted = True
                    continue
                log_message(
                    f"Regions MATCHED '{', '.join(self.searchregion)}'", self.debug
                )
                post = True

            # Check for matched capcodes
            if len(self.searchcapcode):
                if not check_filter_with_list(self.searchcapcode, msg.capcodes):
                    log_message(
                        f"Capcodes UNMATCHED '{', '.join(self.searchcapcode)}'", self.debug
                    )
                    msg.is_posted = True
                    continue
                log_message(
                    f"Capcodes MATCHED '{', '.join(msg.capcodes)}'", self.debug
                )
                post = True

            # Check for matched disciplines
            if len(self.searchdiscipline):
                if not check_filter(self.searchdiscipline, msg.disciplines):
                    log_message(
                        f"Disciplines UNMATCHED '{', '.join(self.searchdiscipline)}'", self.debug
                    )
                    msg.is_posted = True
                    continue
                log_message(
                    f"Disciplines MATCHED '{', '.join(msg.disciplines)}'", self.debug
                )
                post = True

            # No other matches are valid, if distance is not valid, skip
            if post is False:
                log_message(
                    f"Message IGNORED no criterias matched", self.debug
                )
                msg.is_posted = True
                continue
            else:
                log_message(
                    f"Message MATCHED criterias, updating sensor", self.debug
                )

            """Post data to Home Assistant via MQTT topic."""
            attributes = {
                "time received": msg.timestamp,
                "group id": msg.groupid,
                "receivers": msg.receivers,
                "capcodes": msg.capcodes,
                "priority": msg.priority,
                "disciplines": msg.disciplines,
                "raw message": msg.message_raw,
                "region": msg.region,
                "location": msg.location,
                "postal code": msg.postalcode,
                "city": msg.city,
                "address": msg.address,
                "street": msg.street,
                "remarks": msg.remarks,
                "longitude": msg.longitude,
                "latitude": msg.latitude,
                "opencage": msg.opencage,
                "mapurl": msg.mapurl,
                "distance": msg.distance,
                "tts": msg.tts,
            }

            if self.config['mqtt']['ha_autodiscovery']:
                # if HA Autodiscovery is enabled, send the MQTT auto discovery payload once for each sensor
                if not self.sensors[id]['sent_HA_discovery']:
                    log_message('Sending MQTT autodiscovery payload to Home Assistant...', self.debug)
                    discover_topic = '{}/sensor/p2000_rtlsdr/{}/config'.format(self.config['mqtt']['ha_autodiscovery_topic'], self.sensors[id]['id'])
                    discover_payload = {
                        'name': self.sensors[id]['name'],
                        'unique_id': str(self.sensors[id]['id']),
                        'icon': self.sensors[id]['icon'],
                        'availability_topic': '{}/status'.format(self.config['mqtt']['base_topic']),
                        'force_update': True,
                        'state_topic': 'homeassistant/sensor/' + self.sensors[id]['state_topic'],
                        'json_attributes_topic': 'homeassistant/sensor/' + self.sensors[id]['attribute_topic']
                    }
                    self.mqtt_sender.publish(topic=discover_topic, payload=json.dumps(discover_payload), qos=1, retain=True)
                    self.sensors[id]['sent_HA_discovery'] = True

            attribute_topic = 'homeassistant/sensor/' + self.sensors[id]['attribute_topic']
            state_topic = 'homeassistant/sensor/' + self.sensors[id]['state_topic']
            self.mqtt_sender.publish(topic=attribute_topic, payload=json.dumps(attributes), retain=True)
            self.mqtt_sender.publish(topic=state_topic, payload=msg.body, retain=True)

            log_message(f"Sensor '{self.sensors[id]['name']}': '{msg.body}'", self.debug)

        msg.is_posted = True


    def receive_thread_call(self):
        """Thread for receiving and parsing with RTL-SDR."""

        # Open the database
        self.database = Database()
        self.database.database_stats()
        self.skipthesekeywords = []

        log_message(f"RTL-SDR process starting with: {self.rtlfm_cmd}")
        multimon_ng = subprocess.Popen(
            self.rtlfm_cmd, stdout=subprocess.PIPE, shell=True
        )
        log_message("Message receive thread started")
        while self.running:
            # Read line from process
            line = multimon_ng.stdout.readline()
            try:
                line = line.decode("utf8", "backslashreplace")
            except UnicodeDecodeError:
                log_message(f"Error while decoding utf8 string: '{line}'", True)
                line = ""
            multimon_ng.poll()
            if line.startswith("FLEX") and line.__contains__("ALN"):
                line_data = line.split("|")
                timestamp = line_data[1]
                groupid = line_data[3].strip()
                capcodes = line_data[4].strip()
                message = line_data[6].strip()
                priority = p2000_get_prio(message)
                location = ""
                postalcode = ""
                city = ""
                address = ""
                street = ""
                longitude = ""
                latitude = ""
                opencage = ""
                distance = ""
                mapurl = ""
                geocoded = False
                rate_remaining = 9999

                log_message(line.strip(), self.debug)

                # Global filters
                # Check capcodes first, only if they are defined in config global filter
                if self.ignorecapcodes:
                    for capcode in capcodes.split(" "):
                        if len(capcodes.split(" ")) == 1:
                            if capcode in self.ignorecapcodes:
                                log_message(
                                    f"Message '{message}' ignored because it contains only one capcode '{capcode}' and MATCHED ignore_capcodes", self.debug
                                )
                                continue

                # Check for ignore texts if define in global filter
                if self.ignoretext:
                    if check_filter(self.ignoretext, message):
                        log_message(
                            f"Message '{message}' ignored MATCHED ignore_text", self.debug
                        )
                        continue

                # Get address info if any, look for valid postalcode and get the two words around them
                # A2 (DIA: ja) AMBU 17106 Schiedamseweg 3134BA Vlaardingen VLAARD bon 8576
                # or with only postalcode number
                # A1 13108 Surinameplein 1058 Amsterdam 12006
                addr = re.search(r"(\w*.) ([1-9][0-9]{3})([A-Z]{2})? (.\w*)", message)
                if addr:
                    street = addr.group(1)
                    groups = len(addr.groups())
                    if groups == 4:
                        # Add space between digits and letter of postalcode to get better OpenCage results
                        postalcode = f"{addr.group(2)} {addr.group(3)}"
                        city = addr.group(4)
                    elif groups == 3:
                        postalcode = {addr.group(2)}
                        city = addr.group(3)
                    address = f"{street} {postalcode} {city}"

                # Try to get city only when there is one after a prio
                # A1 Breda
                else:
                    loc = re.search(r"(^A\s?1|\s?A\s?2|B\s?1|^B\s?2|^B\s?3|PRIO\s?1|^P\s?1|PRIO\s?2|^P\s?2) (.\w*)", message)
                    #if loc and loc.group(2) in self.plaatsnamen:
                    if loc and self.database.check_plaatsnaam(loc.group(2).replace("'","")):
                        city = loc.group(2)
                    else:
                        # Find all uppercase words with len 3 or longer and check if there is a valid city name amoung them
                        # A2 Ambulancepost Moordrecht Middelweg MOORDR V
                        afkortingen = re.findall("[A-Z]{3,}", message)
                        if afkortingen:
                            log_message(f"Searching for a city using abbrev. in '{afkortingen}'", self.debug)
                        for afkorting in afkortingen:
                            if afkorting not in self.skipthesekeywords:
                                log_message(f"Checking if '{afkorting}' is a city abbrev.", self.debug)
                                if self.database.check_pltsnm(afkorting):
                                    city = self.database.find_plaatsnaam(afkorting)
                                    log_message(f"City '{city}' found", self.debug)
                                    # If uppercase city is found, grab first word before that city name, since it's likely to be the streetname
                                    addr = re.search(rf"(\w*.) ({afkorting})", message)
                                    if addr:
                                        street = addr.group(1)
                                    address = f"{street} {city}"
                                    # Change uppercase city to normal city in message
                                    message = re.sub(afkorting, city, message)
                                else:
                                    self.skipthesekeywords.append(afkorting)

                    # If no address is found, do a wild guess to get a city name at least
                    if not address:
                        # Strip all status info from message
                        strip = re.sub(r"(^A\s?1|\s?A\s?2|B\s?1|^B\s?2|^B\s?3|PRIO\s?1|^P\s?1|PRIO\s?2|^P\s?2|^PRIO\s?3|^P\s?3|^PRIO\s?4|^P\s?4)(\W\d{2,}|.*(BR)\b|)|(rit:|rit|bon|bon:|ambu|dia)\W\d{5,8}|\b\d{5,}$|( : )|\(([^\)]+)\)( \b\d{5,}|)|directe (\w*)|(-)+/gi", "", message, flags=re.I)
                        # Strip any double and leading/trailing spaces from message 
                        strip = re.sub(r"(^[ \t]+|[ \t]+$)", "", strip.strip())
                        # Search in leftover message for a city corresponding to City list
                        log_message(f"Searching for a city in '{strip}'", self.debug)

                        for plaatsnaam in strip.replace("'","").split(" "):
                            if plaatsnaam not in self.skipthesekeywords:
                                log_message(f"Checking if '{plaatsnaam}' is a city", self.debug)
                                if self.database.check_plaatsnaam(plaatsnaam):
                                    log_message(f"City '{plaatsnaam}' found", self.debug)
                                    # Find first word left from city
                                    plaatsnamen_strip = re.search(
                                        rf"\w*.[a-z|A-Z] \b{plaatsnaam}\b", strip
                                    )
                                    if plaatsnamen_strip:
                                        # Final non-address symbols strip
                                        address = re.sub(
                                            r"(- )|(\w[0-9] )", "", plaatsnamen_strip.group(0)
                                        )
                                        city = plaatsnaam
                                        log_message(
                                            f"Address found: '{address}'", self.debug
                                        )
                                else:
                                    self.skipthesekeywords.append(plaatsnaam)

                # Get more info using the capcodes data
                for capcode in capcodes.split(" "):
                    result = self.database.find_capcode(capcode)
                    if result:
                        log_message(f"Capcode {capcode}: Disc: '{result['discipline']}' Reg: '{result['region']}' Loc: '{result['location']}' Descr: '{result['description']}' Remark: '{result['remark']}'", self.debug)
                        description = f"{result['description']} ({capcode})"
                        discipline = result['discipline']
                        region = result['region']
                        location = result['location']
                        remark = result['remark']
                    else:
                        description = capcode
                        discipline = ""
                        region = ""
                        remark = ""

                log_message(f"DEBUG message post: {message}", self.debug)

                # If this message was already received, only add extra info
                if len(self.messages) > 0 and self.messages[0].body == message:
                    if self.messages[0].receivers == "":
                        self.messages[0].receivers = description
                    elif description:
                        self.messages[0].receivers += ", " + description

                    if self.messages[0].disciplines == "":
                        self.messages[0].disciplines = discipline
                    elif discipline:
                        self.messages[0].disciplines += ", " + discipline
                    if self.messages[0].remarks == "":
                        self.messages[0].remarks = remark
                    elif remark:
                        self.messages[0].remarks += ", " + remark

                    if self.messages[0].region == "":
                        self.messages[0].region = region

                    self.messages[0].capcodes.append(capcode)
                    self.messages[0].location = location
                    self.messages[0].postalcode = postalcode
                    self.messages[0].city = city
                    self.messages[0].street = street
                    self.messages[0].address = address
                else:
                    # TODO
                    # After midnight (UTC), reset the opencage disable
                    hour = datetime.now(timezone.utc).replace(tzinfo=None)
                    if (
                        hour.hour >= 0
                        and hour.minute >= 1
                        and hour.hour < 1
                        and hour.minute < 15
                    ):
                        self.opencage_disabled = False

                    # If address is filled and OpenCage is enabled check for GPS coordinates
                    # First check local GPS database
                    if address and self.use_opencage:
                        try:
                            log_message(f"Checking gps database for '{address}'", self.debug)
                            geocode = self.database.find_geocode(address.replace("'", ""))
                            if geocode:
                                log_message(
                                    f"Address '{address}' was found in geocode database", self.debug
                                )
                                latitude = geocode["latitude"]
                                longitude = geocode["longitude"]
                                mapurl = geocode["mapurl"]
                                log_message(
                                    f"GPS database results: {latitude}, {longitude}, {mapurl}", self.debug
                                )
                                geocoded = True
                        except KeyError as err:
                            log_message(
                                    f"Address '{address}' was not found in gps database", self.debug
                                )

                    # If not found in GPS database file, check opencage
                    # If address is filled and OpenCage is enabled check for GPS coordinates and mapurl
                    if (
                        address
                        and self.use_opencage
                        and (self.opencage_disabled is False)
                        and (geocoded is False)
                    ):
                        try:
                            log_message(
                                    f"OpenCage query: '{address}'", self.debug
                            )
                            locations = OpenCageGeocode(address, self.opencagetoken)
                            log_message(f"OpenCageGecode: {locations}", self.debug)
                            if int(locations['total_results']) > 0:

                                postcode = ""
                                road = ""
                                oc_address = ""
                                datatype = locations['results'][0]['components']['_type']

                                # Plaats can be in city, town or village field
                                if 'city' in locations['results'][0]['components']:
                                    plaats = locations['results'][0]['components']['city']
                                if 'town' in locations['results'][0]['components']:
                                    plaats = locations['results'][0]['components']['town']
                                if 'village' in locations['results'][0]['components']:
                                    plaats = locations['results'][0]['components']['village']
                                if 'road' in locations['results'][0]['components']:
                                    road = locations['results'][0]['components']['road']
                                if 'postcode' in locations['results'][0]['components']:
                                    postcode = locations['results'][0]['components']['postcode']

                                if plaats and plaats in address or (plaats == 'Den Haag' and 's-Gravenhage' in address):
                                    latitude = locations['results'][0]['geometry']['lat']
                                    longitude = locations['results'][0]['geometry']['lng']
                                    mapurl = locations['results'][0]['annotations']['OSM']['url']
                                    rate_remaining = locations['rate']['remaining']
                                    
                                    # OpenCage returned a different postal code, keep the original but update rest of addresss
                                    if datatype == 'city':
                                        oc_address = f"{plaats}"
                                    elif postcode and road:
                                        oc_address = f"{road}, {postcode} {plaats}"

                                    log_message(
                                        f"OpenCage results: {datatype} {latitude}, {longitude}, '{oc_address}', '{mapurl}'", self.debug
                                    )

                                    try:
                                        self.database.store_geocode(address, datatype, str(latitude), str(longitude), postcode, street, plaats, oc_address, mapurl)

                                        geocoded = True
                                    except:
                                        log_message(
                                            f"Error while trying to store geocode data in database: '{address}'", True
                                        )
                                else:
                                    latitude = ""
                                    longitude = ""
                                    mapurl = ""
                                    log_message(f"OpenCage API returned invalid location for given address (or returned wrong city for example): '{plaats}'", self.debug)
                            else:
                                latitude = ""
                                longitude = ""
                                mapurl = ""
                                log_message(f"OpenCage API didn't return any location data for this address: '{address}'", self.debug)
                            
                        except IndexError as err:
                            log_message(f"IndexError: '{err}' occurred while parsing: '{locations}'", True)
                            latitude = ""
                            longitude = ""
                            mapurl = ""
                            geocoded = False
                        except (RateLimitExceededError) as err:
                            log_message(err, True)
                            # Rate limit reached, disable opencage until midnight
                            self.opencage_disabled = True
                        except (InvalidInputError, NotAuthorizedError, ForbiddenError, UnknownError) as err:
                            log_message(err, True)
                    else:
                        geocoded = False

                    #Replace all TTS replacement
                    tts = message
                    for tts_replacement in self.tts_replacements:
                        tts = re.sub(tts_replacement['pattern'], tts_replacement['replacement'], tts)
  
                    opencage = f"enabled: {self.use_opencage} ratelimit: {self.opencage_disabled} ({rate_remaining}) geocoded: {geocoded}"

                    msg = MessageItem()
                    msg.groupid = groupid
                    msg.receivers = description
                    msg.capcodes = capcodes.split(" ")
                    msg.body = message
                    msg.message_raw = line.strip()
                    msg.disciplines = discipline
                    msg.priority = priority
                    msg.region = region
                    msg.location = location
                    msg.postalcode = postalcode
                    msg.longitude = longitude
                    msg.latitude = latitude
                    msg.city = city
                    msg.street = street
                    msg.address = address
                    msg.remarks = remark
                    msg.opencage = opencage
                    msg.mapurl = mapurl
                    msg.timestamp = to_local_datetime(timestamp)
                    msg.is_posted = False
                    msg.distance = distance
                    msg.tts = tts
                    self.messages.insert(0, msg)

            # TODO
            # Limit the message list size
            if len(self.messages) > 20:
                self.messages = self.messages[:20]

        log_message("Message receive thread stopped")


    def process_thread_call(self):
        """Thread for processing data."""

        log_message("Processing thread started")
        while True:
            if not self.running:
                break

            now = time.monotonic()
            for msg in self.messages:
                if msg.is_posted is False and now - msg.timereceived >= 1.0:
                    self.post_data(msg)
            time.sleep(1)

        log_message("Processing thread stopped")


# Start Add-on
Main()
