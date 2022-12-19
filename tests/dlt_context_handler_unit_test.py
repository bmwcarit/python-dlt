# Copyright (C) 2016. BMW Car IT GmbH. All rights reserved.
from multiprocessing import Queue as mp_queue
from queue import Empty, Queue
import time
import unittest

from dlt.dlt_broker_handlers import DLTContextHandler
from tests.utils import create_messages, stream_one, stream_multiple


class TestDLTContextHandler(unittest.TestCase):
    def setUp(self):
        self.filter_queue = mp_queue()
        self.message_queue = mp_queue()
        self.handler = DLTContextHandler(self.filter_queue, self.message_queue)

    def test_init(self):
        self.assertFalse(self.handler.stop_flag.is_set())
        self.assertFalse(self.handler.is_alive())
        self.assertTrue(self.handler.filter_queue.empty())
        self.assertTrue(self.handler.message_queue.empty())

    def test_register_no_filter(self):
        queue = Queue()
        queue_id = id(queue)

        self.handler.register(queue)

        # When no filter is specified, filter (None, None) should be
        # added (ie: match all messages)
        self.assertIn(queue_id, self.handler.context_map)
        self.assertEqual(self.handler.context_map[queue_id], (queue, [(None, None)]))
        self.assertEqual(self.handler.filter_queue.get(), (queue_id, [(None, None)], True))

    def test_register_single_filter(self):
        queue = Queue()
        queue_id = id(queue)
        filters = ("SYS", "JOUR")

        self.handler.register(queue, filters)

        # Specified, filter should be added to filter_queue
        self.assertIn(queue_id, self.handler.context_map)
        self.assertEqual(self.handler.context_map[queue_id], (queue, filters))
        self.assertEqual(self.handler.filter_queue.get(), (queue_id, filters, True))

    def test_register_similar_filters(self):
        queue0 = Queue()
        queue_id0 = id(queue0)
        filters0 = ("SYS", "JOUR")

        queue1 = Queue()
        queue_id1 = id(queue1)
        filters1 = ("SYS", "JOUR")

        self.handler.register(queue0, filters0)
        self.handler.register(queue1, filters1)

        # Each queue should have a unique entry in the context_map and
        # filter_queue (even if they have the same filter)
        self.assertIn(queue_id0, self.handler.context_map)
        self.assertIn(queue_id1, self.handler.context_map)
        self.assertEqual(self.handler.context_map[queue_id0], (queue0, filters0))
        self.assertEqual(self.handler.context_map[queue_id1], (queue1, filters1))
        self.assertEqual(self.handler.filter_queue.get(), (queue_id0, filters0, True))
        self.assertEqual(self.handler.filter_queue.get(), (queue_id1, filters1, True))

    def test_unregister(self):
        queue = Queue()
        queue_id = id(queue)
        filters = ("SYS", "JOUR")

        self.handler.register(queue, filters)
        self.assertIn(queue_id, self.handler.context_map)
        self.assertEqual(self.handler.filter_queue.get(), (queue_id, filters, True))

        self.handler.unregister(queue)
        self.assertNotIn(queue_id, self.handler.context_map)
        self.assertEqual(self.handler.filter_queue.get(), (queue_id, filters, False))

    def test_run_no_messages(self):
        try:
            self.handler.start()
            time.sleep(0.2)
            self.handler.stop()
            self.assertTrue(self.handler.stop_flag.is_set())
            self.assertFalse(self.handler.is_alive())
        except:  # noqa: E722
            self.fail()

    def test_run_single_context_queue(self):
        queue = Queue()
        queue_id = id(queue)
        filters = ("DA1", "DC1")
        self.handler.register(queue, filters)

        self.handler.start()

        # - simulate feeding of messages into the message_queue
        for _ in range(10):
            self.handler.message_queue.put((queue_id, create_messages(stream_one)))

        try:
            for _ in range(10):
                queue.get(timeout=0.01)
        except Empty:
            # - we should not get an Empty for exactly 10 messages
            self.fail()
        finally:
            self.handler.stop()

    def test_run_multiple_context_queue(self):
        self.handler.start()

        queue0 = Queue()
        queue_id0 = id(queue0)
        filters0 = ("DA1", "DC1")
        self.handler.register(queue0, filters0)

        queue1 = Queue()
        queue_id1 = id(queue1)
        filters1 = ("SYS", "JOUR")
        self.handler.register(queue1, filters1)

        # - queue with no filter
        queue2 = Queue()
        queue_id2 = id(queue2)
        self.handler.register(queue2)

        # - simulate feeding of messages into the message_queue
        for _ in range(10):
            for message in create_messages(stream_multiple, from_file=True):
                queue_id = queue_id0 if message.apid == "DA1" else queue_id1
                self.handler.message_queue.put((queue_id, message))
                # - simulate feeding of all messages for the queue with
                # no filter.
                self.handler.message_queue.put((queue_id2, message))

        try:
            da1_messages = []
            sys_messages = []
            all_messages = []
            for _ in range(10):
                da1_messages.append(queue0.get(timeout=0.01))
                sys_messages.append(queue1.get(timeout=0.01))
                all_messages.append(queue2.get(timeout=0.01))

            # these queues should not get any messages from other queues
            self.assertTrue(all(msg.apid == "DA1" for msg in da1_messages))
            self.assertTrue(all(msg.apid == "SYS" for msg in sys_messages))
            # this queues should get all messages
            self.assertFalse(
                all(msg.apid == "DA1" for msg in all_messages) or all(msg.apid == "SYS" for msg in all_messages)
            )
        except Empty:
            # - we should not get an Empty for at least 10 messages
            self.fail()
        finally:
            self.handler.stop()

    def test_run_unregister_with_unread_messages(self):
        self.handler.start()
        queue = Queue()
        queue_id = id(queue)
        filters = ("DA1", "DC1")
        self.handler.register(queue, filters)

        self.assertIn(queue_id, self.handler.context_map)
        self.handler.unregister(queue)

        # - simulate feeding of messages into the message_queue
        for _ in range(3):
            self.handler.message_queue.put((queue_id, create_messages(stream_one)))

        try:
            self.assertNotIn(queue_id, self.handler.context_map)
            # allow some time for the thread to read all messages
            time.sleep(0.5)
            self.assertTrue(self.handler.message_queue.empty())
            self.assertTrue(queue.empty())
        finally:
            self.handler.stop()
