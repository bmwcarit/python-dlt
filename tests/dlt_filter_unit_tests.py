
# Copyright (C) 2015. BMW Car IT GmbH. All rights reserved.
"""Basic unittests for DLTFilter definition"""
import ctypes

from nose.tools import *

from dlt.dlt import DLTFilter, DLT_FILTER_MAX, DLT_ID_SIZE


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
            assert_true(ctypes.string_at(entry, DLT_ID_SIZE) == "\0\0\0\0")

        for entry in self.dlt_filter.ctid:
            assert_true(ctypes.string_at(entry, DLT_ID_SIZE) == "\0\0\0\0")

    def test_add0(self):
        self.dlt_filter.add("AAA", "BBB")
        assert_equal(self.dlt_filter.counter, 1)
        assert_equal(len(self.dlt_filter.apid[0]), 4)
        assert_equal(len(self.dlt_filter.ctid[0]), 4)
        assert_true(ctypes.string_at(self.dlt_filter.apid[0], DLT_ID_SIZE) == "AAA\0")
        assert_true(ctypes.string_at(self.dlt_filter.ctid[0], DLT_ID_SIZE) == "BBB\0")

    def test_add1(self):
        self.dlt_filter.add("AAA", "BBB")
        self.dlt_filter.add("XXX", "YYY")
        assert_equal(self.dlt_filter.counter, 2)
        assert_true(ctypes.string_at(self.dlt_filter.apid[0], DLT_ID_SIZE) == "AAA\0")
        assert_true(ctypes.string_at(self.dlt_filter.ctid[0], DLT_ID_SIZE) == "BBB\0")
        assert_true(ctypes.string_at(self.dlt_filter.apid[1], DLT_ID_SIZE) == "XXX\0")
        assert_true(ctypes.string_at(self.dlt_filter.ctid[1], DLT_ID_SIZE) == "YYY\0")

    def test_add2(self):
        self.dlt_filter.add("AAAA", "BBBB")
        self.dlt_filter.add("XXX", "YYY")
        self.dlt_filter.add("CCCC", "DDDD")
        assert_equal(self.dlt_filter.counter, 3)
        assert_true(ctypes.string_at(self.dlt_filter.apid[0], DLT_ID_SIZE) == "AAAA")
        assert_true(ctypes.string_at(self.dlt_filter.ctid[0], DLT_ID_SIZE) == "BBBB")
        assert_true(ctypes.string_at(self.dlt_filter.apid[1], DLT_ID_SIZE) == "XXX\0")
        assert_true(ctypes.string_at(self.dlt_filter.ctid[1], DLT_ID_SIZE) == "YYY\0")
        assert_true(ctypes.string_at(self.dlt_filter.apid[2], DLT_ID_SIZE) == "CCCC")
        assert_true(ctypes.string_at(self.dlt_filter.ctid[2], DLT_ID_SIZE) == "DDDD")

    def test_repr(self):
        self.dlt_filter.add("AAAA", "BBBB")
        self.dlt_filter.add("XXX", "YYY")
        self.dlt_filter.add("CCCC", "DDDD")
        assert_true(str(self.dlt_filter) == str([("AAAA", "BBBB"), ("XXX", "YYY"), ("CCCC", "DDDD")]))
