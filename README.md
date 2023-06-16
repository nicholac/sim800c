# Python Controller for SIMCOM 800C GPRS/GSM

Simple python interface to the Waveshare Sim800C GSM/GPRS Module.

Provides interfaces to SMS, TCP and HTTP methods.  Principally just a wrapper around the various AT commands.

## Requirements:

* Hardware reset requires RPi.GPIO
* Can be used from non-Raspi hosts with serial connection

## Configuration:

The following environment variables can be used to override default initialisation variables:

* SIM800_SERIAL_PORT
* SIM800_BAUD_RATE
* SIM800_SERIAL_READ_TIMEOUT
* SIM800_PROVIDER
* SIM800_BOOT_WAIT_TIME
* SIM800_HTTP_REQUEST_TIMEOUT
* SIM800_HTTP_POST_UPLOAD_TIMEOUT
* SIM800_SERIAL_COMMAND_PAUSE
* SIM800_RESET_GPIO_PIN
* SIM800_LOG_LEVEL

## Usage:

### Import / Init


```python
python3
>>> from sim800c import Sim800C
# Config params are optional and can be provided by default using the envionment variable - as above
>>> gprs = Sim800C(
    serial_port=SERIAL_PORT,
    baudrate=BAUD_RATE,
    serial_read_timeout=SERIAL_READ_TIMEOUT,
    provider=PROVIDER,
    bootup=True,
    cmd_pause=SERIAL_COMMAND_PAUSE,
    gpio_reset_pin=RESET_GPIO_PIN
)
```

### HTTP

```python
# HTTP GET
>>> response_data = gprs.http_get('http://some.endpoint.com')
# HTTPS GET
>>> response_data = gprs.https_get('https://some.endpoint.com')
# HTTP POST
>>> response_data = gprs.http_post('http://some.post.endpoint', data_to_be_sent)
```

### TCP

```python
# TCP Send Message
>>> response_data = gprs.send_tcp_message(server_ip_address, server_port, message)
```

### SMS

```python
# SMS Send Message
>>> response_data = gprs.read_sms_message(message_number=1)
# Empty Inbox
>>> gprs.delete_all_sms_messages()
```
