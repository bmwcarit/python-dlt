# Copyright (C) 2015. BMW Car IT GmbH. All rights reserved.
"""Handlers are classes that assist dlt_broker in receiving and
filtering DLT messages
"""
from __future__ import absolute_import
import logging
import socket
import time

from collections import defaultdict
from threading import Thread, Event, Lock
from multiprocessing import Process
from multiprocessing.queues import Empty

from dlt.dlt import DLTClient, py_dlt_client_main_loop

DLT_CLIENT_TIMEOUT = 5
logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class DLTContextHandler(Thread):
    """Communication layer between the DLTContext instances and
    DLTMessageHandler Process.

    This class handles the transfer of messages between the process
    receiving traces from the DLT Daemon and the DLTContext queues.
    """

    def __init__(self, filter_queue, message_queue):
        super(DLTContextHandler, self).__init__()
        self.stop_flag = Event()
        self.context_map = {}
        self.lock = Lock()
        self.filter_queue = filter_queue
        self.message_queue = message_queue

    def register(self, queue, filters=None):
        """Register a queue to collect messages matching specific filters

        :param Queue queue: The new queue to add
        :param tuple filters: An tuple with (apid, ctid) used to filter
                              messages that go into this queue.
        """
        if filters is None:
            filters = [(None, None)]

        queue_id = id(queue)  # - unique identifier for this queue
        with self.lock:
            self.context_map[queue_id] = (queue, filters)

        # - inform the DLTMessageHandler process about this new
        # (queue, filter) pair
        self.filter_queue.put((queue_id, filters, True))

    def unregister(self, queue):
        """Remove a queue from set of queues being handled

        :param Queue queue: The queue to remove
        """
        queue_id = id(queue)
        _, filters = self.context_map.get(queue_id, (None, None))
        if filters:
            with self.lock:
                try:
                    del(self.context_map[queue_id])
                except KeyError:
                    pass

            # - inform the DLTMessageHandler process about removal of this
            # (queue, filter) pair
            self.filter_queue.put((queue_id, filters, False))

    def run(self):
        """The thread's main loop
        """
        while not self.stop_flag.is_set():
            queue_id, message = None, None
            try:
                if self.message_queue.full():
                    logger.error("message_queue is full ! put() on this queue will block")
                queue_id, message = self.message_queue.get_nowait()
            except Empty:
                pass

            if message:
                queue, _ = self.context_map.get(queue_id, (None, None))
                if queue:
                    queue.put(message)
            else:
                time.sleep(0.01)

    def stop(self):
        """Stops thread execution"""
        self.stop_flag.set()
        self.filter_queue.close()
        if self.is_alive():
            self.join()


class DLTMessageHandler(Process):
    """Process receiving the DLT messages and handing them to DLTContextHandler

    This process instance is responsible for collecting messages from
    the DLT daemon, tagging them with the correct queue id and placing
    them on the messages queue.
    """

    def __init__(self, filter_queue, message_queue, mp_stop_event, client_cfg):
        self.filter_queue = filter_queue
        self.message_queue = message_queue
        self.mp_stop_flag = mp_stop_event
        super(DLTMessageHandler, self).__init__()

        # - dict mapping filters to queue ids
        self.context_map = defaultdict(list)

        self._ip_address = client_cfg["ip_address"]
        self._port = client_cfg["port"]
        self._filename = client_cfg.get("filename")
        self.verbose = client_cfg.get("verbose", 0)
        self.timeout = client_cfg.get("timeout", DLT_CLIENT_TIMEOUT)
        self._client = None
        self.tracefile = None

    def _client_connect(self):
        """Create a new DLTClient

        :param int timeout: Time in seconds to wait for connection.
        :returns: True if connected, False otherwise
        :rtype: bool
        """
        logger.debug("Creating DLTClient (ip_address='%s', logfile='%s')", self._ip_address, self._port, self._filename)
        self._client = DLTClient(servIP=self._ip_address, port=self._port, verbose=self.verbose)
        connected = self._client.connect(self.timeout)
        if connected:
            logger.info("DLTClient connected to %s", self._client.servIP)
        return connected

    def _process_filter_queue(self):
        """Check if filters have been added or need to be removed"""
        while not self.filter_queue.empty():
            queue_id, filters, add = self.filter_queue.get_nowait()
            if add:
                for apid_ctid in filters:
                    self.context_map[apid_ctid].append(queue_id)
            else:
                try:
                    for apid_ctid in filters:
                        self.context_map[apid_ctid].remove(queue_id)
                        if not self.context_map[apid_ctid]:
                            del(self.context_map[apid_ctid])
                except (KeyError, ValueError):
                    # - queue_id already removed or not inserted
                    pass

    def handle(self, message):
        """Function to be called for every message received

        :param DLTMessage message: received new DLTMessage instance
        :returns: True if the loop should continue, False to stop the loop and exit
        :rtype: bool
        """
        self._process_filter_queue()

        if message is not None and not (message.apid == "" and message.ctid == ""):
            for filters, queue_ids in self.context_map.items():
                if filters in [(message.apid, message.ctid), (None, None), (message.apid, None), (None, message.ctid)]:
                    for queue_id in queue_ids:
                        if self.message_queue.full():
                            logger.error("message_queue is full ! put() on this queue will block")
                        self.message_queue.put((queue_id, message))
        return not self.mp_stop_flag.is_set()

    def run(self):
        """DLTMessageHandler worker method"""
        if self._filename is not None:
            logger.info("Opening the DLT trace file '%s'", self._filename)
            self.tracefile = open(self._filename, mode="ab", buffering=False)

        while not self.mp_stop_flag.is_set():
            exception_occured = False
            if not self._client_connect():
                # keep trying to reconnect, until we either successfully
                # connect or the stop_flag is set
                continue
            try:
                res = py_dlt_client_main_loop(self._client, verbose=0, callback=self.handle, dumpfile=self.tracefile)
                if res is False and not self.mp_stop_flag.is_set():  # main loop returned False
                    logger.error("DLT connection lost. Restarting DLT client")
                    exception_occured = True
            except KeyboardInterrupt:
                exception_occured = True
                logger.debug("main loop manually interrupted")
                break
            except socket.timeout as exc:
                exception_occured = True
                logger.error("socket timeout error")
                logger.debug(exc)
            except Exception:  # pylint: disable=broad-except
                exception_occured = True
                logger.exception("Exception during the DLT message receive")

            finally:
                if exception_occured:
                    logger.debug("Closing open socket connections.")
                    self._client.disconnect()

        self.message_queue.close()
        logger.info("DLTMessageHandler worker execution complete")
