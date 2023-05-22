# Copyright (C) 2023. BMW Car IT GmbH. All rights reserved.
"""Test DLTBroker with message handler DLTFileSpinner"""
import os
import pytest
import tempfile
import time
import unittest
from unittest.mock import ANY, patch
from queue import Queue, Empty

from dlt.dlt_broker import DLTBroker, logger
from tests.utils import (
    stream_multiple,
    stream_with_params,
    append_stream_to_file,
    create_messages,
    append_message_to_file,
)


class TestDLTBrokerFromDLTFileSpinnerWithNotExistingDLT(unittest.TestCase):
    def setUp(self) -> None:
        self.broker = None
        _, self.dlt_file_name = tempfile.mkstemp(suffix=b".dlt")

    def tearDown(self) -> None:
        if self.broker:
            self.broker.stop()
        if os.path.exists(self.dlt_file_name):
            os.remove(self.dlt_file_name)

    def test_broker_with_not_existing_dlt_file(self):
        """
        Test DLTBroker could work with not existing dlt file

        1. prepare a file name which does not exist
        2. start dlt broker to dispatch messages from this not-existing file --> no error
        3. dlt broker could not add context successfully, but encounter a warning message
        4. no message could be dispatched from not existing file and throws out Queue.Empty exception
        5. dlt_time is 0.0, because it could not be reset according to the latest timestamp of messages
        """
        # Remove the dlt file
        os.remove(self.dlt_file_name)
        # Start broker with non-existing dlt file
        self.broker = DLTBroker(
            filename=self.dlt_file_name,
            enable_dlt_time=True,
            enable_filter_set_ack=True,
            ignore_filter_set_ack_timeout=True,
        )
        self.broker.start()
        # Add context should report warning message
        queue = Queue(maxsize=0)
        with patch.object(logger, "warning") as logger_mock:
            self.broker.add_context(queue, filters=None)
            logger_mock.assert_called_with(ANY, ANY, [(None, None)], id(queue))
        # Not existing dlt file should not throw any exception out
        for _ in range(5):
            with pytest.raises(Empty):
                queue.get_nowait()
        # dlt_time is not None, even though it is not reset with latest timestamp from messages
        self.assertEqual(self.broker.dlt_time(), 0.0)

    def test_broker_with_later_created_dlt_file(self):
        """
        Simulate a scenario: first dlt file does not exist, then dlt file is created and written with messages.

        1. delete the dlt file
        2. start broker
        3. create the dlt file and write 1 sample message
            Expectation: 1 message could be dispatched from broker
        """
        # 1. delete the dlt file
        os.remove(self.dlt_file_name)
        # 2. Start broker with non-existing dlt file
        self.broker = DLTBroker(
            filename=self.dlt_file_name,
            enable_dlt_time=True,
            enable_filter_set_ack=True,
            ignore_filter_set_ack_timeout=True,
        )
        self.broker.start()
        # Add context should report warning message
        queue = Queue(maxsize=0)
        self.broker.add_context(queue, filters=None)
        # 3. Write 1 sample message to the dlt file
        append_stream_to_file(stream_with_params, self.dlt_file_name)
        # Expectation: 1 message could be dispatched from broker
        time.sleep(0.5)
        self.assertIsNotNone(queue.get_nowait())
        # If we try to dispatch for another time, exception Queue.Empty is thrown,
        # because there is no new log from dlt file
        with pytest.raises(Empty):
            queue.get_nowait()


class TestDLTBrokerFromDLTFileSpinner(unittest.TestCase):
    def setUp(self):
        # Dlt file is created with empty content
        _, self.dlt_file_name = tempfile.mkstemp(suffix=b".dlt")
        self.dispatched_message_queue = Queue(maxsize=0)
        # Instantiate DLTBroker without ignoring fileter ack timeout
        self.broker = DLTBroker(
            filename=self.dlt_file_name,
            enable_dlt_time=True,
            enable_filter_set_ack=True,
            ignore_filter_set_ack_timeout=True,
        )
        self.broker.start()
        self.broker.add_context(self.dispatched_message_queue, filters=None)

    def tearDown(self):
        self.broker.stop()
        os.remove(self.dlt_file_name)

    def test_001_dispatch_from_empty_dlt_file(self):
        """
        From empty file, no message could be dispatched from queue and raise Queue.Empty.
        dlt_time is 0.0, because it could not be reset according to the latest timestamp of messages
        """
        for _ in range(5):
            with pytest.raises(Empty):
                self.dispatched_message_queue.get_nowait()
        self.assertEqual(self.broker.dlt_time(), 0.0)

    def test_002_dispatch_from_real_dlt_file(self):
        """
        Test DltBroker dispatches from a run-time written dlt file

        With a running dlt broker:
        1. Write 2 sample messages to dlt file
        2. These two messages could be dispatched with the running dlt broker
           With another try to dispatch, Queue.Empty is thrown, because no more logs could be read from dlt log;
           dlt_time from dlt_broker is equal to the timestamp of 2nd message
        3. Append another 1 message to the same dlt file
        4. Total 3 messages could be dispatched with the dlt broker
           With another try to dispatch, Queue.Empty is thrown, because no more logs could be read from dlt log;
           dlt_time from dlt_broker is equal to the timestamp of 3rd message
        """
        # 1. Write 2 sample messages to dlt file
        append_stream_to_file(stream_multiple, self.dlt_file_name)
        # 2. Dispatch 2 messages from dlt broker
        time.sleep(0.1)
        message_1 = self.dispatched_message_queue.get_nowait()
        time.sleep(0.1)
        message_2 = self.dispatched_message_queue.get_nowait()
        self.assertNotEqual(message_1, message_2)
        # If we try to dispatch for another time, exception Queue.Empty is thrown,
        # because there is no new log from dlt file
        with pytest.raises(Empty):
            self.dispatched_message_queue.get_nowait()
        # Validate dlt time from broker
        self.assertEqual(self.broker.dlt_time(), message_2.storage_timestamp)
        # 3. Append another 1 message to the same dlt file
        append_stream_to_file(stream_with_params, self.dlt_file_name)
        # 4. Total 3 messages could be dispatched with the dlt broker
        time.sleep(0.1)
        message_3 = self.dispatched_message_queue.get_nowait()
        self.assertNotEqual(message_1, message_3)
        self.assertNotEqual(message_2, message_3)
        # If try to dispatch for another time, exception Queue.Empty is thrown,
        # because there is no new log from dlt file
        with pytest.raises(Empty):
            self.dispatched_message_queue.get_nowait()
        # Validate dlt time from broker
        self.assertEqual(self.broker.dlt_time(), message_3.storage_timestamp)

    def test_003_dispatch_from_real_dlt_file(self):
        """
        Test DltBroker dispatches apid==b"" and ctid==b"" message from a run-time written dlt file

        With a running dlt broker:
        1. Write apid==b"" and ctid==b"" message to dlt file
        2. This message could be dispatched with the running dlt broker
           a. With another try to dispatch, Queue.Empty is thrown, because no more logs could be read from dlt log;
           b. dlt_time from dlt_broker is equal to the timestamp of this message
           c. the received message should have apid==b"" and ctid==b""
        """
        # 1. Write apid==b"" and ctid==b"" message to dlt file
        # Construct a message with apid==b"" and ctid==b""
        message = create_messages(stream_with_params, from_file=True)[0]
        message.extendedheader.apid = b""
        message.extendedheader.ctid = b""
        # Write this message into dlt file
        append_message_to_file(message, self.dlt_file_name)
        # 2. Dispatch from dlt broker
        time.sleep(0.5)
        message = self.dispatched_message_queue.get_nowait()
        # If we try to dispatch for another time, exception Queue.Empty is thrown,
        # because there is no new log from dlt file
        with pytest.raises(Empty):
            self.dispatched_message_queue.get_nowait()
        # Validate dlt time from broker
        self.assertEqual(self.broker.dlt_time(), message.storage_timestamp)
        # Expectation: the received message should have apid==b"" and ctid==b""
        self.assertEqual("", message.apid)
        self.assertEqual("", message.ctid)
