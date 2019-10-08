# Copyright (C) 2015. BMW Car IT GmbH. All rights reserved.
"""Basic unittests for DLT messages"""
import io
import pickle
import re

try:
    from mock import patch, PropertyMock
except ImportError:
    from unittest.mock import patch, PropertyMock

from nose.tools import *

from dlt.dlt import DLTMessage

from .utils import create_messages, stream_one, stream_with_params, stream_multiple, msg_benoit, control_one


class TestsDLTMessageUnit(object):

    def test_compare_default_attrs(self):
        attrs = {"extendedheader.apid": "DA1", "extendedheader.ctid": "DC1"}
        msg = create_messages(stream_one)

        assert_true(msg.compare(other=attrs))
        assert_true(msg.compare(other={"extendedheader.ctid": "DC1"}))

    def test_equal(self):
        msg1 = create_messages(stream_one)
        msg2 = create_messages(stream_one)

        assert_equal(msg1, msg2)

    def test_easy_attributes(self):
        msg = create_messages(stream_one)

        assert_equal(msg.ecuid, "MGHS")
        assert_equal(msg.seid, 0)
        assert_equal(msg.tmsp, 372391.26500000001)
        assert_equal(msg.apid, "DA1")
        assert_equal(msg.ctid, "DC1")

    def test_compare(self):
        msg1 = create_messages(stream_one)
        msg2 = create_messages(stream_one)

        assert_true(msg1.compare(msg2))
        assert_true(msg1.compare(other=msg2))
        assert_true(msg1.compare(dict(apid="DA1", ctid="DC1")))
        assert_false(msg1.compare(dict(apid="DA1", ctid="XX")))

    def test_compare_regexp(self):
        msg1 = create_messages(stream_one)

        assert_true(msg1.compare(dict(apid="DA1", ctid=re.compile(r"D.*"))))
        assert_true(msg1.compare(dict(apid="DA1", ctid=re.compile(r"D.*"),
                                      payload_decoded=re.compile(r".connection_info ok."))))
        assert_true(msg1.compare(dict(apid="DA1", ctid=re.compile(r"D.*"),
                                      payload_decoded=re.compile(r".connection_info ok."))))
        assert_true(msg1.compare(dict(apid="DA1", ctid=re.compile(r"D.*"),
                                      payload_decoded=re.compile(r".*info ok."))))
        assert_true(msg1.compare(dict(apid="DA1", ctid="DC1", payload_decoded=re.compile(r".*info ok."))))
        assert_true(msg1.compare(dict(apid=re.compile(r"D."))))
        assert_true(msg1.compare(dict(apid=re.compile(r"D.+"))))
        assert_true(msg1.compare(dict(apid=re.compile(r"D."))))
        assert_false(msg1.compare(dict(apid=re.compile(r"X."))))

    def test_compare_regexp_nsm(self):
        nsm = create_messages(io.BytesIO(b'5\x00\x00 MGHS\xdd\xf6e\xca&\x01NSM\x00DC1\x00\x02\x0f\x00\x00'
                                         b'\x00\x02\x00\x00\x00\x00'))
        nsma = create_messages(io.BytesIO(b'5\x00\x00 MGHS\xdd\xf6e\xca&\x01NSMADC1\x00\x02\x0f\x00\x00'
                                          b'\x00\x02\x00\x00\x00\x00'))

        assert_true(nsm.compare(dict(apid=re.compile("^NSM$"))))
        assert_false(nsma.compare(dict(apid=re.compile("^NSM$"))))

        assert_true(nsm.compare(dict(apid="NSM")))
        assert_false(nsma.compare(dict(apid="NSM")))

        assert_true(nsm.compare(dict(apid=re.compile("NSM"))))
        assert_true(nsma.compare(dict(apid=re.compile("NSM"))))

    @raises(Exception)
    def test_compare_regexp_throw(self):
        assert_true(nsm.compare(dict(apid=b"NSM"), regexp=True))

    def test_compare_regexp_benoit(self):
        msg1 = create_messages(msg_benoit, from_file=True)[0]
        assert_true(msg1.compare({"apid": "DEMO",
                                  "ctid": "DATA",
                                  "payload_decoded": re.compile("Logging from the constructor of a global instance")}))

    def test_compare_two_msgs(self):
        msgs = create_messages(stream_multiple, from_file=True)
        assert_not_equal(msgs[0], msgs[-1])

    def test_compare_other_not_modified(self):
        msg = create_messages(stream_one)
        other = dict(apid='XX', ctid='DC1')
        assert_false(msg.compare(other))
        assert_equal(other, dict(apid='XX', ctid='DC1'))

    def test_compare_quick_return(self):
        msg = create_messages(stream_one)
        other = dict(apid=b'DA1', ctid=b'XX', ecuid=b'FOO')

        with patch('dlt.dlt.DLTMessage.ecuid', new_callable=PropertyMock) as ecuid:
            ecuid.return_value = b'FOO'
            assert_false(msg.compare(other))
            ecuid.assert_not_called()

    def test_compare_matching_apid_ctid(self):
        msg = create_messages(stream_one)
        other = dict(apid='DA1', ctid='DC1', ecuid='FOO')

        with patch('dlt.dlt.DLTMessage.ecuid', new_callable=PropertyMock) as ecuid:
            ecuid.return_value = 'BAR'
            assert_false(msg.compare(other))
            ecuid.assert_called_once()

            ecuid.return_value = 'FOO'
            assert_true(msg.compare(other))
            assert_equal(ecuid.call_count, 2)

    def test_pickle_api(self):
        messages = create_messages(stream_multiple, from_file=True)
        for msg in messages:
            assert_equal(msg, pickle.loads(pickle.dumps(msg)))

    def test_from_bytes_control(self):
        msg = DLTMessage.from_bytes(b"DLT\x011\xd9PY(<\x08\x00MGHS5\x00\x00 MGHS\x00\x00\x96\x85&\x01DA1\x00DC1"
                                    b"\x00\x02\x0f\x00\x00\x00\x02\x00\x00\x00\x00")

        assert_equal(msg.apid, "DA1")
        assert_equal(msg.ctid, "DC1")
        assert_equal(msg.ecuid, "MGHS")
        assert_equal(msg.tmsp, 3.8533)
        assert_equal(msg.storage_timestamp, 1498470705.539688)
        assert_equal(msg.payload_decoded, "[connection_info ok] connected \x00\x00\x00\x00")

    def test_from_bytes_log_multipayload(self):
        msg = DLTMessage.from_bytes(b"DLT\x011\xd9PYfI\x08\x00MGHS=\x00\x000MGHS\x00\x00\x03\x1e\x00\x00\x94\xc8A"
                                    b"\x01MON\x00CPUS\x00\x02\x00\x00\x10\x004 online cores\n\x00")

        assert_equal(msg.apid, "MON")
        assert_equal(msg.ctid, "CPUS")
        assert_equal(msg.ecuid, "MGHS")
        assert_equal(msg.tmsp, 3.8088)
        assert_equal(msg.payload_decoded, "4 online cores\n")

    def test_sort_data_control(self):
        data = (
            b"DLT\x011\xd9PY(<\x08\x00MGHS5\x00\x00 MGHS\x00\x00\x96\x85&\x01DA1\x00DC1"
            b"\x00\x02\x0f\x00\x00\x00\x02\x00\x00\x00\x00"
        )
        tmsp, length, apid, ctid = DLTMessage.extract_sort_data(data)

        assert_equal(tmsp, 3.8533)
        assert_equal(length, len(data))
        assert_equal(apid, "DA1")
        assert_equal(ctid, "DC1")

    def test_sort_data_log_multipayload(self):
        data = (
            b"DLT\x011\xd9PYfI\x08\x00MGHS=\x00\x000MGHS\x00\x00\x03\x1e\x00\x00\x94\xc8A"
            b"\x01MON\x00CPUS\x00\x02\x00\x00\x10\x004 online cores\n\x00"
        )
        tmsp, length, apid, ctid = DLTMessage.extract_sort_data(data)

        assert_equal(tmsp, 3.8088)
        assert_equal(length, len(data))
        assert_equal(apid, "MON")
        assert_equal(ctid, "CPUS")

    def test_largelog(self):
        data = (
            b'DLT\x012\xd9PY)\x00\x01\x00MGHS=o\x02\x04MGHS\x00\x00\x03\x1e\x00\x00\x9e\xb7'
            b'A\x01MON\x00THRD\x00\x02\x00\x00\xe4\x01Process avb_streamhandl with pid: 307 '
            b'"/usr/bin/avb_streamhandler_app_someip -s pluginias-media_transport-avb_config'
            b'uration_bmw_mgu.so --bg setup --target Harman_MGU_B1 -p MGU_ICAM -k local.alsa'
            b'.baseperiod=256 -k ptp.loopcount=0 -k ptp.pdelaycount=0 -k ptp.synccount=0 -k '
            b'sched.priority=20 -k tspec.vlanprio.low=3 -k tspec.presentation.time.offset.lo'
            b'w=2200000 -k tspec.interval.low=1333000 -k debug.loglevel._RXE=4 -k alsa.group'
            b'name=mgu_avbsh -n socnet0 -b 2 "  started 2401 msec ago\x00'
        )

        msg = DLTMessage.from_bytes(data)
        assert_equal(msg.apid, "MON")
        assert_equal(msg.ctid, "THRD")
        assert_equal(msg.ecuid, "MGHS")
        assert_equal(msg.tmsp, 4.0631)
        assert_equal(
            msg.payload_decoded,
            'Process avb_streamhandl with pid: 307 "/usr/bin/avb_streamhandler_app_someip -s '
            'pluginias-media_transport-avb_configuration_bmw_mgu.so --bg setup --target Harman_MGU_B1 -p MGU_ICAM '
            '-k local.alsa.baseperiod=256 -k ptp.loopcount=0 -k ptp.pdelaycount=0 -k ptp.synccount=0 '
            '-k sched.priority=20 -k tspec.vlanprio.low=3 -k tspec.presentation.time.offset.low=2200000 '
            '-k tspec.interval.low=1333000 -k debug.loglevel._RXE=4 -k alsa.groupname=mgu_avbsh -n socnet0 '
            '-b 2 "  started 2401 msec ago'
        )

        tmsp, length, apid, ctid = DLTMessage.extract_sort_data(data)
        assert_equal(msg.tmsp, tmsp)
        assert_equal(len(msg.to_bytes()), length)
        assert_equal(msg.apid, apid)
        assert_equal(msg.ctid, ctid)


class TestsPayload(object):

    def test_split(self):
        msg = create_messages(stream_with_params, from_file=True)[0]
        payload = msg.payload
        assert_equal(len(payload), msg.noar)
        assert_equal(payload[0], b"CLevelMonitor::notification() => commandType")
        assert_equal(payload[1], 3)
        assert_equal(payload[2], b"deviceId")
        assert_equal(payload[3], 5)
        assert_equal(payload[4], b"value")
        assert_equal(payload[5], 4074)
        assert_equal(payload[6], b"simulation status")
        assert_equal(payload[7], 0)
        assert_raises(IndexError, payload.__getitem__, 8)


class TestsControl(object):

    def test_load(self):
        msg = create_messages(control_one, from_file=True)[0]
        assert_equal(msg.apid, "DA1")
        assert_equal(msg.ctid, "DC1")
        assert_equal(msg.is_mode_verbose, 0)
        assert_equal(msg.payload_decoded, "[get_log_info 7] get_log_info, 07, 01 00 48 44 44 4d 01 00 43 41 50 49 ff"
                                          " ff 04 00 43 41 50 49 06 00 68 64 64 6d 67 72 72 65 6d 6f")
