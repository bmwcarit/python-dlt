# Copyright (C) 2026. BMW Car IT GmbH. All rights reserved.
"""Unit tests for handling corrupt messages in cDLTFile indexing and iteration."""

import os
import tempfile
import unittest

from dlt.dlt import cDLTFile
from tests.utils import msg_benoit


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


if __name__ == "__main__":
    unittest.main()
