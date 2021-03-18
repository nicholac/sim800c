"""
SIM800 SMS Handling

SMS Send, Receive, Inbox Management
"""

import logging
from time import time

from .exceptions import (
    GPRSSMSError
)

logger = logging.getLogger(__name__)

class SMS(object):

    def __init__(self, controller):
        self.controller = controller

    def send_sms_message(self, number, message, send_sms_pause=3):
        '''
        Send an SMS
        '''
        logger.debug('send SMS - check time blocked')
        if self.controller._sms_time_blocked():
            raise GPRSSMSError('SMS throttling time blocked for another {} secs'.format(
                time() - (self.controller.last_sms_time + self.controller.sms_throttle_time)
            ), ''
            )
        res = self.controller.do_at_command('set_sms_mode')
        logger.debug('send SMS - set sms mode result: %s', res)
        chk = self.controller.at_response_ok(res)
        if not chk:
            raise GPRSSMSError('set SMS mode failed: ' + res, '')
        cmd = self.controller._at_commands('set_sms_phone_number') + \
            '\"{}\"'.format(number)
        res = self.controller.do_at_command(cmd)
        logger.debug('send SMS - set sms number result: %s', res)
        chk = self.controller.sms_send_ready_response_ok(res)
        if not chk:
            raise GPRSSMSError('set SMS number failed: ' + res, '')
        # Send the text and terminator
        _ = self.controller.do_at_command(message + "\x1a", pause_time=send_sms_pause)
        self.last_sms_time = time()

    def read_sms_message(self, message_number=1):
        '''
        Read SMS, return the message text - 
            dont attempt to parse anything other than the message text at this stage
        ::param message_number int default -1 == read most recent message (if it exists)
            b'\r\n+CMTI: "SM",1\r\nAT+CMGR=1\r\r\n+CMGR: "REC UNREAD","+447941074267","","20/10/09,14:52:02+04"\r\nTest\r\n\r\nOK\r\n'
        '''
        res = self.controller.do_at_command('set_sms_mode')
        logger.debug('SMS - read sms set mode result: %s', res)
        chk = self.controller.at_response_ok(res)
        if not chk:
            raise GPRSSMSError('set SMS mode failed: ' + res, '')
        # Get the message with given ID
        cmd = self.controller._at_commands('read_sms') + str(message_number)
        res = self.controller.do_at_command(cmd)
        logger.debug('SMS - read SMS result: %s', res)
        chk = self.controller.at_response_ok(res)
        if not chk:
            raise GPRSSMSError('read SMS failed: ' + res, '')
        # Parse out the text
        message = res.split('+CMGR: ')[1].split('\r\n')[1]
        logger.debug('SMS - read SMS result: %s', message)
        return message

    def delete_all_sms_messages(self):
        '''
        Delete all stored SMS messages
        '''
        res = self.controller.do_at_command('set_sms_mode')
        chk = self.controller.at_response_ok(res)
        if not chk:
            raise GPRSSMSError('set SMS mode failed: ' + res, '')
        res = self.controller.do_at_command('delete_all_sms')
        chk = self.controller.at_response_ok(res)
        if not chk:
            raise GPRSSMSError('delete all SMS failed: ' + res, '')