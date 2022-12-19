# Copyright (C) 2016. BMW Car IT GmbH. All rights reserved.
"""Basic unittests for the py_dlt_client_main_loop function"""
import ctypes
import functools
from io import BytesIO as StringIO
import socket
import unittest
from unittest.mock import patch, Mock

from dlt.dlt import py_dlt_client_main_loop, DLTClient, logger
from dlt.core import cDltStorageHeader
from tests.utils import stream_one


def mock_dlt_receiver_receive_socket(client_receiver, partial=False, Fail=False):
    if Fail:
        return 0
    stream_one.seek(0)
    buf = stream_one.read()
    if partial:
        buf = buf[:16]

    client_receiver._obj.buf = ctypes.create_string_buffer(buf)
    client_receiver._obj.bytesRcvd = len(buf)
    return len(buf)


class TestMainLoop(unittest.TestCase):
    def setUp(self):
        self.client = DLTClient()
        self.client._connected_socket = Mock()

    def test_target_down(self):
        with patch.object(self.client._connected_socket, "recv", side_effect=socket.timeout):
            callback = Mock(return_value="should not be called")

            with self.assertLogs(logger=logger) as dlt_logger:
                return_value = py_dlt_client_main_loop(self.client, callback=callback)
                self.assertFalse(return_value)

                log_output = dlt_logger.output
                self.assertEqual(len(log_output), 1)
                self.assertEqual(log_output[0], "ERROR:dlt.dlt:[]: DLTLib closed connected socket")

            self.assertFalse(callback.called)

    def test_target_up_nothing_to_read(self):
        with patch.object(self.client._connected_socket, "recv", return_value=b"") as mock_recv:
            callback = Mock(return_value="should not be called")
            self.assertFalse(py_dlt_client_main_loop(self.client, callback=callback))
            self.assertEqual(mock_recv.call_count, 1)
            self.assertFalse(callback.called)

    @patch("dlt.dlt.dltlib.dlt_receiver_move_to_begin", return_value=0)
    def test_exit_if_callback_returns_false(self, *ignored):
        with patch.object(self.client._connected_socket, "recv", return_value=b"X"):
            # setup dlt_receiver_receive to return a partial message
            replacement = functools.partial(mock_dlt_receiver_receive_socket, partial=True)
            with patch("dlt.dlt.dltlib.dlt_receiver_receive", new=replacement):
                self.assertFalse(py_dlt_client_main_loop(self.client, callback=lambda msg: False))

    def test_read_message(self, *ignored):
        dumpfile = StringIO()

        stream_one.seek(0)
        expected = stream_one.read()

        with patch.object(self.client._connected_socket, "recv", return_value=b"X"):
            # setup dlt_receiver_receive to return a complete message
            replacement = functools.partial(mock_dlt_receiver_receive_socket)
            callback = Mock(side_effect=[True, False, False])
            with patch("dlt.dlt.dltlib.dlt_receiver_receive", new=replacement):
                self.assertTrue(py_dlt_client_main_loop(self.client, dumpfile=dumpfile, callback=callback))
                self.assertEqual(dumpfile.getvalue()[ctypes.sizeof(cDltStorageHeader) :], expected)
