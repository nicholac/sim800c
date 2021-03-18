"""
Python Controller for Sim800C PiHat
"""

import serial
from time import sleep, time
import json
import logging
import sys
import re
import os

from .config import (
    SERIAL_PORT,
    BAUD_RATE,
    SERIAL_READ_TIMEOUT,
    PROVIDER,
    BOOT_WAIT_TIME,
    HTTP_REQUEST_TIMEOUT,
    HTTP_POST_UPLOAD_TIMEOUT,
    RESET_GPIO_PIN,
    LOG_LEVEL
)

from .sim800c import Sim800C
from .sms import SMS
from .tcpip import TCPIP
# Set default logging handler to avoid "No handler found" warnings.
import logging
from logging import NullHandler

logger = logging.getLogger(__name__)
log_lvl = logging.getLevelName(LOG_LEVEL)
logger.setLevel(log_lvl)

# NEXT: format everything
# NEXT: Documentation

def detect_env():
    chipset = os.uname()[4][:3]
    logger.info('%s environment detected', chipset)
    if chipset == 'arm':
        try:
            import RPi.GPIO as GPIO
            # PWRKEY Pin
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(RESET_GPIO_PIN, GPIO.OUT)
            logger.info('RPi.GPIO is available')
        except:
            logger.warning('RPi.GPIO library missing - automated hardware reset will not function')
    else:
        logger.warning('RPi.GPIO is not available in this environment - automated hardware reset will not function')


# Detect environment and provide feedback
detect_env() 


