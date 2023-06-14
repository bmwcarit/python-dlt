# Copyright (C) 2015. BMW Car IT GmbH. All rights reserved.
"""DLT Broker is running in a loop in a separate thread until stop_flag is set and adding received messages
to all registered queues
"""
from contextlib import contextmanager
import ipaddress as ip
import logging
from multiprocessing import Event, Queue
import queue as tqueue

from dlt.dlt_broker_handlers import (
    DLT_DAEMON_TCP_PORT,
    DLTContextHandler,
    DLTFilterAckMessageHandler,
    DLTMessageDispatcherBase,
    DLTMessageHandler,
    DLTFileSpinner,
    DLTTimeValue,
)

DLT_CLIENT_TIMEOUT = 5

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


@contextmanager
def create_filter_ack_queue(filter_ack_msg_handler):
    """Register and unregister a queue into DLTFilterAckMessageHandler"""
    queue = tqueue.Queue()

    try:
        filter_ack_msg_handler.register(queue)

        yield queue

    finally:
        filter_ack_msg_handler.unregister(queue)


class DLTBroker(object):
    """DLT Broker class manages receiving and filtering of DLT Messages"""

    def __init__(
        self,
        ip_address=None,
        port=DLT_DAEMON_TCP_PORT,
        use_proxy=False,
        enable_dlt_time=False,
        enable_filter_set_ack=False,
        filter_set_ack_timeout=2.0,
        ignore_filter_set_ack_timeout=False,
        **kwargs,
    ):
        """Initialize the DLT Broker

        :param str | None ip_address: IP address of the DLT Daemon.
                If None, then dlt does not come with any ip listening, in other words, it comes from dlt log directly;
                Else, dlt comes from listening to some ip address. Defaults to TCP connection,
                unless a multicast address is used. In that case an UDP multicast connection will be used
        :param str post: Port of the DLT Daemon
        :param bool use_proxy: Ignored - compatibility option
        :param bool enable_dlt_time: Record the latest dlt message timestamp if enabled.
        :param bool enable_filter_set_ack: Wait an ack message when sending a filter-setting message
        :param float filter_set_ack_timeout: Waiting time for the ack message
        :param bool ignore_filter_set_ack_timeout: Ignore the timeout when the value is True
        :param **kwargs: All other args passed to DLTMessageHandler
        """
        # - dlt-time share memory init
        self._dlt_time_value = DLTTimeValue() if enable_dlt_time else None

        # - handlers init
        self.mp_stop_flag = Event()
        self.filter_queue = Queue()
        self.message_queue = Queue()

        # - filter ack queue setting
        self.enable_filter_set_ack = enable_filter_set_ack
        self.ignore_filter_set_ack_timeout = ignore_filter_set_ack_timeout
        self.filter_set_ack_timeout = filter_set_ack_timeout
        if enable_filter_set_ack:
            # Optional[multiprocessing.Queue[Tuple[int, bool]]]
            # int presents queue id, bool presents enable or not
            self.filter_ack_queue = Queue()
            self.filter_ack_msg_handler = DLTFilterAckMessageHandler(self.filter_ack_queue)
        else:
            self.filter_ack_queue = None
            self.filter_ack_msg_handler = None

        self.msg_handler = self.create_dlt_message_dispather(ip_address, port, kwargs)

        self.context_handler = DLTContextHandler(self.filter_queue, self.message_queue)

        self._ip_address = ip_address
        self._port = port
        self._filename = kwargs.get("filename")

    def create_dlt_message_dispather(self, ip_address, port, client_cfg) -> DLTMessageDispatcherBase:
        if ip_address:
            # If ip_address is given, then messages are retrieved from dlt client at run-time
            return self._create_dlt_message_handler(ip_address, port, client_cfg)
        else:
            # If not ip_address is given, then messages are retrieved from the given filename
            # The logs are written to the given filename from another process
            return self._create_dlt_file_spinner(client_cfg.get("filename"))

    def _create_dlt_message_handler(self, ip_address, port, client_cfg):
        client_cfg["ip_address"] = ip_address
        client_cfg["port"] = port
        client_cfg["timeout"] = client_cfg.get("timeout", DLT_CLIENT_TIMEOUT)
        return DLTMessageHandler(
            self.filter_queue,
            self.message_queue,
            self.mp_stop_flag,
            client_cfg,
            dlt_time_value=self._dlt_time_value,
            filter_ack_queue=self.filter_ack_queue,
        )

    def _create_dlt_file_spinner(self, file_name):
        return DLTFileSpinner(
            self.filter_queue,
            self.message_queue,
            self.mp_stop_flag,
            file_name,
            dlt_time_value=self._dlt_time_value,
            filter_ack_queue=self.filter_ack_queue,
        )

    def start(self):
        """DLTBroker main worker method"""
        if isinstance(self.msg_handler, DLTMessageHandler):
            logger.debug(
                "Starting DLTBroker with parameters: use_proxy=%s, ip_address=%s, port=%s, filename=%s, multicast=%s",
                False,
                self._ip_address,
                self._port,
                self._filename,
                ip.ip_address(self._ip_address).is_multicast,
            )
        else:
            logger.debug("Starting DLTBroker by reading %s", self._filename)

        if self._dlt_time_value:
            logger.debug("Enable dlt time for DLTBroker.")

        self.msg_handler.start()
        self.context_handler.start()
        if self.enable_filter_set_ack:
            self.filter_ack_msg_handler.start()

        # - ensure we don't block on join_thread() in stop()
        # https://docs.python.org/2.7/library/multiprocessing.html#multiprocessing.Queue.cancel_join_thread
        self.filter_queue.cancel_join_thread()
        self.message_queue.cancel_join_thread()
        if self.enable_filter_set_ack:
            self.filter_ack_queue.cancel_join_thread()

    def _recv_filter_set_ack(self, context_filter_ack_queue, required_response):
        try:
            resp = context_filter_ack_queue.get(timeout=self.filter_set_ack_timeout)
            if resp != required_response:
                logger.debug("Filter-setting ack response not matched: %s, expected: %s", resp, required_response)
                return False

            return True
        except tqueue.Empty as err:
            if self.ignore_filter_set_ack_timeout:
                logger.info(
                    "Timeout for getting filter-setting ack: %s, %s", id(context_filter_ack_queue), required_response
                )
                return None

            raise err

        return False

    def add_context(self, context_queue, filters=None):
        """Register context

        :param Queue context_queue: The queue to which new messages will
                                    be added
        :param tuple filters: An list of tuples (eg: [(apid, ctid)])
                              used to filter messages that go into this
                              queue.
        """
        filters = filters or [(None, None)]

        if not isinstance(filters, (tuple, list)):
            raise RuntimeError("Context queue filters must be a tuple. Ex. (('SYS', 'JOUR'), ('AUDI', 'CAPI'))")

        if self.enable_filter_set_ack:
            logger.debug("Send a filter-setting message with requesting ack")
            with create_filter_ack_queue(self.filter_ack_msg_handler) as context_filter_ack_queue:
                self.context_handler.register(
                    context_queue, filters, context_filter_ack_queue=context_filter_ack_queue
                )

                if not self._recv_filter_set_ack(context_filter_ack_queue, True):
                    failure_reason = ""
                    if isinstance(self.msg_handler, DLTMessageHandler):
                        failure_reason = (
                            "It's possible that DLTClient client does not start."
                            " If it's a test case, it might be an error"
                        )
                    elif isinstance(self.msg_handler, DLTFileSpinner):
                        failure_reason = (
                            f"It's possible that dlt file {self._filename} is empty now. No big issue, "
                            f"filters would be added once after new message is available in dlt file"
                        )
                    logger.warning(
                        (
                            "Could not receive filter-setting message ack. %s. For now, Run it anyway. "
                            "filters: %s, queue_id: %s"
                        ),
                        failure_reason,
                        filters,
                        id(context_queue),
                    )
        else:
            self.context_handler.register(context_queue, filters)

    def remove_context(self, context_queue):
        """Unregister context

        :param Queue context_queue: The queue to unregister.
        """
        self.context_handler.unregister(context_queue)

    def stop(self):
        """Stop the broker"""
        logger.info("Stopping DLTContextHandler and %s", type(self.msg_handler).__name__)

        self.msg_handler.break_blocking_main_loop()

        logger.debug("Stop %s", type(self.msg_handler).__name__)
        self.mp_stop_flag.set()

        logger.debug("Stop DLTContextHandler")
        self.context_handler.stop()

        logger.debug("Waiting on DLTContextHandler ending")
        self.context_handler.join()

        if self.enable_filter_set_ack:
            logger.debug("Stop DLTFilterAckMessageHandler")
            self.filter_ack_msg_handler.stop()

            logger.debug("Waiting on DLTFilterAckMessageHandler ending")
            self.filter_ack_msg_handler.join()

        logger.debug("Waiting on %s ending", type(self.msg_handler).__name__)
        if self.msg_handler.is_alive():
            try:
                self.msg_handler.terminate()
            except OSError:
                pass
            else:
                self.msg_handler.join()

        logger.debug("DLTBroker execution done")

    # pylint: disable=invalid-name
    def isAlive(self):
        """Backwards compatibility method

        Called from mtee.testing.connectors.tools.broker_assert. Will
        need to be replaced in MTEE eventually.
        """
        return any((self.msg_handler.is_alive(), self.context_handler.is_alive()))

    def dlt_time(self):
        """Get time for the last dlt message

        The value is seconds from 1970/1/1 0:00:00

        :rtype: float
        """
        if self._dlt_time_value:
            return self._dlt_time_value.timestamp

        raise RuntimeError("Getting dlt time function is not enabled")
