from nose.tools import raises

from dlt.helpers import ContinuousnessChecker


class Msg(object):
    def __init__(self, apid, ctid, seid, mcnt):
        self.apid = apid
        self.ctid = ctid
        self.seid = seid
        self.mcnt = mcnt


def run_check(messages):
    cont = ContinuousnessChecker()
    for msg in messages:
        cont(msg)


class TestsContinuousness(object):

    def test_simple(self):
        messages = [
                    Msg("X", "Y", "99", 4),
                    Msg("X", "Y", "99", 5),
                    Msg("X", "Y", "99", 6),
                    Msg("X", "Y", "99", 7),
                    Msg("X", "Y", "99", 8)
                    ]
        run_check(messages)

    @raises(RuntimeError)
    def test_simple_missing(self):
        messages = [
                    Msg("X", "Y", "99", 4),
                    Msg("X", "Y", "99", 5),
                    Msg("X", "Y", "99", 6),
                    # 7 is missing
                    Msg("X", "Y", "99", 8),
                    Msg("X", "Y", "99", 9)
                    ]
        run_check(messages)

    def test_simple_over(self):
        # message counter is a unsigned char so counts till 255 and then restarted back to 0
        messages = [
                    Msg("X", "Y", "99", 254),
                    Msg("X", "Y", "99", 255),
                    Msg("X", "Y", "99", 0),
                    Msg("X", "Y", "99", 1)
                    ]
        run_check(messages)

    @raises(RuntimeError)
    def test_simple_reset(self):
        messages = [
                    Msg("X", "Y", "99", 230),
                    Msg("X", "Y", "99", 231),
                    Msg("X", "Y", "99", 0)
                    ]
        run_check(messages)

    def test_ignore_control(self):
        messages = [
                    Msg("DA1", "DC1", "0", 0),
                    Msg("X", "Y", "99", 231),
                    Msg("DA1", "DC1", "0", 0)
                    ]
        run_check(messages)

    def test_zeros_da1_dc1(self):
        messages = [
                    Msg("DA1", "DC1", "0", 0),
                    Msg("DA1", "DC1", "0", 0)
                    ]
        run_check(messages)

    @raises(RuntimeError)
    def test_zeros_non_da1_dc1(self):
        messages = [
                    Msg("X", "Y", "0", 0),
                    Msg("X", "Y", "0", 0)
                    ]
        run_check(messages)
