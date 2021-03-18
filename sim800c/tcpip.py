"""
SIM800 TCI/IP Handling

Including TCP and HTTP Methods
"""

import logging
from time import time

from .exceptions import (
    GPRSHTTPError,
    GPRSTCPError
)

from .config import (
    HTTP_REQUEST_TIMEOUT,
    HTTP_POST_UPLOAD_TIMEOUT
)

logger = logging.getLogger(__name__)

class TCPIP(object):

    def __init__(
            self, 
            controller, 
            http_request_timeout = HTTP_REQUEST_TIMEOUT, 
            http_post_upload_timeout = HTTP_POST_UPLOAD_TIMEOUT
        ):
        self.controller = controller
        self.http_request_timeout = http_request_timeout
        self.http_post_upload_timeout = http_post_upload_timeout

    def connect_tcp(self, server_ip_address, server_port, tcp_connect_pause=2):
        '''
        Establish a TCP Connection
        '''
        # Connect TCP
        cmd = self.controller._at_commands('connect_tcp_client')
        cmd = cmd + '\"{}\",{}'.format(
            server_ip_address, server_port
        )
        res = self.controller.do_at_command(cmd, pause_time=tcp_connect_pause)
        chk = self.controller.tcp_connect_response_ok(res)
        if not chk:
            # Some issue - abort
            raise GPRSTCPError(
                'I have an IP but I failed to connect to the target server: {}'.format(res), '')

    def disconnect_tcp(self):
        '''
        Cleanly close TCP
        '''
        res = self.controller.do_at_command('close_tcp')
        logger.debug('Closed TCP: %s', res)
        res = self.controller.do_at_command('close_pdp')
        logger.debug('Closed PDP: %s', res)

    def send_tcp_message(self, server_ip_address, server_port, message):
        '''
            Establish a TCP client connection and send some data via GPRS
            b'AT+CIPSTART="TCP","178.62.95.128",4444\r\r\nOK\r\n\r\nCONNECT OK\r\n'
            b'AT+CIPSEND=5\r\r\n> 
            hello\r\n\r\nSEND OK\r\n
            AT+CIPSEND=5\r\r\n> 
            hello\r\n
            \r\nSEND OK\r\n
            AT+CIPCLOSE\r\r\n
            CLOSE OK\r\n'
        '''
        self.controller.connected_ok()
        # We have an IP Address - connect to server
        self.connect_tcp(server_ip_address, server_port)
        # Set the message length
        cmd = self.controller._at_commands('tcp_send_string')
        cmd = cmd + '{}'.format(len(message))
        # Dont care about the response here...
        _ = self.controller.do_at_command(cmd)
        # Send the message
        _ = self.controller.do_at_command(message)
        self.disconnect_tcp()

    def _await_get_session_complete(self):
        '''
        Await current status of http is in progres or complete
        +GET,1,11341,1314 - Session running
        +HTTPACTION: 0, 200,9335 - Get success
        +HTTPSTATUS: GET,0,0,0 - Get session over

        sometime wpayloads we seem to miss the start - it gets caught on timeout
        '''
        finished = False
        finished_counts = 0
        counts_before_finished = 50
        start = time()
        while True:
            res = self.controller.do_at_command('http_session_status')
            chk = res.find('+HTTPSTATUS: GET,0,0,0')
            if chk != -1:
                finished_counts += 1
                if finished_counts >= counts_before_finished:
                    finished = True
            if finished:
                break
            logger.debug('timeout: %s, %s', time() -
                         start, self.http_request_timeout)
            if time() - start >= self.http_request_timeout:
                logger.error('http await timeout')
                break

    def http_deinit(self):
        '''
        Cleanup an http conn
        '''
        try:
            _ = self.controller.do_at_command('http_terminate_session')
            _ = self.controller.do_at_command('http_close_gprs_context')
        except:
            raise GPRSHTTPError('http deinit exception', '')

    def http_init(self, url):
        '''
        Setup hardware ready for http comms
        '''
        try:
            # We have an IP Address
            logger.debug('Attempting to init gprs for http...')
            res = self.controller.do_at_command('http_configure_conn_bearer')
            logger.debug('http conn bearer: %s', res)
            res = self.controller.do_at_command('http_configure_conn_bearer_apn')
            logger.debug('http conn bearer apn: %s', res)
            res = self.controller.do_at_command('http_open_gprs_context')
            logger.debug('http gprs context open: %s', res)
            res = self.controller.do_at_command('http_query_gprs_context')
            logger.debug('http gprs context check: %s', res)
            res = self.controller.do_at_command('http_init')
            logger.debug('http init result: %s', res)
            # Set params for http session
            _ = self.controller.do_at_command('https_disable')
            _ = self.controller.do_at_command('http_redir_disable')
            res = self.controller.do_at_command('http_set_param_cid')
            logger.debug('http Set CID Resp: %s', res)
            chk_cid = self.controller.at_response_ok(res)
            if not chk_cid:
                raise GPRSHTTPError('http init failed setting CID', '')
            cmd = self.controller._at_commands(
                'http_set_param_url') + '\"{}\"'.format(url)
            res = self.controller.do_at_command(cmd)
            logger.debug('http Set URL Resp: %s', res)
            chk_url = self.controller.at_response_ok(res)
            if not chk_url:
                raise GPRSHTTPError('http init failed setting URL', '')
            return True
        except Exception as e:
            raise e

    def https_init(self, url):
        '''
        Setup hardware ready for https comms
        '''
        try:
            # We have an IP Address
            logger.debug('Attempting to init gprs for http...')
            res = self.controller.do_at_command('http_configure_conn_bearer')
            logger.debug('http conn bearer: %s', res)
            res = self.controller.do_at_command('http_configure_conn_bearer_apn')
            logger.debug('http conn bearer apn: %s', res)
            res = self.controller.do_at_command('http_open_gprs_context')
            logger.debug('http gprs context open: %s', res)
            res = self.controller.do_at_command('http_query_gprs_context')
            logger.debug('http gprs context check: %s', res)
            res = self.controller.do_at_command('http_init')
            logger.debug('http init result: %s', res)
            # Set params for http session
            res = self.controller.do_at_command('http_set_param_cid')
            logger.debug('http Set CID Resp: %s', res)
            chk_cid = self.controller.at_response_ok(res)
            if not chk_cid:
                raise GPRSHTTPError('https init failed setting CID', '')
            cmd = self.controller._at_commands(
                'http_set_param_url') + '\"{}\"'.format(url)
            res = self.controller.do_at_command(cmd)
            chk_url = self.controller.at_response_ok(res)
            if not chk_url:
                raise GPRSHTTPError('https init failed setting URL', '')
            # cmd = self._at_commands('http_redir_enable')
            # _ = self.do_at_command(cmd)
            res = self.controller.do_at_command('https_enable')
            chk_https = self.controller.at_response_ok(res)
            if not chk_https:
                raise GPRSHTTPError('https enable failed', '')
            return True
        except Exception as e:
            raise e

    def parse_http_response(self, res):
        '''
        Retrieve the data associated with http get request
        '''
        logger.debug('http get raw response: %s', res)
        try:
            message = res.split('+HTTPREAD: ')[1].split('\r\n')[1]
            logger.debug('http get processed response: %s', message)
        except Exception as err:
            logger.debug(
                'failed to parse http response content: %s, %s', res, err)
            message = ''
        return message

    def http_get(self, url):
        '''
        http GET request
        '''
        try:
            chk_init = self.http_init(url)
            if chk_init:
                res = self.controller.do_at_command('http_get_session_start')
                chk_sess = self.controller.at_response_ok(res)
                self._await_get_session_complete()
                res = self.controller.do_at_command('http_get_data')
                chk_get_data = self.controller.at_response_ok(res)
                if chk_sess and chk_get_data:
                    logger.debug('HTTP Get Response: %s', res)
                    parsed_response = self.parse_http_response(res)
                    return parsed_response
            else:
                raise GPRSHTTPError('http get failed init', '')
        except Exception as e:
            raise e
        finally:
            # Cleanup attempt
            self.http_deinit()

    def http_post(self, url, data):
        '''
        http POST request
        '''
        try:
            chk_init = self.http_init(url)
            if chk_init:
                res = self.controller.do_at_command('http_session_status')
                size = len(data)
                cmd = self.controller._at_commands('http_post_data')
                cmd = cmd + '{},{}'.format(size, self.http_post_upload_timeout)
                res = self.controller.do_at_command(cmd)
                # res = self.do_at_command('http_session_status')
                # Send the actual data
                res = self.controller.do_at_command(data, pause_time=10)
                chk_data = self.controller.at_response_ok(res)
                # This is apparently essential to flush the data
                # Set the transmission going
                res = self.controller.do_at_command(
                    'http_post_session_start', pause_time=10)
                chk_post = self.controller.at_response_ok(res)
                return chk_data and chk_post
            else:
                raise GPRSHTTPError('http post failed init', '')
        except Exception as e:
            raise e
        finally:
            # Cleanup attempt
            self.http_deinit()

    def https_get(self, url):
        '''
        https GET request
        '''
        try:
            chk_init = self.https_init(url)
            if chk_init:
                res = self.controller.do_at_command('http_get_session_start')
                chk_sess = self.controller.at_response_ok(res)
                self._await_get_session_complete()
                res_data = self.controller.do_at_command('http_get_data')
                flushed = False
                # Here we have to keep firing a basic AT command to flush the buffer properly
                while not flushed:
                    res_flush = self.controller.do_at_command('test_at')
                    res_data += res_flush
                    flushed = self.controller.at_response_ok(res_flush)
                if chk_sess and flushed:
                    logger.debug('HTTPS Get Response: %s', res_data)
                    parsed_response = self.parse_http_response(res_data)
                    return parsed_response
            else:
                raise GPRSHTTPError('https get failed init', '')
        except Exception as e:
            raise e
        finally:
            # Cleanup attempt
            self.http_deinit()

    def https_post(self, url, data):
        '''
        https POST request
        WARNING - THIS IS NOT SUPPORTED ON THE SIM 800 Module for the time being
        '''
        raise GPRSHTTPError('https post is unsupported', '')
