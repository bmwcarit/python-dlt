# Copyright (C) 2015. BMW Car IT GmbH. All rights reserved.
"""Pure Python implementation of DLT library"""
# pylint: disable=too-many-lines
from __future__ import absolute_import

import ctypes
import ipaddress as ip
import logging
import os
import re
import socket
import struct
import time
import threading

import six

from dlt.core import (
    dltlib, DLT_CLIENT_MODE_UDP_MULTICAST, DLT_ID_SIZE, DLT_HTYP_WEID, DLT_HTYP_WSID, DLT_HTYP_WTMS,
    DLT_HTYP_UEH, DLT_RETURN_OK, DLT_RETURN_ERROR, DLT_RETURN_TRUE, DLT_FILTER_MAX, DLT_MESSAGE_ERROR_OK,
    cDltExtendedHeader, cDltClient, MessageMode, cDLTMessage, cDltStorageHeader, cDltStandardHeader,
    DLT_TYPE_INFO_UINT, DLT_TYPE_INFO_SINT, DLT_TYPE_INFO_STRG, DLT_TYPE_INFO_SCOD,
    DLT_TYPE_INFO_TYLE, DLT_TYPE_INFO_VARI, DLT_TYPE_INFO_RAWD,
    DLT_SCOD_ASCII, DLT_SCOD_UTF8, DLT_TYLE_8BIT, DLT_TYLE_16BIT, DLT_TYLE_32BIT, DLT_TYLE_64BIT,
    DLT_TYLE_128BIT, DLT_DAEMON_TCP_PORT, DLT_RECEIVE_BUFSIZE,
    DLT_RECEIVE_SOCKET,
)
from dlt.helpers import bytes_to_str

try:
    # Use xrange by default on Python 2
    range = xrange  # pylint: disable=redefined-builtin,undefined-variable,invalid-name
except Exception:  # pylint: disable=broad-except
    pass

MAX_LOG_IN_ROW = 3
# Return value for DLTFilter.add() - exceeded maximum number of filters
MAX_FILTER_REACHED = 1
# Return value for DLTFilter.add() - specified filter already exists
REPEATED_FILTER = 2
logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


DLT_EMPTY_FILE_ERROR = "DLT TRACE FILE IS EMPTY"
cDLT_FILE_NOT_OPEN_ERROR = "Could not open DLT Trace file (libdlt)"  # pylint: disable=invalid-name


class cached_property(object):  # pylint: disable=invalid-name
    """
    A property that is only computed once per instance and then replaces itself
    with an ordinary attribute. Deleting the attribute resets the property.
    Copyright: Marcel Hellkamp <marc@gsites.de>
    Source: https://github.com/bottlepy/bottle/commit/fa7733e075da0d790d809aa3d2f53071897e6f76
    Licence: MIT
    """  # noqa

    def __init__(self, func):
        self.__doc__ = getattr(func, '__doc__')
        self.func = func

    def __get__(self, obj, cls):
        if obj is None:
            return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


class DLTFilter(ctypes.Structure):
    """Structure to store filter parameters. ID are maximal four characters. Unused values are filled with zeros.
    If every value as filter is valid, the id should be empty by having only zero values.

    typedef struct
    {
        char apid[DLT_FILTER_MAX][DLT_ID_SIZE]; /**< application id */
        char ctid[DLT_FILTER_MAX][DLT_ID_SIZE]; /**< context id */
        int  counter;                           /**< number of filters */
    } DltFilter;
    """

    _fields_ = [("apid", (ctypes.c_char * DLT_ID_SIZE) * DLT_FILTER_MAX),
                ("ctid", (ctypes.c_char * DLT_ID_SIZE) * DLT_FILTER_MAX),
                ("counter", ctypes.c_int)]

    verbose = 0

    def __init__(self, **kwords):
        self.verbose = kwords.pop("verbose", 0)
        if dltlib.dlt_filter_init(ctypes.byref(self), self.verbose) == DLT_RETURN_ERROR:
            raise RuntimeError("Could not initialize DLTFilter")
        super(DLTFilter, self).__init__(**kwords)

    def __del__(self):
        if dltlib.dlt_filter_free(ctypes.byref(self), self.verbose) == DLT_RETURN_ERROR:
            raise RuntimeError("Could not cleanup DLTFilter")

    def add(self, apid, ctid):
        """Add new filter pair"""
        if six.PY3:
            if isinstance(apid, str):
                apid = bytes(apid, "ascii")
            if isinstance(ctid, str):
                ctid = bytes(ctid, "ascii")
        if dltlib.dlt_filter_add(ctypes.byref(self), apid or b"", ctid or b"", self.verbose) == DLT_RETURN_ERROR:
            if self.counter >= DLT_FILTER_MAX:
                logger.error("Maximum number (%d) of allowed filters reached, ignoring filter!\n", DLT_FILTER_MAX)
                return MAX_FILTER_REACHED
            logger.debug("Filter ('%s', '%s') already exists", apid, ctid)
            return REPEATED_FILTER
        return 0

    def __repr__(self):
        """return the 'official' string representation of an object"""
        apids = [ctypes.string_at(entry[:DLT_ID_SIZE]) for entry in self.apid]
        ctids = [ctypes.string_at(entry[:DLT_ID_SIZE]) for entry in self.ctid]

        return str(list(zip(apids[:self.counter], ctids[:self.counter])))

    def __nonzero__(self):
        """Truth value testing"""
        return self.counter > 0

    __bool__ = __nonzero__


class Payload(object):
    """Payload object encapsulates the payload decoding and list-like access to arguments"""

    def __init__(self, message):
        self._params = None
        self._noar = message.noar
        self._buf = ctypes.string_at(message.databuffer, message.datasize)

    def __getitem__(self, index):
        """Accessing the payload item as a list"""
        if index < 0 or index > self._noar:
            return IndexError()

        # we have parsed it already - just return the item
        if self._params is not None:
            return self._params[index]

        self._parse_payload()

        return self._params[index]

    def _parse_payload(self):  # pylint: disable=too-many-branches,too-many-statements
        """Parse the payload into list of arguments"""
        self._params = []

        offset = 0
        for _ in range(self._noar):
            type_info = struct.unpack_from("I", self._buf, offset)[0]
            offset += struct.calcsize("I")

            def get_scod(type_info):
                """Helper function"""
                return type_info & DLT_TYPE_INFO_SCOD

            value = None
            if type_info & DLT_TYPE_INFO_STRG:
                if (get_scod(type_info) == DLT_SCOD_ASCII) or (get_scod(type_info) == DLT_SCOD_UTF8):

                    length = struct.unpack_from("H", self._buf, offset)[0]
                    offset += struct.calcsize("H")
                    value = self._buf[offset:offset + length - 1]  # strip the string terminating char \x00
                    offset += length

            elif type_info & DLT_TYPE_INFO_UINT:

                if type_info & DLT_TYPE_INFO_VARI:
                    pass

                tyle = type_info & DLT_TYPE_INFO_TYLE
                if tyle == DLT_TYLE_8BIT:
                    value = struct.unpack_from("B", self._buf, offset)[0]
                    offset += 1
                elif tyle == DLT_TYLE_16BIT:
                    value = struct.unpack_from("H", self._buf, offset)[0]
                    offset += 2
                elif tyle == DLT_TYLE_32BIT:
                    value = struct.unpack_from("I", self._buf, offset)[0]
                    offset += 4
                elif tyle == DLT_TYLE_64BIT:
                    value = struct.unpack_from("Q", self._buf, offset)[0]
                    offset += 8
                elif tyle == DLT_TYLE_128BIT:
                    raise TypeError("reading 128BIT values not supported")

            elif type_info & DLT_TYPE_INFO_SINT:

                if type_info & DLT_TYPE_INFO_VARI:
                    pass

                tyle = type_info & DLT_TYPE_INFO_TYLE
                if tyle == DLT_TYLE_8BIT:
                    value = struct.unpack_from("b", self._buf, offset)[0]
                    offset += 1
                elif tyle == DLT_TYLE_16BIT:
                    value = struct.unpack_from("h", self._buf, offset)[0]
                    offset += 2
                elif tyle == DLT_TYLE_32BIT:
                    value = struct.unpack_from("i", self._buf, offset)[0]
                    offset += 4
                elif tyle == DLT_TYLE_64BIT:
                    value = struct.unpack_from("q", self._buf, offset)[0]
                    offset += 8
                elif tyle == DLT_TYLE_128BIT:
                    raise TypeError("reading 128BIT values not supported")

            elif type_info & DLT_TYPE_INFO_RAWD:

                if type_info & DLT_TYPE_INFO_VARI:
                    pass

                length = struct.unpack_from("H", self._buf, offset)[0]
                offset += struct.calcsize("H")

                value = self._buf[offset:offset + length]
                offset += length

            else:
                value = "ERROR"

            self._params.append(value)

    def __len__(self):
        """Return number of parsed parameters"""
        if self._params is None:
            self._parse_payload()

        return len(self._params)


class DLTMessage(cDLTMessage, MessageMode):
    """Python wrapper class for the cDLTMessage structure"""

    verbose = 0

    # object is not initialized if the message is loaded from a file
    initialized_as_object = False

    def __init__(self, *args, **kwords):
        self.initialized_as_object = True
        self.verbose = kwords.pop("verbose", 0)
        if self.verbose:
            logger.debug("DLTMessage._init_(%s)", kwords)
        self.lifecycle = None

        if dltlib.dlt_message_init(ctypes.byref(self), self.verbose) == DLT_RETURN_ERROR:
            raise RuntimeError("Could not initialize DLTMessage")

        super(DLTMessage, self).__init__(*args, **kwords)

    def __reduce__(self):
        """Pickle serialization API

        This method is called by the pickle module to serialize objects
        that it cannot automatically serialize.
        """
        # copy the data from the databuffer pointer into an array
        databuffer = ctypes.ARRAY(ctypes.c_uint8, self.datasize)()
        ctypes.memmove(databuffer, self.databuffer, self.datasize)

        init_args = (self.found_serialheader, self.resync_offset, self.headersize, self.datasize)
        state_dict = {'headerbuffer': bytearray(self.headerbuffer),
                      'databuffer': bytearray(databuffer),
                      'databuffersize': self.databuffersize,
                      'storageheader': self.storageheader,
                      'standardheader': self.standardheader,
                      'headerextra': self.headerextra,
                      'extendedheader': self.extendedheader, }
        return (DLTMessage, init_args, state_dict)

    # pylint: disable=attribute-defined-outside-init
    def __setstate__(self, state):
        """Pickle deserialization API

        This method is called by the pickle module to populate a
        deserialized object's state after it has been created.
        """
        self.databuffersize = state['databuffersize']
        self.p_storageheader.contents = state['storageheader']
        self.p_standardheader.contents = state['standardheader']
        self.headerextra = state['headerextra']
        self.p_extendedheader.contents = state['extendedheader']
        # - populate databuffer
        databuffer = ctypes.ARRAY(ctypes.c_uint8, self.datasize)()
        for index, byte in enumerate(state['databuffer']):
            databuffer[index] = byte
        self.databuffer = databuffer

        # - populate headerbuffer
        for index, byte in enumerate(state['headerbuffer']):
            self.headerbuffer[index] = byte

        # - This is required because we are not calling
        # dlt_message_init() so we do not need to call
        # dlt_message_free()
        self.initialized_as_object = False

    @staticmethod
    def from_bytes(data):
        """Create a class instance from a byte string in DLT storage format"""

        msg = DLTMessage()
        storageheader, remainder = msg.extract_storageheader(data)

        buf = ctypes.create_string_buffer(remainder)

        dltlib.dlt_message_read(ctypes.byref(msg),
                                ctypes.cast(buf, ctypes.POINTER(ctypes.c_uint8)),
                                ctypes.c_uint(len(remainder)),
                                0,  # resync
                                0)  # verbose
        msg.p_storageheader.contents = storageheader
        msg.initialized_as_object = False

        return msg

    def to_bytes(self):
        """Create DLT storage format bytes from DLTMessage instance"""
        return ctypes.string_at(self.headerbuffer, self.headersize) + ctypes.string_at(self.databuffer, self.datasize)

    def __copy__(self):
        """Create a copy of the message"""
        return DLTMessage.from_bytes(self.to_bytes())

    @staticmethod
    def extract_storageheader(data):
        """Split binary message data into storage header and remainder"""
        header = data[0:ctypes.sizeof(cDltStorageHeader)]
        # pylint: disable=no-member
        return (cDltStorageHeader.from_buffer_copy(header), data[ctypes.sizeof(cDltStorageHeader):])

    @staticmethod
    def extract_sort_data(data):
        """Extract timestamp, message length, apid, ctid from a bytestring in DLT storage format (speed optimized)"""
        htyp_data = ord(chr(data[16])) if six.PY3 else ord(data[16])
        len_data = data[19:17:-1]
        len_value = ctypes.cast(len_data, ctypes.POINTER(ctypes.c_ushort)).contents.value + 16
        apid = b""
        ctid = b""
        tmsp_value = 0.0

        bytes_offset = 0    # We know where data will be in the message, but ...
        if not htyp_data & DLT_HTYP_WEID:  # if there is no ECU ID and/or Session ID, then it will be earlier
            bytes_offset -= 4
        if not htyp_data & DLT_HTYP_WSID:
            bytes_offset -= 4

        if htyp_data & DLT_HTYP_WTMS:
            tmsp_base = 31 + bytes_offset  # Typical timestamp end offset
            tmsp_data = data[tmsp_base:tmsp_base - 4:-1]
            tmsp_value = ctypes.cast(tmsp_data, ctypes.POINTER(ctypes.c_uint32)).contents.value / 10000.0

        if htyp_data & DLT_HTYP_UEH:
            apid_base = 38 + bytes_offset  # Typical APID end offset
            apid = data[apid_base - 4:apid_base].rstrip(b"\x00")
            ctid = data[apid_base:apid_base + 4].rstrip(b"\x00")

        apid = bytes_to_str(apid)
        ctid = bytes_to_str(ctid)

        return tmsp_value, len_value, apid, ctid

    def __del__(self):
        if self.initialized_as_object is True:
            if dltlib.dlt_message_free(ctypes.byref(self), self.verbose) == DLT_RETURN_ERROR:
                raise RuntimeError("Could not free DLTMessage")

    @property
    def storageheader(self):
        """Workaround to get rid of need to call .contents"""
        try:
            return self.p_storageheader.contents
        except ValueError:
            return None

    @property
    def standardheader(self):
        """Workaround to get rid of need to call .contents"""
        return self.p_standardheader.contents

    @property
    def extendedheader(self):
        """Workaround to get rid of need to call .contents"""
        try:
            return self.p_extendedheader.contents
        except ValueError:
            return None

    def __eq__(self, other):
        """Equal test - not comparing storage header (contains timestamps)"""
        header1 = ctypes.string_at(self.headerbuffer, self.headersize)[ctypes.sizeof(cDltStorageHeader):]
        header2 = ctypes.string_at(other.headerbuffer, other.headersize)[ctypes.sizeof(cDltStorageHeader):]

        data1 = ctypes.string_at(self.databuffer, self.datasize)
        data2 = ctypes.string_at(other.databuffer, other.datasize)

        return header1 == header2 and data1 == data2

    def compare(self, other=None):  # pylint: disable=too-many-return-statements,too-many-branches
        """Compare messages by given attributes

        :param [DLTMessage|DLTFilter|dict] other: DLTMessage object (or DLTFilter or a dict with selected keys)
            to compare with. Use DLTFilter object with APID,CTID pairs for the best performance.
        :returns: True if all attributes match or False if any of the given attributes differs
        :rtype: bool
        :raises TypeError: if other is neither DLTMessage nor a dictionary

        Example:
        message.compare(other=message2)
        message.compare(message2)
        message.compare(other=dict(apid="AP1", ctid="CT1"))
        message.compare(dict(apid="AP1", ctid="CT1"))
        message.compare(dict(apid=re.compile(r"^A.*"))  # match all messages which apid starting with A
        message.compare(dict(apid="AP1", ctid="CT1", payload_decoded=re.compile(r".connected.*")))
        """
        if hasattr(other, "apid") and hasattr(other, "ctid") and hasattr(other, "payload_decoded"):
            # other is DLTMessage - full compare
            return self.apid == other.apid and self.ctid == other.ctid and self.__eq__(other)

        # pylint: disable=protected-access
        if hasattr(other, "_fields_") and [x[0] for x in other._fields_] == ["apid", "ctid", "counter"]:
            # other id DLTFilter
            return dltlib.dlt_message_filter_check(ctypes.byref(self), ctypes.byref(other), 0)

        if not isinstance(other, dict):
            raise TypeError("other must be instance of mgu_dlt.dlt.DLTMessage, mgu_dlt.dlt.DLTFilter or a dictionary"
                            " found: {}".format(type(other)))

        re_pattern_type = type(re.compile(r"type"))

        other = other.copy()
        apid = other.get("apid", None)
        if apid and not isinstance(apid, re_pattern_type) and self.apid != apid:
            return False

        ctid = other.get("ctid", None)
        if ctid and not isinstance(ctid, re_pattern_type) and self.ctid != ctid:
            return False

        for key, val in other.items():
            if val is None:
                continue
            key = key.rsplit(".", 1)[-1]  # In case the obsolete "extendedheader.apid" notation is used
            msg_val = getattr(self, key, b"")
            if not msg_val:
                return False
            if isinstance(val, re_pattern_type):
                if not val.search(msg_val):
                    return False
            elif msg_val != val:
                return False
        return True

    def __str__(self):
        """Construct DLTViewer-like string"""
        out = [time.asctime(time.gmtime(self.storage_timestamp))]
        if self.headerextra:
            out.append(self.headerextra.tmsp / 10000.0)
        out += [self.standardheader.mcnt, self.storageheader.ecu]
        if self.extendedheader:
            out += [self.extendedheader.apid, self.extendedheader.ctid]
        if self.headerextra:
            out.append(self.headerextra.seid)
        out += [self.type_string, self.subtype_string, self.mode_string, self.noar, self.payload_decoded]
        return " ".join(bytes_to_str(item) for item in out)

    # convenient access to import DLT message attributes
    # no need to remember in which header are those attrs defined
    @cached_property
    def ecuid(self):   # pylint: disable=invalid-overridden-method
        """Get the ECU ID

        :returns: ECU ID
        :rtype: str
        """
        return bytes_to_str(self.storageheader.ecu or self.headerextra.ecu)

    @cached_property
    def mcnt(self):  # pylint: disable=invalid-overridden-method
        """Get the message counter index

        :returns: message index
        :rtype: int
        """
        return int(self.standardheader.mcnt)

    @cached_property
    def seid(self):  # pylint: disable=invalid-overridden-method
        """Get the Session ID if WSID is set in the message type, otherwise 0

        :returns: Session ID
        :rtype: int
        """
        return int(self.headerextra.seid) if (self.standardheader.htyp & DLT_HTYP_WSID) else 0

    @cached_property
    def tmsp(self):  # pylint: disable=invalid-overridden-method
        """Get the timestamp

        :returns: timestamp
        :rtype: float [s]
        """
        return (self.headerextra.tmsp / 10000.0) if (self.standardheader.htyp & DLT_HTYP_WTMS) else 0

    @cached_property
    def apid(self):  # pylint: disable=invalid-overridden-method
        """Get the Application ID

        :returns: Application ID
        :rtype: str
        """
        return bytes_to_str(self.extendedheader.apid if self.extendedheader else "")

    @cached_property
    def ctid(self):  # pylint: disable=invalid-overridden-method
        """Get the Context ID

        :returns: Context ID
        :rtype: str
        """
        return bytes_to_str(self.extendedheader.ctid if self.extendedheader else "")

    @cached_property
    def noar(self):  # pylint: disable=invalid-overridden-method
        """Get the number of arguments

        :returns: Context ID
        :rtype: str
        """
        if self.use_extended_header and self.is_mode_verbose:
            return self.extendedheader.noar
        return 0

    @cached_property
    def payload(self):  # pylint: disable=invalid-overridden-method
        """Get the payload object

        :returns: Payload object
        :rtype: Payload
        """
        return Payload(self)

    @cached_property
    def payload_decoded(self):  # pylint: disable=invalid-overridden-method
        """Get the payload string

        :returns: Payload string
        :rtype: str
        """
        return bytes_to_str(super(DLTMessage, self).payload_decoded)

    @cached_property
    def storage_timestamp(self):  # pylint: disable=invalid-overridden-method
        """Get the storage header timestamp in seconds

        :returns: storage header timestamp
        :rtype: float
        """
        return float("{}.{}".format(self.storageheader.seconds, self.storageheader.microseconds))


class cDLTFile(ctypes.Structure):  # pylint: disable=invalid-name
    """The structure to organise the access to DLT files. This structure is used by the corresponding functions.

    typedef struct sDltFile
    {
        /* file handle and index for fast access */
        FILE *handle;      /**< file handle of opened DLT file */
        long *index;       /**< file positions of all DLT messages for fast access to file, only filtered messages */

        /* size parameters */
        int32_t counter;       /**< number of messages in DLT file with filter */
        int32_t counter_total; /**< number of messages in DLT file without filter */
        int32_t position;      /**< current index to message parsed in DLT file starting at 0 */
        long file_length;  /**< length of the file */
        long file_position; /**< current position in the file */

        /* error counters */
        int32_t error_messages; /**< number of incomplete DLT messages found during file parsing */

        /* filter parameters */
        DltFilter *filter;  /**< pointer to filter list. Zero if no filter is set. */
        int32_t filter_counter; /**< number of filter set */

        /* current loaded message */
        DltMessage msg;     /**< pointer to message */

    } DltFile;
    """

    _fields_ = [("handle", ctypes.POINTER(ctypes.c_int)),
                ("index", ctypes.POINTER(ctypes.c_long)),
                ("counter", ctypes.c_int32),
                ("counter_total", ctypes.c_int32),
                ("position", ctypes.c_int32),
                ("file_length", ctypes.c_long),
                ("file_position", ctypes.c_long),
                ("error_messages", ctypes.c_int32),
                ("filter", ctypes.POINTER(DLTFilter)),
                ("filter_counter", ctypes.c_int32),
                ("msg", DLTMessage)]

    def __init__(self, **kwords):
        self.verbose = kwords.pop("verbose", 0)
        self.filename = kwords.pop("filename", None)
        if six.PY3 and isinstance(self.filename, str):
            self.filename = bytes(self.filename, "utf-8")
        super(cDLTFile, self).__init__(**kwords)
        if dltlib.dlt_file_init(ctypes.byref(self), self.verbose) == DLT_RETURN_ERROR:
            raise RuntimeError("Could not initialize DLTFile")
        self._iter_index = 0
        self.corrupt_msg_count = 0

        self.indexed = False
        self.end = False
        self.live_run = kwords.pop("is_live", False)
        self.stop_reading = threading.Event()

    def __repr__(self):
        # pylint: disable=bad-continuation
        return '<DLTFile object {} with {} messages>'.format(
            "filename={}".format(self.filename) if self.filename else "",
            self.counter_total)

    def __del__(self):
        if dltlib.dlt_file_free(ctypes.byref(self), self.verbose) == DLT_RETURN_ERROR:
            raise RuntimeError("Could not cleanup DLTFile")

    def _find_next_header(self):
        """Helper function for generate_index to skip over invalid storage headers.

        :returns: Offset to the next storage header position (after
                  self.file_position), if it was found, or position of EOF if not
        :rtype: int
        """
        with open(self.filename, "rb") as fobj:
            last_position = self.file_position   # pylint: disable=access-member-before-definition
            fobj.seek(last_position)
            buf = fobj.read(1024)
            while buf:
                found = buf.find(b"DLT\x01")
                if found != -1:
                    return last_position + found
                last_position = fobj.tell()
                buf = fobj.read(1024)
        return None

    # pylint: disable=attribute-defined-outside-init,access-member-before-definition
    def generate_index(self):
        """Generate an index for the loaded DLT file

        :returns: True if file had been previously read and the index is
                  successfully generated, otherwise False
        :rtype: bool
        """
        if not self.filename:
            return False

        self.indexed = False
        if dltlib.dlt_file_open(ctypes.byref(self), self.filename, self.verbose) >= DLT_RETURN_OK:
            # load, analyse data file and create index list
            if self.file_length == 0:
                raise IOError(DLT_EMPTY_FILE_ERROR)
            while self.file_position < self.file_length:
                ret = dltlib.dlt_file_read(ctypes.byref(self), self.verbose)
                if ret < DLT_RETURN_OK:
                    # - This can happen if either the frame's storage
                    # header could not be read correctly or the frame is
                    # corrupt. If the frame's storage header could not
                    # be read correctly we try to get the next storage
                    # header and continue indexing
                    next_header_position = self._find_next_header()
                    if next_header_position:
                        if self.file_position == next_header_position:  # pylint: disable=no-else-break
                            # - This this implies that dltlib.dlt_read_file()
                            # returned due to an error other than invalid storage
                            # header because we already were at the correct
                            # header_position in the last iteration. So, we
                            # need to break out of the read/index loop.
                            break
                        else:
                            self.file_position = next_header_position
                            self.corrupt_msg_count += 1
                    else:
                        break
            self.indexed = True
        else:
            raise IOError(cDLT_FILE_NOT_OPEN_ERROR)
        return self.indexed

    def read(self, filename, filters=None):
        """Index the DLT trace file for optimized DLT Message access

        :param str filename: DLT log filename to read the messages from
        :param list filters: List of filters to apply [("APPID", "CTID"), ...]
        :returns: True if file was read and indexed successfully, otherwise False
        :rtype: bool
        """
        # load the filters
        self.set_filters(filters)

        if six.PY3 and isinstance(filename, str):
            filename = bytes(filename, "utf-8")
        # read and index file
        self.filename = filename
        self.generate_index()
        return self.indexed

    def set_filters(self, filters):
        """Set filters to optimize access"""
        if filters is not None:
            dlt_filter = DLTFilter(verbose=self.verbose)
            for apid, ctid in filters:
                if six.PY3:
                    if isinstance(apid, str):
                        apid = bytes(apid, "ascii")
                    if isinstance(ctid, str):
                        ctid = bytes(ctid, "ascii")
                dlt_filter.add(apid, ctid)
            self.filters = dlt_filter
            dltlib.dlt_file_set_filter(ctypes.byref(self), ctypes.byref(dlt_filter), self.verbose)

    def __getitem__(self, index):
        """Load a DLT message from opened file

        :param int index: Index of a message to load
        :returns: Loaded DLTMessage
        :rtype: DLTMessage object
        :raises IndexError: If message index is out of boundary
        """
        if index < 0:
            if self.counter == 0:
                self.read(self.filename)
            index = self.counter + index

        if index == 0 and self.counter == 0:
            self.read(self.filename)

        if index < 0 or index >= self.counter:
            raise IndexError("Index out of range (0 < %d < %d)" % (index, self.counter))

        dltlib.dlt_file_message(ctypes.byref(self), index, self.verbose)
        # deepcopy the object
        msg = DLTMessage.from_buffer_copy(self.msg)  # pylint: disable=no-member
        msg.databuffer.contents = ctypes.create_string_buffer(self.msg.datasize)
        ctypes.memmove(msg.databuffer, self.msg.databuffer, msg.datasize)

        # set the new storage header pointer
        offset = 0
        hdr = cDltStorageHeader.from_address(ctypes.addressof(msg.headerbuffer) + offset)  # pylint: disable=no-member
        msg.p_storageheader = ctypes.pointer(hdr)

        # set the new standard header pointer
        offset = ctypes.sizeof(cDltStorageHeader)
        hdr = cDltStandardHeader.from_address(ctypes.addressof(msg.headerbuffer) + offset)  # pylint: disable=no-member
        msg.p_standardheader = ctypes.pointer(hdr)
        # set the new extended header pointer
        if self.msg.use_extended_header:
            offset = ctypes.addressof(self.msg.p_extendedheader.contents) - ctypes.addressof(self.msg.headerbuffer)
            # pylint: disable=no-member
            hdr = cDltExtendedHeader.from_address(ctypes.addressof(msg.headerbuffer) + offset)
            msg.p_extendedheader = ctypes.pointer(hdr)

        return msg

    def _open_file(self):
        """Open the configured file for processing"""
        file_opened = False
        while not self.stop_reading.isSet():
            if dltlib.dlt_file_open(ctypes.byref(self), self.filename, self.verbose) >= DLT_RETURN_OK:
                file_opened = True
                break
            if not self.live_run:
                break
            time.sleep(0.5)

        if not file_opened:
            logger.error("DLT FILE OPEN FAILED - Analysis will not be performed")
            raise IOError(cDLT_FILE_NOT_OPEN_ERROR)

    def _log_message_progress(self):
        """Logs current message for progress information"""
        length = os.stat(self.filename).st_size
        logger.debug(
            "Processed %s messages (%s%% of %sfile), next message is apid %s, ctid %s",
            self.position,
            int(100 * self.file_position / length),
            "live " if self.live_run else "",
            self.msg.apid,
            self.msg.ctid,
        )

    def __iter__(self):  # pylint: disable=too-many-branches
        """Iterate over messages in the file"""
        logger.debug("Starting File Read")
        logger.debug("File Position: %d File Counter: %d File Name: %s",
                     self.file_position, self.counter, self.filename)
        cached_mtime = 0
        cached_file_pos = 0
        corruption_check_try = True

        self._open_file()

        found_data = False
        while not self.stop_reading.isSet() or corruption_check_try:  # pylint: disable=too-many-nested-blocks
            os_stat = os.stat(self.filename)
            mtime = os_stat.st_mtime

            if mtime != cached_mtime and os_stat.st_size or corruption_check_try:
                cached_mtime = mtime
                corruption_check_try = False

                while dltlib.dlt_file_read(ctypes.byref(self), self.verbose) >= DLT_RETURN_OK:
                    found_data = True
                    if self.filter and dltlib.dlt_message_filter_check(
                            ctypes.byref(self.msg), self.filter, 0) != DLT_RETURN_TRUE:
                        continue

                    index = self.position
                    msg = self[index]
                    if not index % 100000:
                        self._log_message_progress()
                    yield msg

                if cached_file_pos != self.file_position:
                    # We were able to read messages, don't do a corrupt message check yet.
                    corruption_check_try = True
                    cached_file_pos = self.file_position
                else:
                    next_header_position = self._find_next_header()
                    if next_header_position:
                        if self.file_position == next_header_position:
                            if not self.live_run:
                                logger.warning("Incomplete message while parsing DLT file at %s", self.file_position)
                                break
                        else:
                            logger.warning("Found a corrupt message at %s, skipping it", self.file_position)
                            self.file_position = next_header_position
                            self.corrupt_msg_count += 1
                            corruption_check_try = True
                    # Wait for further messages to determine if corrupt, else just end of file
                    else:
                        if not self.live_run:
                            logger.info("End of file reached at %s", self.file_position)
                            break

            time.sleep(0.1)

        if not found_data:
            raise IOError(DLT_EMPTY_FILE_ERROR)

    def __len__(self):
        """Returns filtered file length"""
        return self.counter


class DLTClient(cDltClient):
    """DLTClient class takes care about correct initialization and
    cleanup"""

    verbose = 0

    def __init__(self, **kwords):
        self.is_udp_multicast = False
        self.verbose = kwords.pop("verbose", 0)
        if dltlib.dlt_client_init(ctypes.byref(self), self.verbose) == DLT_RETURN_ERROR:
            raise RuntimeError("Could not initialize DLTClient")

        if "servIP" in kwords:
            serv_ip = kwords.pop("servIP")
            if isinstance(serv_ip, str):
                serv_ip = serv_ip.encode('utf8')
            ip_init_state = dltlib.dlt_client_set_server_ip(ctypes.byref(self), ctypes.create_string_buffer(serv_ip))
            if ip_init_state == DLT_RETURN_ERROR:
                raise RuntimeError("Could not initialize servIP for DLTClient")

            if ip.ip_address(serv_ip.decode("utf8")).is_multicast:
                self.is_udp_multicast = True
                if "hostIP" in kwords:
                    host_ip = kwords.pop("hostIP")
                    if isinstance(host_ip, str):
                        host_ip = host_ip.encode('utf8')
                    ip_init_state = dltlib.dlt_client_set_host_if_address(
                        ctypes.byref(self),
                        ctypes.create_string_buffer(host_ip)
                    )
                    if ip_init_state == DLT_RETURN_ERROR:
                        raise RuntimeError("Could not initialize multicast address for DLTClient")

                set_mode_state = dltlib.dlt_client_set_mode(ctypes.byref(self),
                                                            DLT_CLIENT_MODE_UDP_MULTICAST)

                if set_mode_state == DLT_RETURN_ERROR:
                    raise RuntimeError("Could not initialize socket mode for DLTClient")

        # attribute to hold a reference to the connected socket in case
        # we created a connection with a timeout (via python, as opposed
        # to dltlib). This avoids the socket object from being garbage
        # collected when it goes out of the connect() method scope
        self._connected_socket = None

        super(DLTClient, self).__init__(**kwords)

        # (re)set self.port, even for API version <2.16.0 since we use
        # it ourselves elsewhere
        self.port = kwords.get("port", DLT_DAEMON_TCP_PORT)

    def __del__(self):
        if dltlib.dlt_client_cleanup(ctypes.byref(self), self.verbose) == DLT_RETURN_ERROR:
            raise RuntimeError("Could not cleanup DLTClient")
        self.disconnect()

    def ready_to_read(self):
        if not self.is_udp_multicast:
            try:
                ready_to_read = self._connected_socket.recv(1, socket.MSG_PEEK | socket.MSG_DONTWAIT)
            except OSError as os_exc:
                logger.error("[%s]: DLTLib closed connected socket", os_exc)
                return DLT_RETURN_ERROR

            if not ready_to_read:
                # - implies that the other end has called close()/shutdown()
                # (ie: clean disconnect)
                logger.debug("connection terminated, returning")
                return DLT_RETURN_ERROR
        return DLT_RETURN_OK

    def connect(self, timeout=None, receiver_type=DLT_RECEIVE_SOCKET):
        """Connect to the server

        If timeout is provided, block on connect until timeout occurs. If
        timeout is not provided or is None, try to connect and return
        immediately

        :param int|None timeout: Seconds to wait for connection
        :returns: True if connected successfully, False otherwise
        :rtype: bool
        """
        connected = None
        error_count = 0
        if not self.is_udp_multicast:
            if timeout:
                end_time = time.time() + timeout
                while time.time() < end_time:
                    timeout_remaining = max(end_time - time.time(), 1) if timeout else None
                    try:
                        self._connected_socket = socket.create_connection((ctypes.string_at(self.servIP), self.port),
                                                                          timeout=timeout_remaining)
                    except IOError as exc:
                        if error_count < MAX_LOG_IN_ROW:
                            logger.debug("DLT client connect failed to connect to %s:%s : %s",
                                         self.servIP, self.port, exc)
                        error_count += 1
                        time.sleep(1)

                    if self._connected_socket:
                        # pylint: disable=attribute-defined-outside-init
                        self.sock = ctypes.c_int(self._connected_socket.fileno())
                        # - also init the receiver to replicate
                        # dlt_client_connect() behavior
                        connected = dltlib.dlt_receiver_init(ctypes.byref(self.receiver),
                                                             self.sock,
                                                             receiver_type,
                                                             DLT_RECEIVE_BUFSIZE)
                        if connected == DLT_RETURN_OK:
                            connected = self.ready_to_read()
                        break
            else:
                connected = dltlib.dlt_client_connect(ctypes.byref(self), self.verbose)
                # - create a python socket object so that we can detect
                # connection loss in the main_loop below as described at
                # http://stefan.buettcher.org/cs/conn_closed.html
                self._connected_socket = socket.fromfd(self.sock, socket.AF_INET6, socket.SOCK_STREAM)
            if error_count > MAX_LOG_IN_ROW:
                logger.debug("Surpressed %d messages for failed connection attempts", error_count - MAX_LOG_IN_ROW)

        else:
            connected = dltlib.dlt_client_connect(ctypes.byref(self), self.verbose)

        return connected == DLT_RETURN_OK

    def disconnect(self):
        """Close all sockets"""
        if self._connected_socket:
            try:
                self._connected_socket.shutdown(socket.SHUT_RDWR)
            except IOError:
                pass
            except Exception:  # pylint: disable=broad-except
                logger.exception("Unexpected exception while shutting down connection")
            try:
                self._connected_socket.close()
            except IOError:
                pass
            except Exception:  # pylint: disable=broad-except
                logger.exception("Unexpected exception while disconnecting")

    def read_message(self, verbose=False):
        """Read new message

        :param bool verbose: Log every dlt_message_read(). Set True only for debugging.
        :returns: A new DLTMessage on successful read, None otherwise
        :rtype: DLTMessage|None
        """
        msg = DLTMessage(verbose=verbose)
        res = dltlib.dlt_message_read(ctypes.byref(msg),
                                      ctypes.cast(self.receiver.buf, ctypes.POINTER(ctypes.c_uint8)),
                                      ctypes.c_uint(self.receiver.bytesRcvd),  # length
                                      ctypes.c_int(0),  # resync
                                      ctypes.c_int(verbose))  # verbose

        if res != DLT_MESSAGE_ERROR_OK:
            # - failed to read a complete message, possibly read an incomplete
            # message
            return None

        # prepare storage header
        if msg.standardheader.htyp & DLT_HTYP_WEID:
            dltlib.dlt_set_storageheader(msg.p_storageheader, msg.headerextra.ecu)
        else:
            dltlib.dlt_set_storageheader(msg.p_storageheader, ctypes.c_char_p(""))

        return msg

    # NEW_API - ensure backwards compatibility
    @property
    def serial_mode(self):
        """Get the mode"""
        return getattr(self, "mode", getattr(super(DLTClient, self), "serial_mode", 0))

    @ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(DLTMessage), ctypes.c_void_p)
    def msg_callback(msg, data):  # pylint: disable=no-self-argument
        """Implements a simple callback that prints a dlt message received"""
        if msg is None:
            print("NULL message in callback")
            return -1
        if msg.contents.p_standardheader.contents.htyp & DLT_HTYP_WEID:
            dltlib.dlt_set_storageheader(msg.contents.p_storageheader, msg.contents.headerextra.ecu)
        else:
            dltlib.dlt_set_storageheader(msg.contents.p_storageheader, ctypes.c_char_p(""))

        print(msg.contents)
        return 0

    def client_loop(self):
        """Executes native dlt_client_main_loop() after registering msg_callback method as callback"""
        dltlib.dlt_client_register_message_callback(self.msg_callback)
        dltlib.dlt_client_main_loop(ctypes.byref(self), None, self.verbose)


# pylint: disable=too-many-arguments,too-many-return-statements,too-many-branches
def py_dlt_client_main_loop(client, limit=None, verbose=0, dumpfile=None, callback=None):
    """Reimplementation of dlt_client.c:dlt_client_main_loop() in order to handle callback
    function return value"""
    bad_messages = 0
    while True:
        if bad_messages > 100:
            # Some bad data is coming in and we can not recover - raise an error to cause a reconnect
            logger.warning("Dropping connection due to multiple malformed messages")
            return False
        # check connection status by peeking on the socket for data.
        # Note that if the remote connection is abruptly terminated,
        # this will raise a socket.timeout exception which the caller is
        # expected to handle (possibly by attempting a reconnect)
        # pylint: disable=protected-access
        if client.ready_to_read() != DLT_RETURN_OK:
            return False

        # - check if stop flag has been set (end of loop)
        if callback and not callback(None):
            logger.debug("callback returned 'False'. Stopping main loop")
            return False

        # we now have data to read. Note that dlt_receiver_receive()
        # is a blocking call that only returns if there is data to be
        # read or the remote end closes connection. So, irrespective of
        # the status of the callback (in the case of dlt_broker, this is
        # the stop_flag Event), this loop will only proceed after the
        # function has returned or terminate when an exception is raised
        recv_size = dltlib.dlt_receiver_receive(ctypes.byref(client.receiver))
        if recv_size <= 0:
            logger.error("Error while reading from socket")
            return False

        msg = client.read_message(verbose)
        while msg:
            try:
                if msg.apid == b"" and msg.ctid == b"":
                    logger.debug("Received a corrupt message")
                    bad_messages += 1
            except AttributeError:
                logger.debug("Skipping a very corrupted message")
                bad_messages += 1
                msg = client.read_message()
                continue

            bad_messages = 0
            # save the message
            if dumpfile:
                dumpfile.write(msg.to_bytes())

            # remove message from receiver buffer
            size = msg.headersize + msg.datasize - ctypes.sizeof(cDltStorageHeader)
            if msg.found_serialheader:
                size += DLT_ID_SIZE

            if dltlib.dlt_receiver_remove(ctypes.byref(client.receiver), size) < 0:
                logger.error("dlt_receiver_remove failed")
                return False

            # send the message to the callback and check whether we
            # need to continue
            if callback and not callback(msg):
                logger.debug("callback returned 'False'. Stopping main loop")
                break

            if limit is not None:
                limit -= 1
                if limit == 0:
                    break

            # read the next message
            msg = client.read_message()
        else:
            # - failed to read a complete message, rewind the client
            # receiver buffer pointer to start of the buffer
            if dltlib.dlt_receiver_move_to_begin(ctypes.byref(client.receiver)) == DLT_RETURN_ERROR:
                logger.error("dlt_receiver_move_to_begin failed")
                return False

        # Check if we need to keep going
        if callback and not callback(msg):
            logger.debug("callback returned 'False'. Stopping main loop")
            break

    return True


def save(messages, filename, append=False):
    """Save DLT messages to a file

    :param list messages: List of messages to save
    :param str filename: Filename for the DLT log file the messages will be stored to
    :param bool append: New data will be appended to an existing file if set to True
    """
    with open(filename, "ab" if append else "wb") as tracefile:
        for msg in messages:
            tracefile.write(msg.to_bytes())


def load(filename, filters=None, split=False, verbose=False, live_run=False):
    """Load DLT messages from a file

    :param str filename: Filename for the DLT log file the messages will be store to
    :param list filters: List of filters to apply [("APPID", "CTID"), ...]
    :param bool split: Ignored - compatibility option
    :param bool verbose: Be verbose
    :returns: A DLTFile object
    :rtype: DLTFile object
    """
    cfile = cDLTFile(filename=filename, is_live=live_run)
    cfile.set_filters(filters)
    return cfile
