# Copyright (C) 2019. BMW Car IT GmbH. All rights reserved.
"""v2.18.6 specific class definitions"""
import ctypes

# DltClientMode from dlt_client.h
DLT_CLIENT_MODE_UNDEFINED = -1
DLT_CLIENT_MODE_TCP = 0
DLT_CLIENT_MODE_SERIAL = 1
DLT_CLIENT_MODE_UNIX = 2
DLT_CLIENT_MODE_UDP_MULTICAST = 3

# DltReceiverType from dlt_common.h
# DltReceiverType is an enum type. These definitions could not be found in shared library (libdlt.so) so
# the enum values are defined here.
DLT_RECEIVE_SOCKET = 0
DLT_RECEIVE_UDP_SOCKET = 1
DLT_RECEIVE_FD = 2


class sockaddr_in(ctypes.Structure):  # pylint: disable=invalid-name
    """Auxiliary definition for cDltReceiver. Defined in netinet/in.h header"""
    _fields_ = [("sa_family", ctypes.c_ushort),  # sin_family
                ("sin_port", ctypes.c_ushort),
                ("sin_addr", ctypes.c_byte * 4),
                ("__pad", ctypes.c_byte * 8)]    # struct sockaddr_in is 16


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
        DltReceiverType  type;    /**< type of connection handle */
        uint32_t buffersize;       /**< size of receiver buffer */
        struct sockaddr_in addr;  /**< socket address information */
    } DltReceiver;
    """
    _fields_ = [("lastBytesRcvd", ctypes.c_int32),
                ("bytesRcvd", ctypes.c_int32),
                ("totalBytesRcvd", ctypes.c_int32),
                ("buffer", ctypes.POINTER(ctypes.c_char)),
                ("buf", ctypes.POINTER(ctypes.c_char)),
                ("backup_buf", ctypes.POINTER(ctypes.c_char)),
                ("fd", ctypes.c_int),
                ("type", ctypes.c_int),
                ("buffersize", ctypes.c_uint32),
                ("addr", sockaddr_in)]


class cDltClient(ctypes.Structure):  # pylint: disable=invalid-name
    """
    typedef struct
    {
        DltReceiver receiver;  /**< receiver pointer to dlt receiver structure */
        int sock;              /**< sock Connection handle/socket */
        char *servIP;          /**< servIP IP adress/Hostname of TCP/IP interface */
        char *hostip;          /**< IP multicast address of group */
        int port;              /**< Port for TCP connections (optional) */
        char *serialDevice;    /**< serialDevice Devicename of serial device */
        char *socketPath;      /**< socketPath Unix socket path */
        char ecuid[4];           /**< ECUiD */
        speed_t baudrate;      /**< baudrate Baudrate of serial interface, as speed_t */
        DltClientMode mode;    /**< mode DltClientMode */
    } DltClient;
    """
    _fields_ = [("receiver", cDltReceiver),
                ("sock", ctypes.c_int),
                ("servIP", ctypes.c_char_p),
                ("hostip", ctypes.c_char_p),
                ("port", ctypes.c_int),
                ("serialDevice", ctypes.c_char_p),
                ("socketPath", ctypes.c_char_p),
                ("ecuid", ctypes.c_char * 4),
                ("baudrate", ctypes.c_uint),
                ("mode", ctypes.c_int)]
