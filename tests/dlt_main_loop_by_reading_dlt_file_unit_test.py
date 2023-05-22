# Copyright (C) 2023. BMW Car IT GmbH. All rights reserved.
"""Basic unittests for the py_dlt_file_main_loop function"""
import os
import unittest
import tempfile
from threading import Thread
import time

from dlt.dlt import cDLTFile, py_dlt_file_main_loop
from tests.utils import (
    append_stream_to_file,
    stream_multiple,
    stream_with_params,
    create_messages,
    append_message_to_file,
)


class TestMainLoopByReadingDltFile(unittest.TestCase):
    def setUp(self):
        # Empty content dlt file is created
        _, self.dlt_file_name = tempfile.mkstemp(suffix=b".dlt")
        self.dlt_reader = cDLTFile(filename=self.dlt_file_name, is_live=True, iterate_unblock_mode=False)
        # message_queue to store the dispatched messages from main loop
        self.message_queue = []
        # When callback() is called, then it is reset to True
        self.callback_is_called = False
        # With this variable, we could test different return value from callback()
        # If callback() returns True, then main loop keeps going; otherwise, it breaks
        self.callback_return_value = True
        # Thread for main loop, which is instantiated in test case
        self.main_loop = None

    def _callback_for_message(self, message):
        self.callback_is_called = True
        print("Called here")
        if message:
            self.message_queue.append(message)
        return self.callback_return_value

    def _start_main_loop(self):
        self.main_loop = Thread(
            target=py_dlt_file_main_loop,
            kwargs={"dlt_reader": self.dlt_reader, "callback": self._callback_for_message},
        )
        # self.main_loop.daemon = True
        self.main_loop.start()
        time.sleep(1)

    def tearDown(self):
        if not self.dlt_reader.stop_reading_proc.is_set():
            self.dlt_reader.stop_reading_proc.set()
            # After the stop of dlt_reader, main loop should be stopped automatically
            if self.main_loop:
                for _ in range(5):
                    if not self.main_loop.is_alive():
                        break
                    time.sleep(0.1)
                self.assertFalse(self.main_loop.is_alive())
        os.remove(self.dlt_file_name)

    def test_001_empty_dlt_file(self):
        """When dlt file has empty content, then no message could be dispatched, and no return value from main loop"""
        self._start_main_loop()
        time.sleep(0.1)
        # When file has empty content, callback() will not be called by any message
        self.assertFalse(self.callback_is_called)
        self.assertEqual(0, len(self.message_queue))

    def test_002_first_write_then_read_dlt_file(self):
        """
        Simulate a real dlt file case: first write to it, and then use main loop to read it
        """
        # First write to dlt file without opening main loop
        append_stream_to_file(stream_multiple, self.dlt_file_name)
        time.sleep(0.1)
        # Expectation: py_dlt_file_main_loop reads out the first batch messages to message_queue
        self._start_main_loop()
        time.sleep(0.1)
        self.assertTrue(self.callback_is_called)
        self.assertEqual(2, len(self.message_queue))

    def test_003_first_read_then_write_dlt_file(self):
        """
        Simulate a real dlt file case: first open main loop to read, then write to the file at opening main loop
        """
        # First only main loop to read dlt file
        self._start_main_loop()
        # Then write to dlt file
        append_stream_to_file(stream_multiple, self.dlt_file_name)
        time.sleep(0.1)
        # Expect the written logs could be dispatched by main loop
        self.assertTrue(self.callback_is_called)
        self.assertEqual(2, len(self.message_queue))

    def test_004_read_2_writes(self):
        """
        Test main loop reads from 2 consecutive writes to dlt file
        """
        # First only main loop to read dlt file
        self._start_main_loop()
        # First write to dlt file
        append_stream_to_file(stream_multiple, self.dlt_file_name)
        time.sleep(0.1)
        # Expect main loop could dispatch 2 logs
        self.assertTrue(self.callback_is_called)
        self.assertEqual(2, len(self.message_queue))
        # Second write to dlt file, and expect to dispatch 3 logs
        append_stream_to_file(stream_with_params, self.dlt_file_name)
        time.sleep(0.1)
        self.assertEqual(3, len(self.message_queue))

    def test_005_callback_return_false(self):
        """
        If callback returns false, then main loop should exit
        """
        # Set callback return value to False
        self.callback_return_value = False
        # Write to file
        append_stream_to_file(stream_multiple, self.dlt_file_name)
        time.sleep(0.1)
        # Open main loop to dispatch logs
        self._start_main_loop()
        # Expect main loop could dispatch 2 logs
        self.assertTrue(self.callback_is_called)
        # Callback returns False after it handles the first message, which terminates main loop
        # So, main loop wont be able to proceed the second message
        self.assertEqual(1, len(self.message_queue))
        self.assertFalse(self.main_loop.is_alive())

    def test_006_read_empty_apid_ctid_message(self):
        """
        Simulate a case to read a apid==b"" and ctid==b"" message
        """
        # Construct a message with apid==b"" and ctid==b""
        message = create_messages(stream_with_params, from_file=True)[0]
        message.extendedheader.apid = b""
        message.extendedheader.ctid = b""
        # Write this message into dlt file
        append_message_to_file(message, self.dlt_file_name)
        # Expectation: py_dlt_file_main_loop reads out the first batch messages to message_queue
        self._start_main_loop()
        time.sleep(0.1)
        self.assertTrue(self.callback_is_called)
        self.assertEqual(1, len(self.message_queue))
        # Expectation: the received message should have apid==b"" and ctid==b""
        self.assertEqual("", self.message_queue[0].apid)
        self.assertEqual("", self.message_queue[0].ctid)
