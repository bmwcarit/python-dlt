# Copyright (C) 2016. BMW Car IT GmbH. All rights reserved.

from dlt.helpers import LimitCondition


class TestsLimitCondition(object):

    __test__ = True

    def test_none(self):
        cond = LimitCondition(None)
        assert cond()

    def test_limit_decreasing(self):
        cond = LimitCondition(2)
        cond()
        assert cond.limit == 1
        assert cond()  # limit=0
        assert not cond()  # limit=-1
