# Copyright (C) 2017. BMW Car IT GmbH. All rights reserved.
"""v2.16.0 specific class definitions"""
import ctypes
from dlt.core.core_base import cDltReceiver


class cDltClient(ctypes.Structure):  # pylint: disable=invalid-name
    """
    typedef struct
    {
        DltReceiver receiver;  /**< receiver pointer to dlt receiver structure */
        int sock;              /**< sock Connection handle/socket */
        char *servIP;          /**< servIP IP adress/Hostname of TCP/IP interface */
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
                ("port", ctypes.c_int),
                ("serialDevice", ctypes.c_char_p),
                ("socketPath", ctypes.c_char_p),
                ("ecuid", ctypes.c_char * 4),
                ("baudrate", ctypes.c_uint),
                ("mode", ctypes.c_int)]
