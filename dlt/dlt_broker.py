# Copyright (C) 2015. BMW Car IT GmbH. All rights reserved.
"""DLT Broker is running in a loop in a separate thread until stop_flag is set and adding received messages
to all registered queues"""
from __future__ import print_function, absolute_import

import logging

from multiprocessing import Event, Queue

from dlt.dlt_broker_handlers import DLT_DAEMON_TCP_PORT, DLTContextHandler, DLTMessageHandler

DLT_CLIENT_TIMEOUT = 5

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class DLTBroker(object):
    """DLT Broker class manages receiving and filtering of DLT Messages
    """

    def __init__(self, ip_address, port=DLT_DAEMON_TCP_PORT, use_proxy=False, **kwargs):
        """Initialize the DLT Broker

        :param str ip_address: IP address of the DLT Daemon
        :param str post: Port of the DLT Daemon
        :param bool use_proxy: Ignored - compatibility option
        :param **kwargs: All other args passed to DLTMessageHandler
        """
        # - handlers init
        self.mp_stop_flag = Event()

        self.filter_queue = Queue()
        self.message_queue = Queue()
        kwargs["ip_address"] = ip_address
        kwargs["port"] = port
        kwargs["timeout"] = kwargs.get("timeout", DLT_CLIENT_TIMEOUT)
        self.msg_handler = DLTMessageHandler(self.filter_queue, self.message_queue, self.mp_stop_flag, kwargs)
        self.context_handler = DLTContextHandler(self.filter_queue, self.message_queue)

        self._ip_address = ip_address
        self._port = port
        self._filename = kwargs.get("filename")

    def start(self):
        """DLTBroker main worker method"""
        logger.debug("Starting DLTBroker with parameters: use_proxy=%s, ip_address=%s, port=%s, filename=%s",
                     False, self._ip_address, self._port, self._filename)

        self.msg_handler.start()
        self.context_handler.start()

        # - ensure we don't block on join_thread() in stop()
        # https://docs.python.org/2.7/library/multiprocessing.html#multiprocessing.Queue.cancel_join_thread
        self.filter_queue.cancel_join_thread()
        self.message_queue.cancel_join_thread()

    def add_context(self, context_queue, filters=None):
        """Register context

        :param Queue context_queue: The queue to which new messages will
                                    be added
        :param tuple filters: An list of tuples (eg: [(apid, ctid)])
                              used to filter messages that go into this
                              queue.
        """
        if filters is None:
            filters = [(None, None)]

        if not isinstance(filters, (tuple, list)):
            raise RuntimeError("Context queue filters must be a tuple."
                               " Ex. (('SYS', 'JOUR'), ('AUDI', 'CAPI'))")

        self.context_handler.register(context_queue, filters)

    def remove_context(self, context_queue):
        """Unregister context

        :param Queue context_queue: The queue to unregister.
        """
        self.context_handler.unregister(context_queue)

    def stop(self):
        """Stop the broker"""
        logger.info("Stopping DLTContextHandler and DLTMessageHandler")

        # - stop the DLTMessageHandler process and DLTContextHandler thread
        self.mp_stop_flag.set()
        self.context_handler.stop()

        logger.debug("Waiting on DLTContextHandler and DLTMessageHandler")
        self.context_handler.join()
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
