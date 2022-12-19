# Copyright (C) 2021. BMW Car IT GmbH. All rights reserved.
"""Test DLTBroker with enabling dlt_time"""
from contextlib import contextmanager
from multiprocessing import Queue
import queue as tqueue
import time
from unittest.mock import ANY, patch, MagicMock

import pytest

from dlt.dlt_broker import create_filter_ack_queue, DLTBroker, logger
from dlt.dlt_broker_handlers import DLTContextHandler, DLTFilterAckMessageHandler, DLTMessageHandler
from tests.utils import MockDLTMessage


def fake_py_dlt_client_main_loop(client, callback, *args, **kwargs):
    return True


@contextmanager
def dlt_broker(pydlt_main_func=fake_py_dlt_client_main_loop, enable_dlt_time=True, enable_filter_set_ack=False):
    """Initialize a fake DLTBroker"""

    with patch("dlt.dlt_broker_handlers.DLTMessageHandler._client_connect"), patch(
        "dlt.dlt_broker_handlers.py_dlt_client_main_loop", side_effect=pydlt_main_func
    ):
        broker = DLTBroker("42.42.42.42", enable_dlt_time=enable_dlt_time, enable_filter_set_ack=enable_filter_set_ack)
        broker.msg_handler._client = MagicMock()

        try:
            broker.start()

            yield broker

        finally:
            broker.stop()


@contextmanager
def dlt_filter_ack_msg_handler():
    queue = Queue()

    handler = DLTFilterAckMessageHandler(queue)
    try:
        handler.start()
        queue.cancel_join_thread()

        yield (handler, queue)
    finally:
        handler.stop()
        queue.close()


def fake_dlt_msg_handler(msg, with_filter_ack_queue):
    """Create a fake DLTMessageHandler"""
    filter_queue = MagicMock()
    filter_ack_queue = MagicMock() if with_filter_ack_queue else None
    client_cfg = {"ip_address": b"127.0.0.1", "filename": b"/dev/null", "verbose": 0, "port": "1234"}

    filter_queue.empty.side_effect = [False, True]
    filter_queue.get_nowait.return_value = msg

    return DLTMessageHandler(
        filter_queue, MagicMock(), MagicMock(), client_cfg, dlt_time_value=None, filter_ack_queue=filter_ack_queue
    )


def test_start_stop_dlt_broker():
    """Test to stop DLTBroker with dlt-time normally"""
    with dlt_broker(fake_py_dlt_client_main_loop, enable_dlt_time=True) as broker:
        assert broker._dlt_time_value


def test_start_stop_dlt_broker_without_dlt_time():
    """Test to stop DLTBroker without dlt-time normally"""
    with dlt_broker(fake_py_dlt_client_main_loop, enable_dlt_time=False) as broker:
        assert not broker._dlt_time_value


@pytest.mark.parametrize(
    "input_sec,input_msec,expected_value",
    [
        (42, 42, 42.42),  # normal test case
        (1618993559, 7377682, 1618993559.7377682),  # big value. The value will be truncated when type is not double
    ],
)
def test_dlt_broker_get_dlt_time(input_sec, input_msec, expected_value):
    """Test to get time from DLTBroker"""

    def handle(client, callback=None, *args, **kwargs):
        return callback(MockDLTMessage(payload="test_payload", sec=input_sec, msec=input_msec))

    with dlt_broker(handle) as broker:
        time.sleep(0.01)

    assert broker.dlt_time() == expected_value


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

    assert sorted(time_vals) == [0.0, 43.42, 44.42, 45.42]


def test_start_stop_dlt_broker_with_dlt_ack_msg_handler():
    """Test to stop DLTBroker with ack msg handler normally"""
    with dlt_broker(fake_py_dlt_client_main_loop, enable_dlt_time=True, enable_filter_set_ack=True) as broker:
        assert broker.filter_ack_msg_handler


def test_start_stop_dlt_broker_without_dlt_ack_msg_handler():
    """Test to stop DLTBroker without ack msg handler normally"""
    with dlt_broker(fake_py_dlt_client_main_loop, enable_dlt_time=True, enable_filter_set_ack=False) as broker:
        assert not broker.filter_ack_msg_handler


def test_create_filter_ack_queue():
    """Test to register and unregister an ack queue"""
    handler_mock = MagicMock()

    with create_filter_ack_queue(handler_mock) as queue:
        queue.put(True)
        assert queue.get()

    handler_mock.register.assert_called_with(queue)
    handler_mock.unregister.assert_called_with(queue)


@pytest.mark.parametrize(
    "ack,required_ack,return_val",
    [
        (True, True, True),
        (False, False, True),
        (True, False, False),
        (False, True, False),
    ],
)
def test_recv_filter_set_ack(ack, required_ack, return_val):
    """Test to receive an ack value"""
    queue = tqueue.Queue()

    queue.put(ack)
    with dlt_broker(enable_filter_set_ack=True) as broker:
        assert return_val == broker._recv_filter_set_ack(queue, required_ack)


def test_recv_filter_set_ack_timeout_ignore():
    """Test not to receive an ack value"""
    queue = tqueue.Queue()

    with dlt_broker(enable_filter_set_ack=True) as broker:
        broker.filter_set_ack_timeout = 0.01
        broker.ignore_filter_set_ack_timeout = True

        assert not broker._recv_filter_set_ack(queue, True)


def test_recv_filter_set_ack_timeout_exception():
    """Test not to receive an ack value and with an exception"""
    queue = tqueue.Queue()

    with dlt_broker(enable_filter_set_ack=True) as broker:
        broker.filter_set_ack_timeout = 0.01
        broker.ignore_filter_set_ack_timeout = False

        with pytest.raises(tqueue.Empty) as err:
            broker._recv_filter_set_ack(queue, True)

        assert not str(err.value)


def test_add_context_with_ack():
    """Test to send a filter-setting message with required ack"""
    queue = tqueue.Queue()

    with patch("dlt.dlt_broker.DLTBroker._recv_filter_set_ack", return_value=True) as ack_mock:
        with dlt_broker(enable_filter_set_ack=True) as broker:
            ori_context_handler = broker.context_handler
            broker.context_handler = MagicMock()
            try:
                broker.add_context(queue, [("APID", "CTID")])

                broker.context_handler.register.assert_called()
                ack_mock.assert_called()
            finally:
                broker.context_handler = ori_context_handler


def test_add_context_with_ack_warning():
    """Test to send a filter-setting message but not received an ack"""
    queue = tqueue.Queue()

    with patch("dlt.dlt_broker.DLTBroker._recv_filter_set_ack", return_value=False) as ack_mock, patch.object(
        logger, "warning"
    ) as logger_mock:
        with dlt_broker(enable_filter_set_ack=True) as broker:
            ori_context_handler = broker.context_handler
            broker.context_handler = MagicMock()
            try:
                broker.add_context(queue, [("APID", "CTID")])

                broker.context_handler.register.assert_called()
                ack_mock.assert_called()

                logger_mock.assert_called_with(ANY, [("APID", "CTID")], id(queue))
            finally:
                broker.context_handler = ori_context_handler


def test_start_stop_dlt_filter_ack_msg_handler():
    """Test to start/stop DLTFilterAckMessageHandler normally"""

    with dlt_filter_ack_msg_handler() as (handler, _):
        pass

    assert not handler.is_alive()


def test_dlt_filter_ack_msg_handler_register():
    """Test to register a new ack queue into DLTFilterAckMessageHandler"""
    queue_ack = tqueue.Queue()

    with dlt_filter_ack_msg_handler() as (handler, queue):
        handler.register(queue_ack)

        queue.put((id(queue_ack), True))
        assert queue_ack.get()


def test_dlt_filter_ack_msg_handler_unregister():
    """Test to unregister a new ack queue into DLTFilterAckMessageHandler"""
    queue_ack = tqueue.Queue()

    with dlt_filter_ack_msg_handler() as (handler, queue):
        handler.register(queue_ack)

        handler.unregister(queue_ack)
        with pytest.raises(tqueue.Empty):
            queue.put((id(queue_ack), False))
            queue_ack.get_nowait()


def test_make_send_filter_msg():
    """Test to generate a filter message"""
    handler = DLTContextHandler(MagicMock(), MagicMock())

    is_register = True
    filters = [("APID", "CTID")]
    queue = MagicMock()

    assert handler._make_send_filter_msg(queue, filters, is_register) == (id(queue), filters, is_register)


def test_make_send_filter_msg_with_ack_queue():
    """Test to generate a filter message with ack queue setting"""
    handler = DLTContextHandler(MagicMock(), MagicMock())

    is_register = True
    filters = [("APID", "CTID")]
    queue = MagicMock()
    queue_ack = MagicMock()

    assert handler._make_send_filter_msg(queue, filters, is_register, context_filter_ack_queue=queue_ack) == (
        id(queue),
        id(queue_ack),
        filters,
        is_register,
    )


def test_dlt_message_handler_process_filter_queue_add():
    """Test to add a filter"""
    handler = fake_dlt_msg_handler(msg=(42, [("APID", "CTID")], True), with_filter_ack_queue=True)
    handler._process_filter_queue()

    assert handler.context_map[("APID", "CTID")] == [42]
    handler.filter_ack_queue.put.assert_not_called()


def test_dlt_message_handler_process_filter_queue_add_ack():
    """Test to add a filter with ack"""
    handler = fake_dlt_msg_handler(msg=(42, 43, [("APID", "CTID")], True), with_filter_ack_queue=True)
    handler._process_filter_queue()

    assert handler.context_map[("APID", "CTID")] == [42]
    handler.filter_ack_queue.put.assert_called_with((43, True))


def test_dlt_message_handler_process_filter_queue_remove():
    """Test to remove a filter"""
    handler = fake_dlt_msg_handler(msg=(42, [("APID", "CTID")], False), with_filter_ack_queue=True)
    handler.context_map[("APID", "CTID")].append(42)

    handler._process_filter_queue()

    assert ("APID", "CTID") not in handler.context_map
    handler.filter_ack_queue.put.assert_not_called()


def test_dlt_message_handler_process_filter_queue_remove_ack():
    """Test to remove a filter with ack"""
    handler = fake_dlt_msg_handler(msg=(42, 43, [("APID", "CTID")], False), with_filter_ack_queue=True)
    handler.context_map[("APID", "CTID")].append(42)

    handler._process_filter_queue()

    assert ("APID", "CTID") not in handler.context_map
    handler.filter_ack_queue.put.assert_called_with((43, False))


def test_dlt_message_handler_process_filter_queue_remove_exception():
    """Test to remove a filter when the filter does not exists"""
    handler = fake_dlt_msg_handler(msg=(42, [("APID", "CTID")], False), with_filter_ack_queue=True)

    handler._process_filter_queue()

    assert not handler.context_map[("APID", "CTID")]
    handler.filter_ack_queue.put.assert_not_called()
