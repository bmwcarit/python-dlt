# Copyright (C) 2026. BMW Car IT GmbH. All rights reserved.
"""Unit tests for handling corrupt and incomplete messages in cDLTFile indexing and iteration."""

import os
import tempfile
import time
import unittest
from threading import Thread

from dlt.dlt import cDLTFile, py_dlt_file_main_loop
from tests.utils import msg_benoit, stream_with_params


class TestCorruptMessageHandling(unittest.TestCase):
    def setUp(self):
        # Construct a byte stream with:
        # - 1 valid message (valid_msg1)
        # - 1 corrupt message with valid DLT magic (DLT\x01) but failing plausibility check (MSGLEN=2)
        # - 3 valid messages after the corrupt message (valid_msg2, valid_msg3, valid_msg4)
        valid_msg1 = msg_benoit

        corrupt_msg = bytearray(msg_benoit)
        corrupt_msg[18] = 0
        corrupt_msg[19] = 2  # MSGLEN = 2 bytes -> fails standard header plausibility check

        valid_msg2 = msg_benoit
        valid_msg3 = msg_benoit
        valid_msg4 = msg_benoit

        self.stream = valid_msg1 + bytes(corrupt_msg) + valid_msg2 + valid_msg3 + valid_msg4

        fd, self.dlt_file_name = tempfile.mkstemp(suffix=b".dlt")
        with os.fdopen(fd, "wb") as f:
            f.write(self.stream)

    def tearDown(self):
        if os.path.exists(self.dlt_file_name):
            os.remove(self.dlt_file_name)

    def test_indexing_with_corrupt_message_header_magic_intact(self):
        """Test indexing recovers past a corrupt message where DLT magic header is intact."""
        dlt_reader = cDLTFile(filename=self.dlt_file_name, is_live=False)
        indexed = dlt_reader.read(self.dlt_file_name)

        self.assertTrue(indexed)
        # Verify indexing recovers past the corrupt message and indexes all 4 valid messages
        self.assertEqual(len(dlt_reader), 4)

    def test_iteration_with_corrupt_message_header_magic_intact(self):
        """Test iteration recovers past a corrupt message where DLT magic header is intact."""
        dlt_reader = cDLTFile(filename=self.dlt_file_name, is_live=False)
        messages = list(dlt_reader)

        # Verify iteration recovers past the corrupt message and yields all 4 valid messages
        self.assertEqual(len(messages), 4)
        self.assertGreater(dlt_reader.corrupt_msg_count, 0)


class TestLiveRunIncompleteMessageHandling(unittest.TestCase):
    def setUp(self):
        fd, self.dlt_file_name = tempfile.mkstemp(suffix=b".dlt")
        os.close(fd)
        self.dlt_reader = cDLTFile(filename=self.dlt_file_name, is_live=True, iterate_unblock_mode=False)
        self.message_queue = []
        self.main_loop = None

    def _callback_for_message(self, message):
        if message:
            self.message_queue.append(message)
        return True

    def _start_main_loop(self):
        self.main_loop = Thread(
            target=py_dlt_file_main_loop,
            kwargs={"dlt_reader": self.dlt_reader, "callback": self._callback_for_message},
        )
        self.main_loop.start()
        time.sleep(0.1)

    def tearDown(self):
        if not self.dlt_reader.stop_reading_proc.is_set():
            self.dlt_reader.stop_reading_proc.set()
            if self.main_loop:
                for _ in range(10):
                    if not self.main_loop.is_alive():
                        break
                    time.sleep(0.1)
        if os.path.exists(self.dlt_file_name):
            os.remove(self.dlt_file_name)

    def test_live_run_two_part_message_write_succeeds(self):
        """
        Start live reading first, then write messages one-by-one.
        Write one message in two parts so it is incomplete during one read attempt.
        Verify reading succeeds after the second part completes the message.
        """
        self._start_main_loop()

        # Write message 1
        with open(self.dlt_file_name, "ab") as f:
            f.write(msg_benoit)
            f.flush()
        time.sleep(0.2)
        self.assertEqual(len(self.message_queue), 1)

        # Write message 2 - Part 1 (incomplete storage header, e.g. 5 bytes)
        with open(self.dlt_file_name, "ab") as f:
            f.write(msg_benoit[:5])
            f.flush()
        time.sleep(0.2)
        # Message 2 is incomplete during this read attempt, so no new complete message is read yet
        self.assertEqual(len(self.message_queue), 1)

        # Write message 2 - Part 2 (remaining bytes of message 2)
        with open(self.dlt_file_name, "ab") as f:
            f.write(msg_benoit[5:])
            f.flush()
        time.sleep(0.2)
        # Message 2 is now completed and read back
        self.assertEqual(len(self.message_queue), 2)

        # Write message 3
        with open(self.dlt_file_name, "ab") as f:
            f.write(stream_with_params)
            f.flush()
        time.sleep(0.2)
        self.assertEqual(len(self.message_queue), 3)

    def test_live_run_incomplete_message_skipped(self):
        """
        Start live reading first, write message 1, then write part 1 of message 2,
        but skip writing part 2 of message 2 and write message 3.
        Reader recovers past the incomplete message fragment and reads message 3.
        """
        self._start_main_loop()

        # Write message 1
        with open(self.dlt_file_name, "ab") as f:
            f.write(msg_benoit)
            f.flush()
        time.sleep(0.2)
        self.assertEqual(len(self.message_queue), 1)

        # Write message 2 - Part 1 only (skip Part 2)
        with open(self.dlt_file_name, "ab") as f:
            f.write(msg_benoit[:5])
            f.flush()
        time.sleep(0.2)

        # Write message 3 (valid message following incomplete fragment)
        with open(self.dlt_file_name, "ab") as f:
            f.write(stream_with_params)
            f.flush()
        time.sleep(0.2)

        # Reader recovers and reads message 1 and message 3 (2 messages total)
        self.assertEqual(len(self.message_queue), 2)
        self.assertGreater(self.dlt_reader.corrupt_msg_count, 0)

    def test_live_run_incomplete_message_skipped_fast(self):
        """
        Start live reading first, write message 1, then write part 1 of message 2,
        but skip writing part 2 of message 2 and write message 3.
        Reader recovers past the incomplete message fragment and reads message 3.
        """
        self._start_main_loop()

        # Write message 1
        with open(self.dlt_file_name, "ab") as f:
            f.write(msg_benoit)
            f.flush()
        time.sleep(0.2)
        self.assertEqual(len(self.message_queue), 1)

        # Write message 2 - Part 1 only (skip Part 2) and message 3 in one write
        with open(self.dlt_file_name, "ab") as f:
            f.write(msg_benoit[:5])
            f.write(stream_with_params)
            f.flush()
        time.sleep(0.2)

        # Write message 4 (valid message following incomplete fragment)
        with open(self.dlt_file_name, "ab") as f:
            f.write(msg_benoit)
            f.flush()
        time.sleep(0.2)

        # Reader recovers and reads message 1, message 3, and message 4 (3 messages total)
        self.assertEqual(len(self.message_queue), 3)
        self.assertGreater(self.dlt_reader.corrupt_msg_count, 0)


if __name__ == "__main__":
    unittest.main()
