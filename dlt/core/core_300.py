# Copyright (C) 2024. All rights reserved.
"""v3.0.0 specific class definitions"""

import ctypes
import logging

from dlt.core.core_base import (
    dltlib,
    cDltStorageHeader,
    cDltStandardHeader,
    cDltStandardHeaderExtra,
    cDltExtendedHeader,
)

# ruff: noqa: F401
from dlt.core.core_21810 import (
    DLT_CLIENT_MODE_UNDEFINED,
    DLT_CLIENT_MODE_TCP,
    DLT_CLIENT_MODE_SERIAL,
    DLT_CLIENT_MODE_UNIX,
    DLT_CLIENT_MODE_UDP_MULTICAST,
    DLT_RECEIVE_SOCKET,
    DLT_RECEIVE_UDP_SOCKET,
    DLT_RECEIVE_FD,
    DLT_ID_SIZE,
    DLT_FILTER_MAX,
    DLT_RETURN_ERROR,
    MAX_FILTER_REACHED,
    REPEATED_FILTER,
    sockaddr_in,
    cDltReceiver,
)

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class cDLTMessage(ctypes.Structure):
    """The structure of the DLT messages. Packed in v3."""

    _fields_ = [
        ("found_serialheader", ctypes.c_int8),
        ("resync_offset", ctypes.c_int32),
        ("headersize", ctypes.c_int32),
        ("datasize", ctypes.c_int32),
        (
            "headerbuffer",
            ctypes.c_uint8
            * (
                ctypes.sizeof(cDltStorageHeader)
                + ctypes.sizeof(cDltStandardHeader)
                + ctypes.sizeof(cDltStandardHeaderExtra)
                + ctypes.sizeof(cDltExtendedHeader)
            ),
        ),
        ("databuffer", ctypes.POINTER(ctypes.c_uint8)),
        ("databuffersize", ctypes.c_uint32),
        ("p_storageheader", ctypes.POINTER(cDltStorageHeader)),
        ("p_standardheader", ctypes.POINTER(cDltStandardHeader)),
        ("headerextra", cDltStandardHeaderExtra),
        ("p_extendedheader", ctypes.POINTER(cDltExtendedHeader)),
    ]
    _pack_ = 1


class cDltClient(ctypes.Structure):  # pylint: disable=invalid-name
    """
    typedef struct
    {
        DltReceiver receiver;      /**< receiver pointer to dlt receiver structure */
        int sock;                  /**< sock Connection handle/socket */
        char *servIP;              /**< servIP IP adress/Hostname of interface */
        char *hostip;              /**< hostip IP address of UDP host receiver interface */
        uint16_t  port;            /**< Port for TCP connections (optional) */
        char *serialDevice;        /**< serialDevice Devicename of serial device */
        char *socketPath;          /**< socketPath Unix socket path */
        char ecuid[4];             /**< ECU id */
        uint8_t ecuid2len;         /**< Version 2 ECU id length */
        char *ecuid2;              /**< Version 2 ECU id of variable length*/
        speed_t baudrate;          /**< baudrate Baudrate of serial interface, as speed_t */
        int mode;                  /**< mode DltClientMode */
        int send_serial_header;    /**< (Boolean) Send DLT messages with serial header */
        int resync_serial_header;  /**< (Boolean) Resync to serial header on all connection */
    } DltClient;
    """

    _fields_ = [
        ("receiver", cDltReceiver),
        ("sock", ctypes.c_int),
        ("servIP", ctypes.c_char_p),
        ("hostip", ctypes.c_char_p),
        ("port", ctypes.c_uint16),
        ("serialDevice", ctypes.c_char_p),
        ("socketPath", ctypes.c_char_p),
        ("ecuid", ctypes.c_char * 4),
        ("ecuid2len", ctypes.c_uint8),
        ("ecuid2", ctypes.c_char_p),
        ("baudrate", ctypes.c_uint),
        ("mode", ctypes.c_int),
        ("send_serial_header", ctypes.c_int),
        ("resync_serial_header", ctypes.c_int),
    ]


class cDLTFilter(ctypes.Structure):  # pylint: disable=invalid-name
    """
    typedef struct
    {
        char apid[DLT_FILTER_MAX][DLT_ID_SIZE]; /**< application id */
        char ctid[DLT_FILTER_MAX][DLT_ID_SIZE]; /**< context id */
        uint8_t apid2len[DLT_FILTER_MAX];       /**< length of application id */
        char *apid2[DLT_FILTER_MAX];            /**< application id */
        uint8_t ctid2len[DLT_FILTER_MAX];       /**< length of context id */
        char *ctid2[DLT_FILTER_MAX];            /**< context id */
        int log_level[DLT_FILTER_MAX];          /**< log level */
        int32_t payload_max[DLT_FILTER_MAX];    /**< upper border for payload */
        int32_t payload_min[DLT_FILTER_MAX];    /**< lower border for payload */
        int counter;                            /**< number of filters */
    } DltFilter;
    """

    _fields_ = [
        ("apid", (ctypes.c_char * DLT_ID_SIZE) * DLT_FILTER_MAX),
        ("ctid", (ctypes.c_char * DLT_ID_SIZE) * DLT_FILTER_MAX),
        ("apid2len", ctypes.c_uint8 * DLT_FILTER_MAX),
        ("apid2", ctypes.c_char_p * DLT_FILTER_MAX),
        ("ctid2len", ctypes.c_uint8 * DLT_FILTER_MAX),
        ("ctid2", ctypes.c_char_p * DLT_FILTER_MAX),
        ("log_level", ctypes.c_int * DLT_FILTER_MAX),
        ("payload_max", (ctypes.c_int32 * DLT_FILTER_MAX)),
        ("payload_min", (ctypes.c_int32 * DLT_FILTER_MAX)),
        ("counter", ctypes.c_int),
    ]

    # pylint: disable=too-many-arguments
    def add(self, apid, ctid, log_level=0, payload_min=0, payload_max=ctypes.c_uint32(-1).value // 2):
        """Add new filter pair"""
        if isinstance(apid, str):
            apid = bytes(apid, "ascii")
        if isinstance(ctid, str):
            ctid = bytes(ctid, "ascii")
        if (
            dltlib.dlt_filter_add(
                ctypes.byref(self), apid or b"", ctid or b"", log_level, payload_min, payload_max, self.verbose
            )
            == DLT_RETURN_ERROR
        ):
            if self.counter >= DLT_FILTER_MAX:
                logger.error("Maximum number (%d) of allowed filters reached, ignoring filter!\n", DLT_FILTER_MAX)
                return MAX_FILTER_REACHED
            logger.debug("Filter ('%s', '%s') already exists", apid, ctid)
            return REPEATED_FILTER
        return 0
