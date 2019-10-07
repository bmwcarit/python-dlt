# Copyright (C) 2016. BMW Car IT GmbH. All rights reserved.
"""Basic unittests for DLTClient class"""

import unittest

try:
    from mock import patch, Mock
except ImportError:
    from unittest.mock import patch, Mock

from dlt.dlt import DLTClient, DLT_RETURN_OK, DLT_RETURN_ERROR


class TestDLTClient(unittest.TestCase):

    def setUp(self):
        # - patch port so that connect fails even if dlt-daemon is running
        self.client = DLTClient(servIP='127.0.0.1', port=424242)

    def test_connect_with_timeout_failed(self):
        # - timeout error
        self.assertFalse(self.client.connect(timeout=2))

        # - dlt_receiver_init error
        with patch('socket.create_connection', return_value=Mock(fileno=Mock(return_value=2000000))), \
                patch('dlt.dlt.dltlib.dlt_receiver_init', return_value=DLT_RETURN_ERROR):
            self.assertFalse(self.client.connect(timeout=2))

    def test_connect_with_timeout_success(self):
        with patch('socket.create_connection', return_value=Mock(fileno=Mock(return_value=2000000))), \
                patch('dlt.dlt.dltlib.dlt_receiver_init', return_value=DLT_RETURN_OK):
            self.assertTrue(self.client.connect(timeout=2))
