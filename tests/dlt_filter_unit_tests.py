
# Copyright (C) 2015. BMW Car IT GmbH. All rights reserved.
"""Basic unittests for DLTFilter definition"""
from __future__ import print_function

import ctypes

from nose.tools import *

from dlt.dlt import DLTFilter
from dlt.core.core_base import DLT_FILTER_MAX, DLT_ID_SIZE

class TestDLTFilter(object):

    def setUp(self):
        self.dlt_filter = DLTFilter()

    def tearDown(self):
        del(self.dlt_filter)

    def test_init(self):
        assert_equal(len(self.dlt_filter.apid), DLT_FILTER_MAX)
        assert_equal(len(self.dlt_filter.ctid), DLT_FILTER_MAX)
        assert_equal(self.dlt_filter.counter, 0)

        for entry in self.dlt_filter.apid:
            assert_true(ctypes.string_at(entry, DLT_ID_SIZE) == b"\0\0\0\0")

        for entry in self.dlt_filter.ctid:
            assert_true(ctypes.string_at(entry, DLT_ID_SIZE) == b"\0\0\0\0")

    def test_add0(self):
        assert_equal(self.dlt_filter.add("AAA", "BBB"), 0)
        assert_equal(self.dlt_filter.counter, 1)
        assert_equal(len(self.dlt_filter.apid[0]), 4)
        assert_equal(len(self.dlt_filter.ctid[0]), 4)
        assert_true(ctypes.string_at(self.dlt_filter.apid[0], DLT_ID_SIZE) == b"AAA\0")
        assert_true(ctypes.string_at(self.dlt_filter.ctid[0], DLT_ID_SIZE) == b"BBB\0")

    def test_add1(self):
        assert_equal(self.dlt_filter.add("AAA", "BBB"), 0)
        assert_equal(self.dlt_filter.add("XXX", "YYY"), 0)
        assert_equal(self.dlt_filter.counter, 2)
        assert_true(ctypes.string_at(self.dlt_filter.apid[0], DLT_ID_SIZE) == b"AAA\0")
        assert_true(ctypes.string_at(self.dlt_filter.ctid[0], DLT_ID_SIZE) == b"BBB\0")
        assert_true(ctypes.string_at(self.dlt_filter.apid[1], DLT_ID_SIZE) == b"XXX\0")
        assert_true(ctypes.string_at(self.dlt_filter.ctid[1], DLT_ID_SIZE) == b"YYY\0")

    def test_add2(self):
        assert_equal(self.dlt_filter.add("AAAA", "BBBB"), 0)
        assert_equal(self.dlt_filter.add("XXX", "YYY"), 0)
        assert_equal(self.dlt_filter.add("CCCC", "DDDD"), 0)
        assert_equal(self.dlt_filter.counter, 3)
        assert_true(ctypes.string_at(self.dlt_filter.apid[0], DLT_ID_SIZE) == b"AAAA")
        assert_true(ctypes.string_at(self.dlt_filter.ctid[0], DLT_ID_SIZE) == b"BBBB")
        assert_true(ctypes.string_at(self.dlt_filter.apid[1], DLT_ID_SIZE) == b"XXX\0")
        assert_true(ctypes.string_at(self.dlt_filter.ctid[1], DLT_ID_SIZE) == b"YYY\0")
        assert_true(ctypes.string_at(self.dlt_filter.apid[2], DLT_ID_SIZE) == b"CCCC")
        assert_true(ctypes.string_at(self.dlt_filter.ctid[2], DLT_ID_SIZE) == b"DDDD")

    def test_repr(self):
        assert_equal(self.dlt_filter.add("AAAA", "BBBB"), 0)
        assert_equal(self.dlt_filter.add("XXX", "YYY"), 0)
        assert_equal(self.dlt_filter.add("CCCC", "DDDD"), 0)
        print(self.dlt_filter)
        assert_true(str(self.dlt_filter) == str([(b"AAAA", b"BBBB"), (b"XXX", b"YYY"), (b"CCCC", b"DDDD")]))
