# Copyright (C) 2015. BMW Car IT GmbH. All rights reserved.
"""Basic unittests for DLT messages"""
import io
import pickle
import re
from unittest.mock import patch, PropertyMock

import pytest

from dlt.dlt import DLTMessage
from tests.utils import (
    create_messages,
    stream_one,
    stream_with_params,
    stream_multiple,
    stream_multiple_with_malformed_message_at_begining,
    msg_benoit,
    control_one,
)


class TestsDLTMessageUnit(object):
    def test_malformed_message(self):
        msgs = create_messages(stream_multiple_with_malformed_message_at_begining, from_file=True)

        assert msgs[0].message_id == 1279675715
        assert len(msgs) == 3
        assert not msgs[0].extendedheader

    def test_compare_default_attrs(self):
        attrs = {"extendedheader.apid": "DA1", "extendedheader.ctid": "DC1"}
        msg = create_messages(stream_one)

        assert msg.compare(other=attrs)
        assert msg.compare(other={"extendedheader.ctid": "DC1"})

    def test_equal(self):
        msg1 = create_messages(stream_one)
        msg2 = create_messages(stream_one)

        assert msg1 == msg2

    def test_easy_attributes(self):
        msg = create_messages(stream_one)

        assert msg.ecuid == "MGHS"
        assert msg.seid == 0
        assert msg.tmsp == 372391.26500000001
        assert msg.apid == "DA1"
        assert msg.ctid == "DC1"

    def test_compare(self):
        msg1 = create_messages(stream_one)
        msg2 = create_messages(stream_one)

        assert msg1.compare(msg2)
        assert msg1.compare(other=msg2)
        assert msg1.compare(dict(apid="DA1", ctid="DC1"))
        assert not msg1.compare(dict(apid="DA1", ctid="XX"))

    def test_compare_regexp(self):
        msg1 = create_messages(stream_one)

        assert msg1.compare(dict(apid="DA1", ctid=re.compile(r"D.*")))
        assert msg1.compare(
            dict(apid="DA1", ctid=re.compile(r"D.*"), payload_decoded=re.compile(r".connection_info ok."))
        )
        assert msg1.compare(
            dict(apid="DA1", ctid=re.compile(r"D.*"), payload_decoded=re.compile(r".connection_info ok."))
        )
        assert msg1.compare(dict(apid="DA1", ctid=re.compile(r"D.*"), payload_decoded=re.compile(r".*info ok.")))
        assert msg1.compare(dict(apid="DA1", ctid="DC1", payload_decoded=re.compile(r".*info ok.")))
        assert msg1.compare(dict(apid=re.compile(r"D.")))
        assert msg1.compare(dict(apid=re.compile(r"D.+")))
        assert msg1.compare(dict(apid=re.compile(r"D.")))
        assert not msg1.compare(dict(apid=re.compile(r"X.")))

    def test_compare_regexp_nsm(self):
        nsm = create_messages(
            io.BytesIO(b"5\x00\x00 MGHS\xdd\xf6e\xca&\x01NSM\x00DC1\x00\x02\x0f\x00\x00" b"\x00\x02\x00\x00\x00\x00")
        )
        nsma = create_messages(
            io.BytesIO(b"5\x00\x00 MGHS\xdd\xf6e\xca&\x01NSMADC1\x00\x02\x0f\x00\x00" b"\x00\x02\x00\x00\x00\x00")
        )

        assert nsm.compare(dict(apid=re.compile("^NSM$")))
        assert not nsma.compare(dict(apid=re.compile("^NSM$")))

        assert nsm.compare(dict(apid="NSM"))
        assert not nsma.compare(dict(apid="NSM"))

        assert nsm.compare(dict(apid=re.compile("NSM")))
        assert nsma.compare(dict(apid=re.compile("NSM")))

    def test_compare_regexp_throw(self):
        nsm = create_messages(
            io.BytesIO(b"5\x00\x00 MGHS\xdd\xf6e\xca&\x01NSM\x00DC1\x00\x02\x0f\x00\x00" b"\x00\x02\x00\x00\x00\x00")
        )
        with pytest.raises(Exception):
            assert nsm.compare(dict(apid=b"NSM"), regexp=True)

    def test_compare_regexp_benoit(self):
        msg1 = create_messages(msg_benoit, from_file=True)[0]
        assert msg1.compare(
            {
                "apid": "DEMO",
                "ctid": "DATA",
                "payload_decoded": re.compile("Logging from the constructor of a global instance"),
            }
        )

    def test_compare_two_msgs(self):
        msgs = create_messages(stream_multiple, from_file=True)
        assert msgs[0] != msgs[-1]

    def test_compare_other_not_modified(self):
        msg = create_messages(stream_one)
        other = dict(apid="XX", ctid="DC1")
        assert not msg.compare(other)
        assert other == dict(apid="XX", ctid="DC1")

    def test_compare_quick_return(self):
        msg = create_messages(stream_one)
        other = dict(apid=b"DA1", ctid=b"XX", ecuid=b"FOO")

        with patch("dlt.dlt.DLTMessage.ecuid", new_callable=PropertyMock) as ecuid:
            ecuid.return_value = b"FOO"
            assert not msg.compare(other)
            ecuid.assert_not_called()

    def test_compare_matching_apid_ctid(self):
        msg = create_messages(stream_one)
        other = dict(apid="DA1", ctid="DC1", ecuid="FOO")

        with patch("dlt.dlt.DLTMessage.ecuid", new_callable=PropertyMock) as ecuid:
            ecuid.return_value = "BAR"
            assert not msg.compare(other)
            ecuid.assert_called_once()

            ecuid.return_value = "FOO"
            assert msg.compare(other)
            assert ecuid.call_count == 2

    def test_pickle_api(self):
        messages = create_messages(stream_multiple, from_file=True)
        for msg in messages:
            assert msg == pickle.loads(pickle.dumps(msg))

    def test_from_bytes_control(self):
        msg = DLTMessage.from_bytes(
            b"DLT\x011\xd9PY(<\x08\x00MGHS5\x00\x00 MGHS\x00\x00\x96\x85&\x01DA1\x00DC1"
            b"\x00\x02\x0f\x00\x00\x00\x02\x00\x00\x00\x00"
        )

        assert msg.apid == "DA1"
        assert msg.ctid == "DC1"
        assert msg.ecuid == "MGHS"
        assert msg.tmsp == 3.8533
        assert msg.storage_timestamp == 1498470705.539688
        assert msg.payload_decoded == "[connection_info ok] connected "

    def test_from_bytes_log_multipayload(self):
        msg = DLTMessage.from_bytes(
            b"DLT\x011\xd9PYfI\x08\x00MGHS=\x00\x000MGHS\x00\x00\x03\x1e\x00\x00\x94\xc8A"
            b"\x01MON\x00CPUS\x00\x02\x00\x00\x10\x004 online cores\n\x00"
        )

        assert msg.apid == "MON"
        assert msg.ctid == "CPUS"
        assert msg.ecuid == "MGHS"
        assert msg.tmsp == 3.8088
        assert msg.payload_decoded == "4 online cores"

    def test_sort_data_control(self):
        data = (
            b"DLT\x011\xd9PY(<\x08\x00MGHS5\x00\x00 MGHS\x00\x00\x96\x85&\x01DA1\x00DC1"
            b"\x00\x02\x0f\x00\x00\x00\x02\x00\x00\x00\x00"
        )
        tmsp, length, apid, ctid = DLTMessage.extract_sort_data(data)

        assert tmsp == 3.8533
        assert length == len(data)
        assert apid == "DA1"
        assert ctid == "DC1"

    def test_sort_data_log_multipayload(self):
        data = (
            b"DLT\x011\xd9PYfI\x08\x00MGHS=\x00\x000MGHS\x00\x00\x03\x1e\x00\x00\x94\xc8A"
            b"\x01MON\x00CPUS\x00\x02\x00\x00\x10\x004 online cores\n\x00"
        )
        tmsp, length, apid, ctid = DLTMessage.extract_sort_data(data)

        assert tmsp == 3.8088
        assert length == len(data)
        assert apid == "MON"
        assert ctid == "CPUS"

    def test_largelog(self):
        data = (
            b"DLT\x012\xd9PY)\x00\x01\x00MGHS=o\x02\x04MGHS\x00\x00\x03\x1e\x00\x00\x9e\xb7"
            b"A\x01MON\x00THRD\x00\x02\x00\x00\xe4\x01Process avb_streamhandl with pid: 307 "
            b'"/usr/bin/avb_streamhandler_app_someip -s pluginias-media_transport-avb_config'
            b"uration_bmw_mgu.so --bg setup --target Harman_MGU_B1 -p MGU_ICAM -k local.alsa"
            b".baseperiod=256 -k ptp.loopcount=0 -k ptp.pdelaycount=0 -k ptp.synccount=0 -k "
            b"sched.priority=20 -k tspec.vlanprio.low=3 -k tspec.presentation.time.offset.lo"
            b"w=2200000 -k tspec.interval.low=1333000 -k debug.loglevel._RXE=4 -k alsa.group"
            b'name=mgu_avbsh -n socnet0 -b 2 "  started 2401 msec ago\x00'
        )

        msg = DLTMessage.from_bytes(data)
        assert msg.apid == "MON"
        assert msg.ctid == "THRD"
        assert msg.ecuid == "MGHS"
        assert msg.tmsp == 4.0631
        assert (
            msg.payload_decoded == 'Process avb_streamhandl with pid: 307 "/usr/bin/avb_streamhandler_app_someip -s '
            "pluginias-media_transport-avb_configuration_bmw_mgu.so --bg setup --target Harman_MGU_B1 -p MGU_ICAM "
            "-k local.alsa.baseperiod=256 -k ptp.loopcount=0 -k ptp.pdelaycount=0 -k ptp.synccount=0 "
            "-k sched.priority=20 -k tspec.vlanprio.low=3 -k tspec.presentation.time.offset.low=2200000 "
            "-k tspec.interval.low=1333000 -k debug.loglevel._RXE=4 -k alsa.groupname=mgu_avbsh -n socnet0 "
            '-b 2 "  started 2401 msec ago'
        )

        tmsp, length, apid, ctid = DLTMessage.extract_sort_data(data)
        assert msg.tmsp == tmsp
        assert len(msg.to_bytes()) == length
        assert msg.apid == apid
        assert msg.ctid == ctid


class TestsPayload(object):
    def test_split(self):
        msg = create_messages(stream_with_params, from_file=True)[0]
        payload = msg.payload
        assert len(payload) == msg.noar
        assert payload[0] == b"CLevelMonitor::notification() => commandType"
        assert payload[1] == 3
        assert payload[2] == b"deviceId"
        assert payload[3] == 5
        assert payload[4] == b"value"
        assert payload[5] == 4074
        assert payload[6] == b"simulation status"
        assert payload[7] == 0

        with pytest.raises(IndexError):
            payload.__getitem__(8)


class TestsControl(object):
    def test_load(self):
        msg = create_messages(control_one, from_file=True)[0]
        assert msg.apid == "DA1"
        assert msg.ctid == "DC1"
        assert msg.is_mode_verbose == 0
        assert (
            msg.payload_decoded == "[get_log_info 7] get_log_info, 07, 01 00 48 44 44 4d 01 00 43 41 50 49 ff"
            " ff 04 00 43 41 50 49 06 00 68 64 64 6d 67 72 72 65 6d 6f"
        )
