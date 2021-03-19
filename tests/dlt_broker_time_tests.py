# Copyright (C) 2021. BMW Car IT GmbH. All rights reserved.
"""Test DLTTimeHandler"""
from contextlib import contextmanager
import itertools
import time

from nose.tools import assert_false, assert_is_none, assert_is_not_none, assert_raises, assert_true, eq_
from parameterized import parameterized
import six

from dlt.dlt_broker import DLTBroker
from dlt.dlt_broker_handlers import DLTMessageHandler
from tests.utils import MockDLTMessage

if six.PY2:
    from mock import patch, MagicMock
else:
    from unittest.mock import patch, MagicMock


def fake_py_dlt_client_main_loop(client, callback, *args, **kwargs):
    return True


@contextmanager
def dlt_broker(pydlt_main_func=fake_py_dlt_client_main_loop, enable_dlt_time=True):
    """Initialize a fake DLTBroker"""

    with patch("dlt.dlt_broker_handlers.DLTMessageHandler._client_connect"), patch(
        "dlt.dlt_broker_handlers.py_dlt_client_main_loop", side_effect=pydlt_main_func
    ):
        broker = DLTBroker("42.42.42.42", enable_dlt_time=enable_dlt_time)
        broker.msg_handler._client = MagicMock()

        broker.start()

        yield broker

        broker.stop()


def test_start_stop_dlt_broker():
    """Test to stop DLTBroker with dlt-time normally"""
    with dlt_broker(fake_py_dlt_client_main_loop, enable_dlt_time=True) as broker:
        assert_is_not_none(broker._dlt_time_value)


def test_start_stop_dlt_broker_without_dlt_time():
    """Test to stop DLTBroker without dlt-time normally"""
    with dlt_broker(fake_py_dlt_client_main_loop, enable_dlt_time=False) as broker:
        assert_is_none(broker._dlt_time_value)


def test_dlt_broker_get_dlt_time():
    """Test to get time from DLTBroker"""

    def handle(client, callback=None, *args, **kwargs):
        return callback(MockDLTMessage(payload="test_payload", sec=42, msec=42))

    with dlt_broker(handle) as broker:
        time.sleep(0.01)

    assert abs(broker.dlt_time() - 42.42) <= 0.01


def test_dlt_broker_get_latest_dlt_time():
    """Test to get the latest time from DLTBroker"""
    # ref: https://stackoverflow.com/questions/3190706/nonlocal-keyword-in-python-2-x
    time_value = {"v": 42}

    def handle(client, callback=None, *args, **kwargs):
        if time_value["v"] < 45:
            time_value["v"] += 1

        time.sleep(0.01)
        return callback(MockDLTMessage(payload="test_payload", sec=time_value["v"], msec=42))

    with dlt_broker(handle) as broker:
        time_vals = set()
        for i in range(10):
            time_vals.add(broker.dlt_time())
            time.sleep(0.01)

    expected_times = [0.0, 43.42, 44.42, 45.42]
    error_value = (
        abs(dlt_value - expected_value) <= 0.01 for dlt_value, expected_value in zip(sorted(time_vals), expected_times)
    )
    assert all(error_value)
