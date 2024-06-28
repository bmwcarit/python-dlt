# Copyright (C) 2022. BMW CTW PT. All rights reserved.
"""v2.18.8 specific class definitions"""
import ctypes
import logging

from dlt.core.core_base import dltlib

# DltClientMode from dlt_client.h
DLT_CLIENT_MODE_UNDEFINED = -1
DLT_CLIENT_MODE_TCP = 0
DLT_CLIENT_MODE_SERIAL = 1
DLT_CLIENT_MODE_UNIX = 2
DLT_CLIENT_MODE_UDP_MULTICAST = 3

# DltReceiverType from dlt_common.h
DLT_RECEIVE_SOCKET = 0
DLT_RECEIVE_UDP_SOCKET = 1
DLT_RECEIVE_FD = 2
DLT_ID_SIZE = 4
DLT_FILTER_MAX = 30  # Maximum number of filters
DLT_RETURN_ERROR = -1

# Return value for DLTFilter.add() - exceeded maximum number of filters
MAX_FILTER_REACHED = 1
# Return value for DLTFilter.add() - specified filter already exists
REPEATED_FILTER = 2

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class sockaddr_in(ctypes.Structure):  # pylint: disable=invalid-name
    """Auxiliary definition for cDltReceiver. Defined in netinet/in.h header"""

    _fields_ = [
        ("sa_family", ctypes.c_ushort),  # sin_family
        ("sin_port", ctypes.c_ushort),
        ("sin_addr", ctypes.c_byte * 4),
        ("__pad", ctypes.c_byte * 8),
    ]  # struct sockaddr_in is 16


class cDltReceiver(ctypes.Structure):  # pylint: disable=invalid-name
    """The structure is used to organise the receiving of data including buffer handling.
    This structure is used by the corresponding functions.

    typedef struct
    {
        int32_t lastBytesRcvd;    /**< bytes received in last receive call */
        int32_t bytesRcvd;        /**< received bytes */
        int32_t totalBytesRcvd;   /**< total number of received bytes */
        char *buffer;             /**< pointer to receiver buffer */
        char *buf;                /**< pointer to position within receiver buffer */
        char *backup_buf;         /** pointer to the buffer with partial messages if any **/
        int fd;                   /**< connection handle */
        DltReceiverType type;     /**< type of connection handle */
        int32_t buffersize;       /**< size of receiver buffer */
        struct sockaddr_in addr;  /**< socket address information */
    } DltReceiver;
    """

    _fields_ = [
        ("lastBytesRcvd", ctypes.c_int32),
        ("bytesRcvd", ctypes.c_int32),
        ("totalBytesRcvd", ctypes.c_int32),
        ("buffer", ctypes.POINTER(ctypes.c_char)),
        ("buf", ctypes.POINTER(ctypes.c_char)),
        ("backup_buf", ctypes.POINTER(ctypes.c_char)),
        ("fd", ctypes.c_int),
        ("type", ctypes.c_int),
        ("buffersize", ctypes.c_int32),
        ("addr", sockaddr_in),
    ]


class cDltClient(ctypes.Structure):  # pylint: disable=invalid-name
    """
    typedef struct
    {
        DltReceiver receiver;      /**< receiver pointer to dlt receiver structure */
        int sock;                  /**< sock Connection handle/socket */
        char *servIP;              /**< servIP IP adress/Hostname of TCP/IP interface */
        char *hostip;              /**< IP multicast address of group */
        int port;                  /**< Port for TCP connections (optional) */
        char *serialDevice;        /**< serialDevice Devicename of serial device */
        char *socketPath;          /**< socketPath Unix socket path */
        char ecuid[4];             /**< ECUiD */
        speed_t baudrate;          /**< baudrate Baudrate of serial interface, as speed_t */
        DltClientMode mode;        /**< mode DltClientMode */
        int send_serial_header;    /**< (Boolean) Send DLT messages with serial header */
        int resync_serial_header;  /**< (Boolean) Resync to serial header on all connection */
    } DltClient;
    """

    _fields_ = [
        ("receiver", cDltReceiver),
        ("sock", ctypes.c_int),
        ("servIP", ctypes.c_char_p),
        ("hostip", ctypes.c_char_p),
        ("port", ctypes.c_int),
        ("serialDevice", ctypes.c_char_p),
        ("socketPath", ctypes.c_char_p),
        ("ecuid", ctypes.c_char * 4),
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
        int log_level[DLT_FILTER_MAX];          /**< log level */
        int32_t payload_max[DLT_FILTER_MAX];    /**< upper border for payload */
        int32_t payload_min[DLT_FILTER_MAX];    /**< lower border for payload */
        int  counter;                           /**< number of filters */
    } DltFilter;
    """

    _fields_ = [
        ("apid", (ctypes.c_char * DLT_ID_SIZE) * DLT_FILTER_MAX),
        ("ctid", (ctypes.c_char * DLT_ID_SIZE) * DLT_FILTER_MAX),
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
