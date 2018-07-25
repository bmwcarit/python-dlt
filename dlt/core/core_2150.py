# Copyright (C) 2017. BMW Car IT GmbH. All rights reserved.
"""v2.15.0 specific class definitions"""
import ctypes
from dlt.core.core_base import cDltReceiver


class cDltClient(ctypes.Structure):  # pylint: disable=invalid-name
    """
    typedef struct
    {
        DltReceiver receiver;  /**< receiver pointer to dlt receiver structure */
        int sock;              /**< sock Connection handle/socket */
        char *servIP;          /**< servIP IP adress/Hostname of TCP/IP interface */
        char *serialDevice;    /**< serialDevice Devicename of serial device */
        char *socketPath;      /**< socketPath Unix socket path */
        speed_t baudrate;      /**< baudrate Baudrate of serial interface, as speed_t */
        DltClientMode mode;    /**< mode DltClientMode */
    } DltClient;
    """
    _fields_ = [("receiver", cDltReceiver),
                ("sock", ctypes.c_int),
                ("servIP", ctypes.c_char_p),
                ("serialDevice", ctypes.c_char_p),
                ("socketPath", ctypes.c_char_p),
                ("baudrate", ctypes.c_int),
                ("mode", ctypes.c_int)]
