# Copyright (C) 2016. BMW Car IT GmbH. All rights reserved.
"""Basic unittests for DLT messages"""

import io
import time

from nose.tools import assert_less

from dlt.dlt import DLTFilter

from .utils import create_messages

stream_one = io.BytesIO(b'5\x00\x00 MGHS\xdd\xf6e\xca&\x01DA1\x00DC1\x00\x02\x0f\x00\x00\x00\x02\x00\x00\x00\x00')
stream_two = io.BytesIO(b'5\x00\x00 MGHS\xdd\xf6e\xca&\x01DA1\x00DC2\x00\x02\x0f\x00\x00\x00\x02\x00\x00\x00\x00')

LOOPS = 100000


class TestsDLTMessagePerf(object):

    def setUp(self):
        self.msgs = [create_messages(stream_one) for i in range(int(LOOPS * 0.1))]
        self.msgs += [create_messages(stream_two) for i in range(int(LOOPS * 0.9))]

    def test_compare_dict(self):
        # with dict as other
        attrs = {"apid": "DA1", "ctid": "DC1"}
        for msg in self.msgs:
            msg.compare(other=attrs)

    def test_compare_filter(self):
        # with DLTFilter as other
        flt = DLTFilter()
        flt.add("DA1", "DC1")
        for msg in self.msgs:
            msg.compare(other=flt)

    def test_compare_mesage(self):
        # with dict as other
        other = create_messages(stream_one)
        for msg in self.msgs:
            msg.compare(other=other)
