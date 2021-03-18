"""
SIM800C Customisable Options

Order of read preference:
- Environment Variable
- This Configuration File

"""

from os import getenv

ENV_BASE = 'SIM800_'

SERIAL_PORT = getenv(ENV_BASE + 'SERIAL_PORT', '/dev/ttyACM0')
BAUD_RATE = getenv(ENV_BASE + 'SERIAL_PORT', 115200)
SERIAL_READ_TIMEOUT = getenv(ENV_BASE + 'SERIAL_PORT', 10) # s
PROVIDER = getenv(ENV_BASE + 'SERIAL_PORT', 'EE')
BOOT_WAIT_TIME = getenv(ENV_BASE + 'SERIAL_PORT', 180) # s
HTTP_REQUEST_TIMEOUT = getenv(ENV_BASE + 'SERIAL_PORT',  60) # s
HTTP_POST_UPLOAD_TIMEOUT = getenv(ENV_BASE + 'SERIAL_PORT', 10000) # ms
SERIAL_COMMAND_PAUSE = getenv(ENV_BASE + 'SERIAL_COMMAND_PAUSE', 0.5) # s
RESET_GPIO_PIN = getenv(ENV_BASE + 'RESET_GPIO_PIN', 4) # GPIO Pin
LOG_LEVEL = getenv(ENV_BASE + 'LOG_LEVEL', 'INFO')