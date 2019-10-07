# Copyright (C) 2016. BMW Car IT GmbH. All rights reserved.
import os
import time
import unittest
from multiprocessing.queues import Empty
from multiprocessing import Event

import six

if six.PY2:
    from multiprocessing.queues import Queue
else:
    from multiprocessing import Queue

from dlt.dlt_broker_handlers import DLTMessageHandler
from .utils import create_messages, stream_multiple


class TestDLTMessageHandler(unittest.TestCase):

    def setUp(self):
        self.filter_queue = Queue()
        self.message_queue = Queue()
        self.client_cfg = {"ip_address": b"127.0.0.1",
                           "filename": b"/dev/null",
                           "verbose": 0,
                           "port": "1234",
                           }
        self.stop_event = Event()
        self.handler = DLTMessageHandler(self.filter_queue, self.message_queue, self.stop_event, self.client_cfg)

    def test_init(self):
        self.assertFalse(self.handler.mp_stop_flag.is_set())
        self.assertFalse(self.handler.is_alive())
        self.assertTrue(self.handler.filter_queue.empty())
        self.assertTrue(self.handler.message_queue.empty())

    def test_run_basic(self):
        self.assertFalse(self.handler.is_alive())
        self.handler.start()
        self.assertTrue(self.handler.is_alive())
        self.assertNotEqual(self.handler.pid, os.getpid())
        self.stop_event.set()
        self.handler.join()
        self.assertFalse(self.handler.is_alive())

    def test_handle_add_new_filter(self):
        self.handler.filter_queue.put(("queue_id", [("SYS", "JOUR")], True))
        time.sleep(0.01)
        self.handler.handle(None)
        self.assertIn(("SYS", "JOUR"), self.handler.context_map)
        self.assertEqual(self.handler.context_map[("SYS", "JOUR")], ["queue_id"])

    def test_handle_remove_filter_single_entry(self):
        self.handler.filter_queue.put(("queue_id", [("SYS", "JOUR")], True))
        time.sleep(0.01)
        self.handler.handle(None)
        self.assertIn(("SYS", "JOUR"), self.handler.context_map)
        self.assertEqual(self.handler.context_map[("SYS", "JOUR")], ["queue_id"])

        self.handler.filter_queue.put(("queue_id", [("SYS", "JOUR")], False))
        time.sleep(0.01)
        self.handler.handle(None)
        self.assertNotIn(("SYS", "JOUR"), self.handler.context_map)

    def test_handle_remove_filter_multiple_entries(self):
        self.handler.filter_queue.put(("queue_id1", [("SYS", "JOUR")], True))
        self.handler.filter_queue.put(("queue_id2", [("SYS", "JOUR")], True))
        time.sleep(0.01)
        self.handler.handle(None)
        self.assertIn(("SYS", "JOUR"), self.handler.context_map)
        self.assertEqual(self.handler.context_map[("SYS", "JOUR")], ["queue_id1", "queue_id2"])

        self.handler.filter_queue.put(("queue_id1", [("SYS", "JOUR")], False))
        time.sleep(0.01)
        self.handler.handle(None)
        self.assertIn(("SYS", "JOUR"), self.handler.context_map)
        self.assertEqual(self.handler.context_map[("SYS", "JOUR")], ["queue_id2"])

    def test_handle_multiple_similar_filters(self):
        self.handler.filter_queue.put(("queue_id0", [("SYS", "JOUR")], True))
        self.handler.filter_queue.put(("queue_id1", [("SYS", "JOUR")], True))
        time.sleep(0.01)
        self.handler.handle(None)
        self.assertIn(("SYS", "JOUR"), self.handler.context_map)
        self.assertEqual(self.handler.context_map[("SYS", "JOUR")], ["queue_id0", "queue_id1"])

    def test_handle_multiple_different_filters(self):
        self.filter_queue.put(("queue_id0", [("SYS", "JOUR")], True))
        self.filter_queue.put(("queue_id1", [("DA1", "DC1")], True))
        time.sleep(0.01)
        self.handler.handle(None)
        self.assertIn(("SYS", "JOUR"), self.handler.context_map)
        self.assertIn(("DA1", "DC1"), self.handler.context_map)
        self.assertEqual(self.handler.context_map[("SYS", "JOUR")], ["queue_id0"])
        self.assertEqual(self.handler.context_map[("DA1", "DC1")], ["queue_id1"])

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
                self.handler.handle(message)

        self.assertIn(("SYS", "JOUR"), self.handler.context_map)
        self.assertIn(("DA1", "DC1"), self.handler.context_map)
        self.assertIn((None, None), self.handler.context_map)
        self.assertIn(("SYS", None), self.handler.context_map)
        self.assertIn((None, "DC1"), self.handler.context_map)
        try:
            # 60 == 10 messages of each for SYS, JOUR and None combinations +
            #       10 for (None,None)
            messages = [self.message_queue.get(timeout=0.01) for _ in range(60)]

            # these queues should not get any messages from other queues
            self.assertEqual(len([msg for qid, msg in messages if qid == 'queue_id0']), 10)
            self.assertEqual(len([msg for qid, msg in messages if qid == 'queue_id1']), 10)
            self.assertEqual(len([msg for qid, msg in messages if qid == 'queue_id2']), 10)
            self.assertEqual(len([msg for qid, msg in messages if qid == 'queue_id3']), 10)
            # this queue should get all messages
            self.assertEqual(len([msg for qid, msg in messages if qid == 'queue_id4']), 20)
        except Empty:
            # - we should not get an Empty for at least 40 messages
            self.fail()
