# Copyright (C) 2023. BMW Car IT GmbH. All rights reserved.
import logging
from multiprocessing import Event, Queue
import os
import time
import tempfile
import unittest
from queue import Empty

from dlt.dlt_broker_handlers import DLTFileSpinner
from tests.utils import (
    create_messages,
    stream_multiple,
    stream_with_params,
    append_stream_to_file,
    append_message_to_file,
)

logger = logging.getLogger(__name__)


class TestDLTFileSpinner(unittest.TestCase):
    def setUp(self):
        self.filter_queue = Queue()
        self.message_queue = Queue()
        self.stop_event = Event()
        # Dlt file is created with empty content
        _, self.dlt_file_name = tempfile.mkstemp(suffix=b".dlt")
        self.dlt_file_spinner = DLTFileSpinner(
            self.filter_queue, self.message_queue, self.stop_event, self.dlt_file_name
        )
        # dispatched_messages from DLTFileSpinner.message_queue
        self.dispatched_messages = []

    def tearDown(self):
        if self.dlt_file_spinner.is_alive():
            self.dlt_file_spinner.break_blocking_main_loop()
            self.stop_event.set()
            self.dlt_file_spinner.join()
        if os.path.exists(self.dlt_file_name):
            os.remove(self.dlt_file_name)

    def test_init(self):
        self.assertFalse(self.dlt_file_spinner.mp_stop_flag.is_set())
        self.assertFalse(self.dlt_file_spinner.is_alive())
        self.assertTrue(self.dlt_file_spinner.filter_queue.empty())
        self.assertTrue(self.dlt_file_spinner.message_queue.empty())

    def test_run_basic_without_dlt_file(self):
        # Delete the created dlt file
        os.remove(self.dlt_file_name)

        self.assertFalse(self.dlt_file_spinner.is_alive())
        self.dlt_file_spinner.start()
        self.assertTrue(self.dlt_file_spinner.is_alive())
        self.assertNotEqual(self.dlt_file_spinner.pid, os.getpid())
        # DLT file does NOT exist
        self.assertFalse(os.path.exists(self.dlt_file_spinner.file_name))

        self.dlt_file_spinner.break_blocking_main_loop()
        self.stop_event.set()
        self.dlt_file_spinner.join()
        self.assertFalse(self.dlt_file_spinner.is_alive())

    def test_run_basic_with_empty_dlt_file(self):
        self.assertFalse(self.dlt_file_spinner.is_alive())
        self.dlt_file_spinner.start()
        self.assertTrue(self.dlt_file_spinner.is_alive())
        self.assertNotEqual(self.dlt_file_spinner.pid, os.getpid())
        # dlt_reader is instantiated and keeps alive
        self.assertTrue(os.path.exists(self.dlt_file_spinner.file_name))
        # Expect no dlt log is dispatched
        time.sleep(2)
        self.assertTrue(self.dlt_file_spinner.message_queue.empty())
        # First stop dlt reader, then stop DLTFileSpinner
        self.dlt_file_spinner.break_blocking_main_loop()
        self.stop_event.set()
        self.dlt_file_spinner.join()
        self.assertFalse(self.dlt_file_spinner.is_alive())

    def test_handle_add_new_filter(self):
        self.dlt_file_spinner.filter_queue.put(("queue_id", [("SYS", "JOUR")], True))
        time.sleep(0.01)
        self.dlt_file_spinner.handle(None)
        self.assertIn(("SYS", "JOUR"), self.dlt_file_spinner.context_map)
        self.assertEqual(self.dlt_file_spinner.context_map[("SYS", "JOUR")], ["queue_id"])

    def test_handle_remove_filter_single_entry(self):
        self.dlt_file_spinner.filter_queue.put(("queue_id", [("SYS", "JOUR")], True))
        time.sleep(0.01)
        self.dlt_file_spinner.handle(None)
        self.assertIn(("SYS", "JOUR"), self.dlt_file_spinner.context_map)
        self.assertEqual(self.dlt_file_spinner.context_map[("SYS", "JOUR")], ["queue_id"])

        self.dlt_file_spinner.filter_queue.put(("queue_id", [("SYS", "JOUR")], False))
        time.sleep(0.01)
        self.dlt_file_spinner.handle(None)
        self.assertNotIn(("SYS", "JOUR"), self.dlt_file_spinner.context_map)

    def test_handle_remove_filter_multiple_entries(self):
        self.dlt_file_spinner.filter_queue.put(("queue_id1", [("SYS", "JOUR")], True))
        self.dlt_file_spinner.filter_queue.put(("queue_id2", [("SYS", "JOUR")], True))
        time.sleep(0.01)
        self.dlt_file_spinner.handle(None)
        self.assertIn(("SYS", "JOUR"), self.dlt_file_spinner.context_map)
        self.assertEqual(self.dlt_file_spinner.context_map[("SYS", "JOUR")], ["queue_id1", "queue_id2"])

        self.dlt_file_spinner.filter_queue.put(("queue_id1", [("SYS", "JOUR")], False))
        time.sleep(0.01)
        self.dlt_file_spinner.handle(None)
        self.assertIn(("SYS", "JOUR"), self.dlt_file_spinner.context_map)
        self.assertEqual(self.dlt_file_spinner.context_map[("SYS", "JOUR")], ["queue_id2"])

    def test_handle_multiple_similar_filters(self):
        self.dlt_file_spinner.filter_queue.put(("queue_id0", [("SYS", "JOUR")], True))
        self.dlt_file_spinner.filter_queue.put(("queue_id1", [("SYS", "JOUR")], True))
        time.sleep(0.01)
        self.dlt_file_spinner.handle(None)
        self.assertIn(("SYS", "JOUR"), self.dlt_file_spinner.context_map)
        self.assertEqual(self.dlt_file_spinner.context_map[("SYS", "JOUR")], ["queue_id0", "queue_id1"])

    def test_handle_multiple_different_filters(self):
        self.filter_queue.put(("queue_id0", [("SYS", "JOUR")], True))
        self.filter_queue.put(("queue_id1", [("DA1", "DC1")], True))
        time.sleep(0.01)
        self.dlt_file_spinner.handle(None)
        self.assertIn(("SYS", "JOUR"), self.dlt_file_spinner.context_map)
        self.assertIn(("DA1", "DC1"), self.dlt_file_spinner.context_map)
        self.assertEqual(self.dlt_file_spinner.context_map[("SYS", "JOUR")], ["queue_id0"])
        self.assertEqual(self.dlt_file_spinner.context_map[("DA1", "DC1")], ["queue_id1"])

    def test_handle_message_tag_and_distribute(self):
        self.filter_queue.put(("queue_id0", [("SYS", "JOUR")], True))
        self.filter_queue.put(("queue_id1", [("DA1", "DC1")], True))
        self.filter_queue.put(("queue_id2", [("SYS", None)], True))
        self.filter_queue.put(("queue_id3", [(None, "DC1")], True))
        self.filter_queue.put(("queue_id4", [(None, None)], True))
        time.sleep(0.01)

        # - simulate receiving of messages
        for _ in range(10):
            for message in create_messages(stream_multiple, from_file=True):
                self.dlt_file_spinner.handle(message)

        self.assertIn(("SYS", "JOUR"), self.dlt_file_spinner.context_map)
        self.assertIn(("DA1", "DC1"), self.dlt_file_spinner.context_map)
        self.assertIn((None, None), self.dlt_file_spinner.context_map)
        self.assertIn(("SYS", None), self.dlt_file_spinner.context_map)
        self.assertIn((None, "DC1"), self.dlt_file_spinner.context_map)
        try:
            # 60 == 10 messages of each for SYS, JOUR and None combinations +
            #       10 for (None,None)
            messages = [self.message_queue.get(timeout=0.01) for _ in range(60)]

            # these queues should not get any messages from other queues
            self.assertEqual(len([msg for qid, msg in messages if qid == "queue_id0"]), 10)
            self.assertEqual(len([msg for qid, msg in messages if qid == "queue_id1"]), 10)
            self.assertEqual(len([msg for qid, msg in messages if qid == "queue_id2"]), 10)
            self.assertEqual(len([msg for qid, msg in messages if qid == "queue_id3"]), 10)
            # this queue should get all messages
            self.assertEqual(len([msg for qid, msg in messages if qid == "queue_id4"]), 20)
        except Empty:
            # - we should not get an Empty for at least 40 messages
            self.fail()

    def _update_dispatch_messages_from_dlt_file_spinner(self):
        for index in range(60):
            try:
                message = self.dlt_file_spinner.message_queue.get(timeout=0.01)
                if not self.dispatched_messages or message[1] != self.dispatched_messages[-1][1]:
                    self.dispatched_messages.append(message)
            except:  # noqa: E722
                pass

    def test_run_with_writing_to_file(self):
        """
        Test with real dlt file, which is written at runtime

        1. set filter_queue properly, so that the handled messages could be added to message_queue later
        2. start DLTFileSpinner
           At this moment, no messages are written to dlt file, so no messages in DLTFileSpinner.message_queue
        3. write 2 sample messages to dlt file
           Expectation: we could dispatch 2 messages from DLTFileSpinner.message_queue
        5. stop DLTFileSpinner
        """
        # 1. set filter_queue properly, so that the handled messages could be added to message_queue later
        self.filter_queue.put(("queue_id0", [("SYS", "JOUR")], True))
        self.filter_queue.put(("queue_id1", [("DA1", "DC1")], True))
        self.filter_queue.put(("queue_id2", [("SYS", None)], True))
        self.filter_queue.put(("queue_id3", [(None, "DC1")], True))
        self.filter_queue.put(("queue_id4", [(None, None)], True))
        time.sleep(0.01)
        # 2. start DLTFileSpinner
        self.assertFalse(self.dlt_file_spinner.is_alive())
        self.dlt_file_spinner.start()
        self.assertTrue(self.dlt_file_spinner.is_alive())
        self.assertNotEqual(self.dlt_file_spinner.pid, os.getpid())
        # dlt_reader is instantiated and keeps alive
        self.assertTrue(os.path.exists(self.dlt_file_spinner.file_name))
        # With empty file content, no messages are dispatched to message_queue
        time.sleep(2)
        self.assertTrue(self.dlt_file_spinner.message_queue.empty())
        # 3. write 2 sample messages to dlt file
        append_stream_to_file(stream_multiple, self.dlt_file_name)
        # Expect the written dlt logs are dispatched to message_queue
        self._update_dispatch_messages_from_dlt_file_spinner()
        self.assertEqual(2, len(self.dispatched_messages))
        # 4. stop DLTFileSpinner
        self.dlt_file_spinner.break_blocking_main_loop()
        self.stop_event.set()
        self.dlt_file_spinner.join()
        self.assertFalse(self.dlt_file_spinner.is_alive())

    def test_run_with_writing_to_file_twice(self):
        """
        Test with real dlt file, which is written at runtime 2 times

        1. set filter_queue properly, so that the handled messages could be added to message_queue later
        2. start DLTFileSpinner
        3. write 2 sample messages to dlt file
           Expectation: we could dispatch 2 messages from DLTFileSpinner.message_queue
        4. append 1 sample message to dlt file
           Expectation: we could dispatch 3 messages from DLTFileSpinner.message_queue
        5. stop DLTFileSpinner
        """
        # 1. set filter_queue properly, so that the handled messages could be added to message_queue later
        self.filter_queue.put(("queue_id0", [("SYS", "JOUR")], True))
        self.filter_queue.put(("queue_id1", [("DA1", "DC1")], True))
        self.filter_queue.put(("queue_id2", [("SYS", None)], True))
        self.filter_queue.put(("queue_id3", [(None, "DC1")], True))
        self.filter_queue.put(("queue_id4", [(None, None)], True))
        time.sleep(0.01)
        # 2. start DLTFileSpinner
        self.assertFalse(self.dlt_file_spinner.is_alive())
        self.dlt_file_spinner.start()
        self.assertTrue(self.dlt_file_spinner.is_alive())
        self.assertNotEqual(self.dlt_file_spinner.pid, os.getpid())
        # dlt_reader is instantiated and keeps alive
        self.assertTrue(os.path.exists(self.dlt_file_spinner.file_name))
        # With empty file content, no messages are dispatched to message_queue
        time.sleep(2)
        self.assertTrue(self.dlt_file_spinner.message_queue.empty())
        # 3. write 2 sample messages to dlt file
        append_stream_to_file(stream_multiple, self.dlt_file_name)
        # Expect the written dlt logs are dispatched to message_queue
        self._update_dispatch_messages_from_dlt_file_spinner()
        self.assertEqual(2, len(self.dispatched_messages))
        # 4. append 1 sample message to dlt file
        append_stream_to_file(stream_with_params, self.dlt_file_name)
        self._update_dispatch_messages_from_dlt_file_spinner()
        self.assertEqual(3, len(self.dispatched_messages))
        # 5. stop DLTFileSpinner
        self.dlt_file_spinner.break_blocking_main_loop()
        self.stop_event.set()
        self.dlt_file_spinner.join()
        self.assertFalse(self.dlt_file_spinner.is_alive())

    def test_run_with_writing_empty_apid_ctid_to_file(self):
        """
        Test with real dlt file, which contains message with apid=b"" and ctid=b""

        1. set filter_queue properly, so that the handled messages could be added to message_queue later
        2. start DLTFileSpinner
           At this moment, no messages are written to dlt file, so no messages in DLTFileSpinner.message_queue
        3. write message with apid=b"" and ctid=b"" to dlt file
           Expectation: we could dispatch 1 message from DLTFileSpinner.message_queue
                        and, apid==b"" and ctid==b""
        5. stop DLTFileSpinner
        """
        # 1. set filter_queue properly, so that the handled messages could be added to message_queue later
        self.filter_queue.put(("queue_id0", [(None, None)], True))
        time.sleep(0.01)
        # 2. start DLTFileSpinner
        self.assertFalse(self.dlt_file_spinner.is_alive())
        self.dlt_file_spinner.start()
        self.assertTrue(self.dlt_file_spinner.is_alive())
        self.assertNotEqual(self.dlt_file_spinner.pid, os.getpid())
        # dlt_reader is instantiated and keeps alive
        self.assertTrue(os.path.exists(self.dlt_file_spinner.file_name))
        # With empty file content, no messages are dispatched to message_queue
        time.sleep(2)
        self.assertTrue(self.dlt_file_spinner.message_queue.empty())
        # 3. write a message to dlt file
        # Construct a message with apid==b"" and ctid==b""
        message = create_messages(stream_with_params, from_file=True)[0]
        message.extendedheader.apid = b""
        message.extendedheader.ctid = b""
        # Write this message into dlt file
        append_message_to_file(message, self.dlt_file_name)
        # Expect the written dlt logs are dispatched to message_queue
        self._update_dispatch_messages_from_dlt_file_spinner()
        self.assertEqual(1, len(self.dispatched_messages))
        # Expectation: the received message should have apid==b"" and ctid==b""
        self.assertEqual("", self.dispatched_messages[0][1].apid)
        self.assertEqual("", self.dispatched_messages[0][1].ctid)
        # 4. stop DLTFileSpinner
        self.dlt_file_spinner.break_blocking_main_loop()
        self.stop_event.set()
        self.dlt_file_spinner.join()
        self.assertFalse(self.dlt_file_spinner.is_alive())
