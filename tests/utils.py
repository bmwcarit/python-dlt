# Copyright (C) 2016. BMW Car IT GmbH. All rights reserved.
"""Test helpers and data"""

import atexit
import ctypes
import io
import tempfile
import os

from dlt.dlt import DLTClient, load


stream_one = io.BytesIO(b"5\x00\x00 MGHS\xdd\xf6e\xca&\x01DA1\x00DC1\x00\x02\x0f\x00\x00\x00\x02\x00\x00\x00\x00")
stream_with_params = (
    b"DLT\x01\xc2<\x85W\xc7\xc5\x02\x00MGHS=r\x00\xa0MGHS\x00\x00\x02B\x00X\xd4\xf1A\x08"
    b"ENV\x00LVLM\x00\x02\x00\x00-\x00CLevelMonitor::notification() => commandType\x00#"
    b"\x00\x00\x00\x03\x00\x00\x00\x00\x02\x00\x00\t\x00deviceId\x00#\x00\x00\x00\x05\x00"
    b"\x00\x00\x00\x02\x00\x00\x06\x00value\x00#\x00\x00\x00\xea\x0f\x00\x00\x00\x02\x00"
    b"\x00\x12\x00simulation status\x00#\x00\x00\x00\x00\x00\x00\x00"
)

stream_multiple = (
    b"DLT\x01#o\xd1WD>\x0c\x00MGHS5\x00\x00YMGHS\x00\x01\x80\xd1&\x01DA1\x00DC1\x00\x03\x00\x00\x00"
    b"\x07\x01\x00SYS\x00\x01\x00FILE\xff\xff\x16\x00File transfer manager.\x12\x00"
    b"DLT System ManagerremoDLT\x01#o\xd1Wo>\x0c\x00MGHS=\x00\x01PMGHS\x00\x00\x03\xf4\x00"
    b"\x01i\xa6A\x05SYS\x00JOUR\x00\x02\x00\x00\x1b\x002011/11/11 11:11:18.005274\x00\x00\x02\x00\x00"
    b"\t\x006.005274\x00\x00\x02\x00\x00\x16\x00systemd-journal[748]:\x00\x00\x02\x00\x00\x0f\x00"
    b"Informational:\x00\x00\x02\x00\x00\xcf\x00Runtime journal (/run/log/journal/) is currently"
    b" using 8.0M.\nMaximum allowed usage is set to 385.9M.\nLeaving at least 578.8M free (of"
    b" currently available 3.7G of space).\nEnforced usage limit is thus 385.9M.\x00"
)

msg_benoit = (
    b"DLT\x01\xa5\xd1\xceW\x90\xb9\r\x00MGHS=\x00\x00RMGHS\x00\x00\n[\x00\x0f\x9b#A\x01DEMODATA\x00"
    b"\x82\x00\x002\x00Logging from the constructor of a global instance\x00"
)


control_one = (
    b"DLT\x01#o\xd1W\x99!\x0c\x00MGHS5\x00\x00;MGHS\x00\x01\x7f\xdb&\x01DA1\x00DC1\x00\x03"
    b"\x00\x00\x00\x07\x01\x00HDDM\x01\x00CAPI\xff\xff\x04\x00CAPI\x06\x00hddmgrremo"
)

# DLT file with invalid storage header and frames
file_storage_clean = (
    b"DLT\x01\x9a\xc6\xbfW\x020\t\x00MGHS5\x00\x00 MGHS\x00\x02\x8aC&\x01DA1\x00DC1"
    b"\x00\x02\x0f\x00\x00\x00\x02\x00\x00\x00\x00DLT\x01\x9a\xc6\xbfWoA\t\x00MGHS="
    b"\x00\x00NMGHS\x00\x00\x049\x00\x01p<A\x01DLTDINTM\x00\x02\x00\x00.\x00Daemon "
    b"launched. Starting to output traces...\x00DLT\x01\x9a\xc6\xbfW_H\t\x00MGHS=\x01"
    b"\x00qMGHS\x00\x00\x049\x00\x01pxA\x01DLTDINTM\x00\x02\x00\x00Q\x00ApplicationID"
    b"'PERD' registered for PID 987, Description=Personalization Daemon\n\x00"
)

# DLT file with invalid storage header but valid frames
file_storage_invalid_storage_hdr = (
    b"DLT\x01V\x03EX8\x06\x0b\x00\x00\x00\x00\x00=\x9d\x00\xaaMGHS\x00"
    b"\x00\x04$\x00\n\x11\xed1\x01NAVCSPCODLT\x01V\x03EXuD\x0c\x00\x00"
    b"\x00\x00\x00'\x01\x00\x1bXORA\x16\x02\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x11\x04\x00\x00\x00\x00DLT\x01V\x03EX\xfd[\x0c\x00"
    b"\x00\x00\x00\x005\x00\x00 MGHS\x00\n\x14\xda&\x01DA1\x00DC1\x00\x02"
    b"\x0f\x00\x00\x00\x02\x00\x00\x00\x00DLT\x01V\x03EXel\x0c\x00\x00\x00"
    b"\x00\x005\x00\x00 MGHS\x00\n\x11\xfb&\x01DA1\x00DC1\x00\x02\x0f\x00"
    b"\x00\x00\x01\x00\x00\x00\x00DLT\x01V\x03EXvl\x0c\x00\x00\x00\x00\x00"
    b"=\x86\x00cMGHS\x00\x00\x07\xa7\x00\n\x12\x1cA\x01NAVIASIA\x00\x02\x00"
    b"\x00C\x00[MSG_NV_MD] [NVS_MV][WIN1]iparam_update gui_mode(0) shmem "
    b"val(0) \n\x00DLT\x01V\x03EX}l\x0c\x00\x00\x00\x00\x00=\x87\x00WMGHS"
    b"\x00\x00\x07\xa7\x00\n\x12!A\x01NAVIASIA\x00\x02\x00\x007\x00[MSG_NV"
    b"_MD] [NVS_MV][WIN1] full menu stratframe(1479)\n\x00DLT\x01V\x03EX\x86"
    b"l\x0c\x00\x00\x00\x00\x00=n\x00\x89MGHS\x00\x00\x04$\x00\n\x12*A\x01NAV"
    b"CBLPS\x00\x02\x00\x00i\x00[Thread A] [PositioningCanAdapter.cpp::operat"
    b"or():92] Send: GPSRo"
)

file_with_four_lifecycles = (
    b"DLT\x01\xc5\x82\xdaX\x19\x93\r\x00XORA'\x01\x00\x1bXORA"  # trace to buffer
    b"\x16\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x11\x04\x00\x00\x00\x00"
    b"DLT\x01\xc5\x82\xdaXQi\x0e\x00MGHS5\x00\x00 MGHS"  # trace to buffer
    b"\x00\x03U\xe0&\x01DA1\x00DC1\x00\x02\x0f\x00\x00\x00\x02\x00\x00\x00\x00"
    b"DLT\x01\xc5\x82\xdaX\x82o\x0e\x00MGHS=\x00\x00NMGHS"  # first lifecycle
    b"\x00\x00\x02r\x00\x00\x8frA\x01DLTDINTM\x00\x02\x00\x00.\x00"
    b"Daemon launched. Starting to output traces...\x00"
    b"DLT\x01\xc9\xc1\x91Y\xbf\x1b\x00\x00MGHS5\x00\x00 MGHS"  # trace to buffer
    b"\x00\x00v\n&\x01DA1\x00DC1\x00\x02\x0f\x00\x00\x00\x02\x00\x00\x00\x00"
    b"DLT\x01\xc9\xc1\x91Y\x9f/\x00\x00MGHS=\x00\x00NMGHS"  # new lifecycle
    b"\x00\x00\x032\x00\x00IWA\x01DLTDINTM\x00\x02\x00\x00.\x00"
    b"Daemon launched. Starting to output traces...\x00"
    b"DLT\x01m\xc2\x91Y\x9f\xda\x07\x00MGHS5\x00\x00 MGHS"  # no new lifecycle
    b"\x00\x00_\xde&\x01DA1\x00DC1\x00\x02\x0f\x00\x00\x00\x02\x00\x00\x00\x00"
    b"DLT\x01m\xc2\x91Y\xad\xe4\x07\x00MGHS=\x01\x00zMGHS"  # random trace
    b"\x00\x00\x02\xab\x00\x00@VA\x01DLTDINTM\x00\x02\x00\x00Z\x00"
    b"ApplicationID 'DBSY' registered for PID 689, Description=DBus"
    b" Logging|SysInfra|Log&Trace\n\x00"
    b"DLT\x01\xed\xc2\x91Y\x0f\xf0\x08\x00MGHS5\x00\x00 MGHS"  # trace to buffer
    b"\x00\x00\x9dC&\x01DA1\x00DC1\x00\x02\x0f\x00\x00\x00\x02\x00\x00\x00\x00"
    b"DLT\x01\xed\xc2\x91Y\x17.\n\x00MGHS=\x00\x00NMGHS"  # new lifecycle
    b"\x00\x00\x02\xae\x00\x00@/A\x01DLTDINTM\x00\x02\x00\x00.\x00"
    b"Daemon launched. Starting to output traces...\x00"
    b"DLT\x01]\xc3\x91Y,\x91\r\x00MGHS=\x00\x00NMGHS"  # new lifecycle
    b"\x00\x00\x02\xbd\x00\x00G\xefA\x01DLTDINTM\x00\x02\x00\x00.\x00"
    b"Daemon launched. Starting to output traces...\x00"
    b"DLT\x01U\xc4\x91Y\x8c>\n\x00MGHS5\x00\x00 MGHS"  # not to buffer
    b"\x00\x00mj&\x01DA1\x00DC1\x00\x02\x0f\x00\x00\x00\x02\x00\x00\x00\x00"
)

file_with_lifecycles_without_start = (
    b"DLT\x01\xc5\x82\xdaX\x19\x93\r\x00XORA'\x01\x00\x1bXORA"  # trace to buffer
    b"\x16\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x11\x04\x00\x00\x00\x00"
    b"DLT\x01\xc5\x82\xdaXQi\x0e\x00MGHS5\x00\x00 MGHS"  # trace to buffer
    b"\x00\x03U\xe0&\x01DA1\x00DC1\x00\x02\x0f\x00\x00\x00\x02\x00\x00\x00\x00"
    b"DLT\x01m\xc2\x91Y\xad\xe4\x07\x00MGHS=\x01\x00zMGHS"  # random trace
    b"\x00\x00\x02\xab\x00\x00@VA\x01DLTDINTM\x00\x02\x00\x00Z\x00"
    b"ApplicationID 'DBSY' registered for PID 689, Description=DBus"
    b" Logging|SysInfra|Log&Trace\n\x00"
    b"DLT\x01\xed\xc2\x91Y\x0f\xf0\x08\x00MGHS5\x00\x00 MGHS"  # trace to buffer
    b"\x00\x00\x9dC&\x01DA1\x00DC1\x00\x02\x0f\x00\x00\x00\x02\x00\x00\x00\x00"
    b"DLT\x01\xed\xc2\x91Y\x17.\n\x00MGHS=\x00\x00NMGHS"  # new lifecycle
    b"\x00\x00\x02\xae\x00\x00@/A\x01DLTDINTM\x00\x02\x00\x00.\x00"
    b"Daemon launched. Starting to output traces...\x00"
)


def create_messages(stream, from_file=False):
    if from_file is False:
        stream.seek(0)
        buf = stream.read()

        client = DLTClient()
        client.receiver.buf = ctypes.create_string_buffer(buf)
        client.receiver.bytesRcvd = len(buf)

        return client.read_message()

    _, tmpname = tempfile.mkstemp(suffix=b"")
    tmpfile = open(tmpname, "wb")
    tmpfile.write(stream)
    tmpfile.flush()
    tmpfile.seek(0)
    tmpfile.close()

    atexit.register(os.remove, tmpname)

    msgs = load(tmpname)
    return msgs


class MockDLTMessage(object):
    """Mock DLT message for dltlyse plugin testing"""

    def __init__(self, ecuid="MGHS", apid="SYS", ctid="JOUR", sid="958", payload="", tmsp=0.0, sec=0, msec=0, mcnt=0):
        self.ecuid = ecuid
        self.apid = apid
        self.ctid = ctid
        self.sid = sid
        self.payload = payload
        self.tmsp = tmsp
        self.mcnt = mcnt
        self.storageheader = MockStorageHeader(sec=sec, msec=msec)

    def compare(self, target):
        """Compare DLT Message to a dictionary"""
        return target == {k: v for k, v in self.__dict__.items() if k in target.keys()}

    @property
    def payload_decoded(self):
        """Fake payload decoding"""
        return self.payload

    @property
    def storage_timestamp(self):
        """Fake storage timestamp"""
        return float("{}.{}".format(self.storageheader.seconds, self.storageheader.microseconds))

    def __repr__(self):
        return str(self.__dict__)


class MockStorageHeader(object):
    """Mock DLT storage header for plugin testing"""

    def __init__(self, msec=0, sec=0):
        self.microseconds = msec
        self.seconds = sec
