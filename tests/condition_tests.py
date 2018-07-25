# Copyright (C) 2016. BMW Car IT GmbH. All rights reserved.

from nose.tools import assert_equals, assert_false, assert_true, raises

from dlt.helpers import LimitCondition


class TestsLimitCondition(object):

    __test__ = True

    def test_none(self):
        cond = LimitCondition(None)
        assert_true(cond())

    def test_limit_decreasing(self):
        cond = LimitCondition(2)
        cond()
        assert_equals(cond.limit, 1)
        assert_true(cond())  # limit=0
        assert_false(cond())  # limit=-1
