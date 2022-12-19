# Copyright (C) 2015. BMW Car IT GmbH. All rights reserved.
"""DLT client helpers"""


class LimitCondition(object):
    """Condition object for counting messages"""

    def __init__(self, limit):
        """Constructor

        :param int limit: The maximum number of the messages for the condition
        """
        self.limit = limit

    def __call__(self):
        if self.limit is None:
            return True

        self.limit = self.limit - 1
        return self.limit >= 0


class ContinuousnessChecker(object):
    """ContinuousnessChecker class is intended to find problems in the order of DLT messages"""

    _ignore = ["DA1-DC1-0"]  # control message will be ignored - there is no continuation

    def __init__(self, start=0):
        self._index = start
        self._counter = dict()

    def __call__(self, message):
        key = "{}-{}-{}".format(message.apid, message.ctid, message.seid)

        self._index += 1

        if key in self._ignore:
            return

        if key in self._counter:
            # message of current type already received - check the continuousness
            err_msg = "Missing message detected. Message"
            err_msg += " #{} (apid='%s', ctid='%s', seid='%s')" % (message.apid, message.ctid, message.seid)
            err_msg += " should have counter '{}' instead of '{}'"

            if not (self._counter[key] + 1) % 256 == message.mcnt:
                counter = self._counter[key]
                self._counter[key] = message.mcnt
                raise RuntimeError(err_msg.format(self._index - 1, (counter + 1) % 256, message.mcnt))

            self._counter[key] = message.mcnt
        else:
            # first message of current type
            self._counter[key] = message.mcnt


def bytes_to_str(byte_or_str):
    """Return string from bytes"""
    if isinstance(byte_or_str, bytes):
        return byte_or_str.decode("utf8", errors="replace")

    return str(byte_or_str)
