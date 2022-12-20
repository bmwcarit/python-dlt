# Copyright (C) 2015. BMW Car IT GmbH. All rights reserved.
"""Basic unittests for DLTFilter definition"""
import unittest

import ctypes

from dlt.dlt import DLTFilter
from dlt.core.core_base import DLT_FILTER_MAX, DLT_ID_SIZE


class TestDLTFilter(unittest.TestCase):
    def setUp(self):
        self.dlt_filter = DLTFilter()

    def tearDown(self):
        del self.dlt_filter

    def test_init(self):
        assert len(self.dlt_filter.apid) == DLT_FILTER_MAX
        assert len(self.dlt_filter.ctid) == DLT_FILTER_MAX
        assert self.dlt_filter.counter == 0

        for entry in self.dlt_filter.apid:
            assert ctypes.string_at(entry, DLT_ID_SIZE) == b"\0\0\0\0"

        for entry in self.dlt_filter.ctid:
            assert ctypes.string_at(entry, DLT_ID_SIZE) == b"\0\0\0\0"

    def test_add0(self):
        assert self.dlt_filter.add("AAA", "BBB") == 0
        assert self.dlt_filter.counter == 1
        assert len(self.dlt_filter.apid[0]) == 4
        assert len(self.dlt_filter.ctid[0]) == 4
        assert ctypes.string_at(self.dlt_filter.apid[0], DLT_ID_SIZE) == b"AAA\0"
        assert ctypes.string_at(self.dlt_filter.ctid[0], DLT_ID_SIZE) == b"BBB\0"

    def test_add1(self):
        assert self.dlt_filter.add("AAA", "BBB") == 0
        assert self.dlt_filter.add("XXX", "YYY") == 0
        assert self.dlt_filter.counter == 2
        assert ctypes.string_at(self.dlt_filter.apid[0], DLT_ID_SIZE) == b"AAA\0"
        assert ctypes.string_at(self.dlt_filter.ctid[0], DLT_ID_SIZE) == b"BBB\0"
        assert ctypes.string_at(self.dlt_filter.apid[1], DLT_ID_SIZE) == b"XXX\0"
        assert ctypes.string_at(self.dlt_filter.ctid[1], DLT_ID_SIZE) == b"YYY\0"

    def test_add2(self):
        assert self.dlt_filter.add("AAAA", "BBBB") == 0
        assert self.dlt_filter.add("XXX", "YYY") == 0
        assert self.dlt_filter.add("CCCC", "DDDD") == 0
        assert self.dlt_filter.counter == 3
        assert ctypes.string_at(self.dlt_filter.apid[0], DLT_ID_SIZE) == b"AAAA"
        assert ctypes.string_at(self.dlt_filter.ctid[0], DLT_ID_SIZE) == b"BBBB"
        assert ctypes.string_at(self.dlt_filter.apid[1], DLT_ID_SIZE) == b"XXX\0"
        assert ctypes.string_at(self.dlt_filter.ctid[1], DLT_ID_SIZE) == b"YYY\0"
        assert ctypes.string_at(self.dlt_filter.apid[2], DLT_ID_SIZE) == b"CCCC"
        assert ctypes.string_at(self.dlt_filter.ctid[2], DLT_ID_SIZE) == b"DDDD"

    def test_repr(self):
        assert self.dlt_filter.add("AAAA", "BBBB") == 0
        assert self.dlt_filter.add("XXX", "YYY") == 0
        assert self.dlt_filter.add("CCCC", "DDDD") == 0
        print(self.dlt_filter)
        assert str(self.dlt_filter) == str([(b"AAAA", b"BBBB"), (b"XXX", b"YYY"), (b"CCCC", b"DDDD")])
