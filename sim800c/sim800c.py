"""
SIM800 Controller

Central module control, including all serial communication and device state management
"""

import os
import serial
from time import sleep, time
import json
import logging
import sys
import re

from .config import (
    SERIAL_PORT,
    BAUD_RATE,
    SERIAL_READ_TIMEOUT,
    PROVIDER,
    BOOT_WAIT_TIME,
    HTTP_REQUEST_TIMEOUT,
    HTTP_POST_UPLOAD_TIMEOUT,
    SERIAL_COMMAND_PAUSE,
    RESET_GPIO_PIN
)

from .exceptions import (
    GPRSError,
    GPRSATCheckError,
    GPRSGPRSCheckError,
    GPRSGetProviderError,
    GPRSSetProviderError,
    GPRSEnableWirelessError,
    GPRSGetIpError,
    GPRSSMSError,
    GPRSTCPError,
    GPRSHTTPError
)

from .sms import SMS
from .tcpip import TCPIP

logger = logging.getLogger(__name__)

class Sim800C(object):

    def __init__(self,
                 serial_port=SERIAL_PORT,
                 baudrate=BAUD_RATE,
                 serial_read_timeout=SERIAL_READ_TIMEOUT,
                 provider=PROVIDER,
                 bootup=True,
                 cmd_pause=SERIAL_COMMAND_PAUSE,
                 gpio_reset_pin=RESET_GPIO_PIN
                 ):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.serial_read_timeout = serial_read_timeout
        self.provider = provider
        self.ser = None
        self.cmd_pause = cmd_pause
        self.at_terminator = b'\r\n'
        self.ip = None
        self.sms_throttle_time = 600.0  # Time forced between sms message sending
        self.last_sms_time = 0.0
        self.serial_init_at_checks = 1
        self.resets_without_success = 0
        self.gpio_reset_pin = gpio_reset_pin
        self.sms = SMS(self)
        self.tcpip = TCPIP(
            self,
            http_request_timeout=HTTP_REQUEST_TIMEOUT,
            http_post_upload_timeout=HTTP_POST_UPLOAD_TIMEOUT
        )
        if bootup is True:
            self.reset(enable_gprs=True)

    def _await_serial(self, pause_time=0.5):
        '''
        Wait some time for a serial command
        '''
        sleep(pause_time)

    def init_serial(self, max_await=30):
        '''
        Initialise the serial interface (does NOT connect to GPRS)
        '''
        logger.debug('Init GPRS Serial')
        self.ser = serial.Serial(
            port=self.serial_port,
            baudrate=self.baudrate,
            timeout=self.serial_read_timeout
        )
        # Wait for serial boot
        logger.debug('awaiting serial response...')
        start = time()
        while True:
            if time() - start > max_await:
                raise Exception("Failed to initialise serial - check port etc", '')
            try:
                self.at_check_ready()
                return
            except:
                sleep(0.1)
        if not self.ser:
            raise Exception("Failed to initialise serial - check port etc", '')

    # AT Commands - Strings and Wrapped
    def _at_commands(self, simple_cmd):
        '''
        Convert a simple command reference to an AT command
        https://www.waveshare.com/wiki/SIM800C_GSM/GPRS_HAT
        https://www.waveshare.com/w/upload/7/76/SIM800_Series_AT_Command_Manual_V1.10.pdf
        '''
        at_cmd_map = {
            'test_at': 'AT',
            'reset_default_config': 'ATZ',
            'get_signal_quality': 'AT+CSQ',
            'test_grps_service_status': 'AT+CGATT?',
            'disable_gprs': 'AT+CGATT=0',
            'enable_gprs': 'AT+CGATT=1',
            'set_provider': 'AT+CSTT=',
            'get_provider': 'AT+CSTT?',
            'enable_wireless': 'AT+CIICR',
            'get_ip': "AT+CIFSR",
            'set_cipmode': "AT+CIPMODE=0",
            'connect_tcp_client': 'AT+CIPSTART=\"TCP\",',
            'tcp_send_string': 'AT+CIPSEND=',
            'close_tcp_client': 'AT+CIPCLOSE',
            'close_pdp': 'AT+CIPSHUT',
            'set_sms_mode': 'AT+CMGF=1',
            'set_sms_phone_number': 'AT+CMGS=',
            'read_sms': 'AT+CMGR=',
            'delete_sms': 'AT+CMGD=',
            'delete_all_sms': 'AT+CMGDA=\"DEL ALL\"',
            'http_configure_conn_bearer': 'AT+SAPBR=3,1,\"Contype\",\"GPRS\"',
            'http_configure_conn_bearer_apn': 'AT+SAPBR=3,1,\"APN\",\"EE\"',
            'http_open_gprs_context': 'AT+SAPBR=1,1',
            'http_query_gprs_context': 'AT+SAPBR=2,1',
            'http_init': 'AT+HTTPINIT',
            'http_set_param_cid': 'AT+HTTPPARA=\"CID\",1',
            'http_set_param_url': 'AT+HTTPPARA=\"URL\",',
            'http_post_data': 'AT+HTTPDATA=',
            'http_get_session_start': 'AT+HTTPACTION=0',
            'http_post_session_start': 'AT+HTTPACTION=1',
            'http_session_status': 'AT+HTTPSTATUS?',
            'http_get_data': 'AT+HTTPREAD',
            'http_terminate_session': 'AT+HTTPTERM',
            'http_close_gprs_context': 'AT+SAPBR=0,1',
            'http_redir_enable': 'AT+HTTPPARA="REDIR",1',
            'http_redir_disable': 'AT+HTTPPARA="REDIR",0',
            'https_enable': 'AT+HTTPSSL=1',
            'https_disable': 'AT+HTTPSSL=0'
        }
        return at_cmd_map.get(simple_cmd, None)

    def at_check_ready(self):
        '''
        Check the system is ready to receive AT commands
            i.e. Serial is connected, AT is responding
            AT result is flushed - i.e. its JUST getting OK - not the response to other commands
            SMS Stuck - if something happens while sending an SMS AT can get stuck in text entry mode (>)
        '''
        if not self.ser:
            raise GPRSATCheckError(
                "AT Check-Ready Failed - AT OK Command Failed, or Serial not initialised", '')
        if not self.ser.isOpen():
            raise GPRSATCheckError(
                "AT Check-Ready Failed - Serial not open -c onect first", '')
        # Do the AT check cmd a few times to ensure we get a good response
        for i in range(self.serial_init_at_checks):
            logger.debug('Send AT Check %s', i)
            res = self.do_at_command('test_at')
            chk = self.at_response_ok(res)
            logger.debug('AT Check Result: %s', chk)
        if not chk:
            raise GPRSATCheckError('AT Check Failed after {} retries'.format(
                self.serial_init_at_checks), '')

    def at_response_ok(self, response):
        if response.find('ERROR') != -1:
            return False
        # Ensure we have an OK and its the ONLY thing we have
        return response.find('\r\nOK\r\n') != -1

    def at_monitor_module_boot(self, max_await=30):
        '''
        Check to ensure we see all the required module messages before boot is really complete
        '''
        start = time()
        required_msgs = [
            '+CPIN: READY', 'Call Ready', 'SMS Ready'
        ]
        seen_msgs = []
        while len(required_msgs) != len(seen_msgs):
            if time() - start > max_await:
                # Call failure
                raise GPRSError('Module boot message not found in requisite time - aborting', '')
            res = self.do_at_command('test_at')
            logger.debug('AT Boot monitor result: %s', res)
            for msg in required_msgs:
                if res.find(msg) != -1:
                    seen_msgs.append(msg)
                    logger.debug('AT Boot monitor seen msgs: %s', seen_msgs)
            sleep(0.1)

    def gprs_enable_response_ok(self, response):
        '''
            b'AT+CGATT?\r\r\nAT+CGATT: 1\r\n\r\nOK\r\n'
        '''
        logger.debug('GPRS Response Check: %s', response)
        if response.find('ERROR') != -1:
            return False
        return int(response.split(' ')[1][0]) == 1

    def gprs_check_response_ok(self, response):
        '''
            b'AT+CGATT=1\r\n\r\nOK\r\n'
        '''
        logger.debug('GPRS Response Check: %s', response)
        if response.find('ERROR') != -1:
            return False
        return int(response.split('=')[1][0]) == 1

    def pdp_disable_response_ok(self, response):
        if response.find('ERROR') != -1:
            return False
        return response.find('SHUT OK') != -1

    def tcp_connect_response_ok(self, response):
        if response.find('ERROR') != -1:
            return False
        return response.find('CONNECT OK') != -1

    def tcp_send_response_ok(self, response):
        if response.find('ERROR') != -1:
            return False
        return response.find('SEND OK') != -1

    def sms_send_ready_response_ok(self, response):
        if response.find('ERROR') != -1:
            return False
        return response.find('>') != -1

    def do_at_command(self, command, pause_time=0.5, log_all_responses=True, max_await=10):
        '''
        ::param command STRING
        Command will be checked against list of known commands (see _at_commands)
        if not found it'll be run directly and the response given (encase it was pre-prepared)
        '''
        cmd_at = self._at_commands(command)
        if not cmd_at:
            # Assume its custoim/ pre-prepared
            cmd_at = command
        try:
            # Encode if its not bytes
            if not isinstance(cmd_at, bytes):
                cmd_at = cmd_at.encode()
        except Exception as err:
            raise GPRSATCheckError(
                'failed to encode command: {} to bytes'.format(cmd_at), '')
        command_bytes = cmd_at + self.at_terminator
        logger.debug("Running AT Command: %s", command_bytes)
        self.ser.write(command_bytes)
        self._await_serial(pause_time=pause_time)
        try:
            res = self.ser.read(self.ser.in_waiting)
            res = res.decode()
            if log_all_responses:
                logger.debug("AT Command Result: %s", res)
            return res
        except UnicodeDecodeError as err:
            logger.debug(
                "Do Cmd result decode error - will keep trying: %s", err)
            start = time()
            while True:
                if time() - start > max_await:
                    raise GPRSError('Decode error retries have failed', '')
                try:
                    self.ser.write(command_bytes)
                    self._await_serial(pause_time=pause_time)
                    res = self.ser.read(self.ser.in_waiting)
                    res = res.decode()
                    logger.debug("AT Command Result: %s", res)
                    return res
                except UnicodeDecodeError as err:
                    logger.debug(
                        "Do Cmd result decode error - retry failed - setting res to empty: %s", err)
                    sleep(pause_time)

    def gprs_ok(self):
        '''
        Check gprs service status
        '''
        res = self.do_at_command('test_grps_service_status')
        chk = self.at_response_ok(res)
        logger.debug("GPRS Check returned %s", res)
        if not chk:
            raise GPRSGPRSCheckError('GPRS Check Failed: ' + res, '')

    def connected_ok(self, enable_ip=True):
        '''
        Check we are connected to the GPRS network and have an IP
        '''
        self.at_check_ready()
        # Check GPRS Status
        self.gprs_ok()
        if enable_ip:
            # Check we have an IP
            self.get_ip()
            return True

    def _sms_time_blocked(self):
        '''
        Check if we are time-blocked by SMS throttling
        '''
        if time() > (self.last_sms_time + self.sms_throttle_time):
            # We've passed the blocking time
            return False
        else:
            return True

# CONNECTION

    def get_provider(self):
        '''
        Get the currently set Provider string
        '''
        res = self.do_at_command('get_provider')
        chk = self.at_response_ok(res)
        if not chk:
            raise GPRSGetProviderError('GPRS Check Failed: ' + res, '')
        provider = res.lstrip(
            'AT+CSTT?\r\r\n+CSTT: ').rstrip('\r\n\r\nOK\r\n').split(',')[0].replace('\"', '')
        logger.debug("Get-Provider returned %s", provider)
        return provider

    def set_provider(self, provider):
        cmd = self._at_commands('set_provider') + provider
        res = self.do_at_command(cmd)
        chk = self.at_response_ok(res)
        logger.debug("Set-Provider returned %s", res)
        if not chk:
            raise GPRSSetProviderError('Set Provider Failed: ' + res, '')

    def enable_gprs(self, gprs_enable_wait=5):
        # Check its not already enabled
        try:
            self.gprs_ok()
        except GPRSGPRSCheckError:
            # Check failed - try to init
            res = self.do_at_command(
                'enable_gprs', pause_time=gprs_enable_wait)
            chk = self.gprs_enable_response_ok(res)
            if not chk:
                raise GPRSError('GPRS Enable failed: ' + res, '')

    def disable_gprs(self):
        res = self.do_at_command('disable_gprs')
        # Should be false
        chk = self.gprs_enable_response_ok(res)
        if chk:
            raise GPRSError('GPRS Disable failed: ' + res, '')

    def disable_pdp(self):
        res = self.do_at_command('close_pdp')
        chk = self.pdp_disable_response_ok(res)
        if chk:
            raise GPRSError('Close PDP failed: ' + res, '')

    def enable_pdp(self, pdp_enable_wait=2):
        # This seems to reset the PDP connection
        res = self.do_at_command('set_cipmode', pause_time=pdp_enable_wait)
        chk = self.at_response_ok(res)
        if not chk:
            raise GPRSSetProviderError('Set CIPMODE Failed: ' + res, '')

    def enable_wireless(self, wireless_enable_wait_time=5):
        ''' Starts the Wireless GPRS Radio '''
        res = self.do_at_command(
            'enable_wireless', pause_time=wireless_enable_wait_time)
        # This doesnt respond with anything if it successed
        chk = res.find('ERROR') == -1
        if not chk:
            raise GPRSSetProviderError(
                'GPRS Enable Wireless Failed: ' + res, '')
        logger.debug("Enable wireless result %s", chk)

    def disable_wireless(self):
        ''' Kills the wireless connection '''
        pass

    def get_ip(self, max_await=10):
        ''' 
        Get GPRS IP Address
            AT+CIFSR\r\r\n100.100.100.255\r\n
        ::kwarg max_await int Max time to await for a good IP
        '''
        start = time()
        while True:
            try:
                res = self.do_at_command('get_ip')
                if res.find('ERROR') != -1:
                    raise GPRSGetIpError('Get IP Failed: ' + res, '')
                ip = res.lstrip('AT+CIFSR\r\r\n').rstrip('\r\n')
                logger.debug("Ip Returned: %s, %s", res, ip)
                ip_recheck = re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip)
                if ip_recheck:
                    self.ip = ip
                    return ip
                else:
                    logger.debug("Ip Failed regex, retrying...")
                    raise GPRSGetIpError('Get IP Failed regex: ' + ip, '')
            except GPRSGetIpError:
                if time()-start > max_await:
                    raise GPRSGetIpError('Get IP failed - timeout', '')
                else:
                    sleep(1)

    def get_signal_strength(self):
        '''
        Get the signal strength of the currently selected provider
            0=-115 dBm or less
            1=-111 dBm
            2...30=-110...-54 dBm 
            31=-52 dBm or greater
            99=not known or not detectable
        '''
        res = self.do_at_command('get_signal_quality')
        chk = self.at_response_ok(res)
        if not chk:
            raise GPRSError('GPRS Get Signal Quality Error: ' + res, '')
        signal = int(res.split('\r\n')[1].split(' ')[1].split(',')[0])
        return signal

    def connect(self):
        '''
        Connect to the GPRS network
        '''
        # Check if we are already connected with an IP
        logger.info("Connecting...")
        try:
            self.at_check_ready()
            # Enable GPRS
            self.enable_gprs()
            # Set the CIPMODE to correct for PDP
            self.enable_pdp()
            # Select the provider
            self.set_provider(self.provider)
            # Establish Wireless
            self.enable_wireless()
            # Get our IP
            ip = self.get_ip()
            logger.debug('ip detected: %s', ip)
            chk_connected = self.connected_ok()
            if chk_connected:
                logger.info("Connect successful")
            else:
                raise GPRSError('Connect Failed', '')
        except Exception as err:
            logger.error(
                "Connect failed: %s", err
            )
            raise

    # RECOVERY ETC

    def check_stuck(self):
        '''
        Check if we are in the stuck state
        '''
        res = self.do_at_command('get_ip')
        chk_ip = self.at_response_ok(res)
        chk_wireless = self.do_at_command('enable_wireless')
        if not chk_ip and not chk_wireless:
            # Stuck
            return True
        else:
            # Not Stuck
            return False

    def reset(self, enable_gprs=True):
        '''
        Fully reset everything - serial port upwards to GPRS, with module reset.
        Then boot back up and enable gprs optionally
        '''
        logger.debug('GPRS Module Resetting...')
        # Power down
        try:
            if self.ser:
                if self.ser.isOpen():
                    self.ser.close()
                self.ser = None
            self.reset_hardware()
            # Power up
            logger.debug('GPRS Reset awaiting boot...')
            # Re-init serial
            self.init_serial()
            # Monitor bootup
            self.at_monitor_module_boot()
            if enable_gprs:
                self.connect()
            logger.debug('Reset and reconnect complete')
            return
        except Exception as err:
            logger.error('reset failed: %s', err)
            raise

    def reset_gprs(self):
        '''
        Reset pdp context if we've been dropped by network
        '''
        logger.debug('GPRS PDP Resetting')
        self.disable_pdp()
        self.disable_gprs()

    def reset_hardware(self):
        '''
        Reset the module via GPIO
        '''
        # Toggle twice to reset
        logger.debug('resetting hardware via GPIO')
        # Lazy import raspi GPIO
        try:
            if os.uname()[4][:3] != 'arm':
                logger.warning('not running under arm - GPIO import/reset will likely fail')
            import RPi.GPIO as GPIO
            # PWRKEY Pin
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.gpio_reset_pin, GPIO.OUT)
            GPIO.output(self.gpio_reset_pin, 0)
            sleep(1)
            GPIO.output(self.gpio_reset_pin, 1)
            sleep(1)
            GPIO.output(self.gpio_reset_pin, 0)
            sleep(1)
            GPIO.output(self.gpio_reset_pin, 1)
        except ImportError:
            logger.warning('missing GPIO module')
        except Exception as err:
            logger.warning('failed to reset module via GPIO: %s', err)

    def reset_sms_text_input_mode(self):
        '''
        Its possible to get stuck in SMS text entry mode 
            - this clears the text input and returns us to command mode
        '''
        _ = self.do_at_command("\x1a")
