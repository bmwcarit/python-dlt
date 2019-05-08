# Copyright (C) 2016. BMW Car IT GmbH. All rights reserved.
"""Default implementation of the ctypes bindings for the DLT library"""
import ctypes

# pylint: disable=too-few-public-methods,invalid-name

dltlib = ctypes.cdll.LoadLibrary('libdlt.so.2')

DLT_ID_SIZE = 4
DLT_FILTER_MAX = 30  # Maximum number of filters
DLT_HTYP_UEH = 0x01  # use extended header
DLT_HTYP_WEID = 0x04  # with ECU ID
DLT_HTYP_WSID = 0x08  # with Session ID
DLT_HTYP_WTMS = 0x10  # with timestamp
DLT_MESSAGE_ERROR_OK = 0

DLT_DAEMON_TEXTSIZE = 10024

DLT_OUTPUT_HEX = 1
DLT_OUTPUT_ASCII = 2
DLT_OUTPUT_MIXED_FOR_PLAIN = 3
DLT_OUTPUT_MIXED_FOR_HTML = 4
DLT_OUTPUT_ASCII_LIMITED = 5

DLT_RETURN_ERROR = -1
DLT_RETURN_OK = 0
DLT_RETURN_TRUE = 1

# DltClientMode from dlt_client.h
DLT_CLIENT_MODE_UNDEFINED = -1
DLT_CLIENT_MODE_TCP = 0
DLT_CLIENT_MODE_SERIAL = 1
DLT_CLIENT_MODE_UNIX = 2

DLT_TYPE_LOG = 0x00  # Log message type
DLT_TYPE_APP_TRACE = 0x01  # Application trace message type
DLT_TYPE_NW_TRACE = 0x02  # Network trace message type
DLT_TYPE_CONTROL = 0x03  # Control message type
DLT_CONTROL_REQUEST = 0x01
DLT_CONTROL_RESPONSE = 0x02  # Response to request message
DLT_CONTROL_TIME = 0x03
DLT_MSIN_MSTP_SHIFT = 1  # shift right offset to get mstp value
DLT_MSIN_MTIN_SHIFT = 4  # shift right offset to get mtin value
DLT_MSIN_MSTP = 0x0e  # message type
DLT_MSIN_MTIN = 0xf0  # message type info
DLT_MSIN_VERB = 0x01  # verbose mode
DLT_MSIN_CONTROL_RESPONSE = (DLT_TYPE_CONTROL << DLT_MSIN_MSTP_SHIFT) | (DLT_CONTROL_RESPONSE << DLT_MSIN_MTIN_SHIFT)

# dlt_protocol.h
DLT_SERVICE_ID_GET_SOFTWARE_VERSION = 0x13  # Service ID: Get software version
DLT_SERVICE_ID_UNREGISTER_CONTEXT = 0xf01  # Service ID: Message unregister context
DLT_SERVICE_ID_CONNECTION_INFO = 0xf02  # Service ID: Message connection info
DLT_SERVICE_ID_TIMEZONE = 0xf03  # Service ID: Timezone
DLT_SERVICE_ID_MARKER = 0xf04  # Service ID: Marker

DLT_CONNECTION_STATUS_DISCONNECTED = 0x01  # Client is disconnected
DLT_CONNECTION_STATUS_CONNECTED = 0x02  # Client is connected

DLT_TYPE_INFO_TYLE = 0x0000000f  # Length of standard data: 1 = 8bit, 2 = 16bit, 3 = 32 bit, 4 = 64 bit, 5 = 128 bit
DLT_TYPE_INFO_BOOL = 0x00000010  # Boolean data
DLT_TYPE_INFO_SINT = 0x00000020  # Signed integer data
DLT_TYPE_INFO_UINT = 0x00000040  # Unsigned integer data
DLT_TYPE_INFO_FLOA = 0x00000080  # Float data
DLT_TYPE_INFO_ARAY = 0x00000100  # Array of standard types
DLT_TYPE_INFO_STRG = 0x00000200  # String
DLT_TYPE_INFO_RAWD = 0x00000400  # Raw data
DLT_TYPE_INFO_VARI = 0x00000800  # Set, if additional information to a variable is available
DLT_TYPE_INFO_FIXP = 0x00001000  # Set, if quantization and offset are added
DLT_TYPE_INFO_TRAI = 0x00002000  # Set, if additional trace information is added
DLT_TYPE_INFO_STRU = 0x00004000  # Struct
DLT_TYPE_INFO_SCOD = 0x00038000  # coding of the type string: 0 = ASCII, 1 = UTF-8

DLT_SCOD_ASCII = 0x00000000
DLT_SCOD_UTF8 = 0x00008000
DLT_SCOD_HEX = 0x00010000
DLT_SCOD_BIN = 0x00018000

DLT_TYLE_8BIT = 0x00000001
DLT_TYLE_16BIT = 0x00000002
DLT_TYLE_32BIT = 0x00000003
DLT_TYLE_64BIT = 0x00000004
DLT_TYLE_128BIT = 0x00000005

DLT_DAEMON_TCP_PORT = 3490
DLT_CLIENT_RCVBUFSIZE = 10024  # Size of client receive buffer from dlt_client_cfg.h

# dlt-viever/qdltbase.cpp
qDltMessageType = ["log", "app_trace", "nw_trace", "control", "", "", "", ""]
qDltLogInfo = ["", "fatal", "error", "warn", "info", "debug", "verbose", "", "", "", "", "", "", "", "", ""]
qDltTraceType = ["", "variable", "func_in", "func_out", "state", "vfb", "", "", "", "", "", "", "", "", "", ""]
qDltNwTraceType = ["", "ipc", "can", "flexray", "most", "vfb", "", "", "", "", "", "", "", "", "", ""]
qDltControlType = ["", "request", "response", "time", "", "", "", "", "", "", "", "", "", "", "", ""]
cqDltMode = ["non-verbose", "verbose"]
qDltEndianness = ["little-endian", "big-endian"]
cqDltTypeInfo = ["String", "Bool", "SignedInteger", "UnsignedInteger", "Float", "RawData", "TraceInfo", "Utf8String"]
qDltCtrlServiceId = ["", "set_log_level", "set_trace_status", "get_log_info", "get_default_log_level", "store_config",
                     "reset_to_factory_default", "set_com_interface_status", "set_com_interface_max_bandwidth",
                     "set_verbose_mode", "set_message_filtering", "set_timing_packets", "get_local_time",
                     "use_ecu_id", "use_session_id", "use_timestamp", "use_extended_header", "set_default_log_level",
                     "set_default_trace_status", "get_software_version", "message_buffer_overflow"]
qDltCtrlReturnType = ["ok", "not_supported", "error", "3", "4", "5", "6", "7", "no_matching_context_id"]


class cDltServiceConnectionInfo(ctypes.Structure):
    """
    typedef struct
    {
        uint32_t service_id;            /**< service ID */
        uint8_t status;                 /**< reponse status */
        uint8_t state;                  /**< new state */
        char comid[DLT_ID_SIZE];        /**< communication interface */
    } PACKED DltServiceConnectionInfo;
    """
    _pack_ = 1
    _fields_ = [("service_id", ctypes.c_uint32),
                ("status", ctypes.c_uint8),
                ("state", ctypes.c_uint8),
                ("comid", DLT_ID_SIZE * ctypes.c_byte)]


class MessageMode(object):
    """Default properties for the DLTMessage"""
    # pylint: disable=no-member

    @property
    def use_extended_header(self):
        """Returns True if the DLTMessage has extended header"""
        return self.standardheader.htyp & DLT_HTYP_UEH

    @property
    def is_mode_verbose(self):
        """Returns True if the DLTMessage is set to verbose mode"""
        return self.extendedheader.msin & DLT_MSIN_VERB

    @property
    def mode_string(self):
        """Returns 'verbose' if DLTMessage is set to verbose mode. Otherwise 'non-verbose'"""
        return self.is_mode_verbose and "verbose" or "non-verbose"

    @property
    def is_mode_non_verbose(self):
        """Returns True if the DLTMessage is set to non-verbose mode"""
        return not self.is_mode_verbose

    @property
    def is_type_control(self):
        """Returns True if the DLTMessage type is control"""
        return self.standardheader.htyp & DLT_TYPE_CONTROL

    @property
    def is_type_control_response(self):
        """Returns True if the DLTMessage type is control response"""
        return self.standardheader.htyp & DLT_MSIN_CONTROL_RESPONSE

    @property
    def message_id(self):
        """Returns message ID of the DLTMessage"""
        if self.is_mode_non_verbose and (self.datasize >= 4):
            ptr_int = ctypes.cast(self.databuffer, ctypes.POINTER(ctypes.c_uint32))
            mid = ptr_int[0]
            return mid
        return 0

    @property
    def message_id_string(self):
        """Returns string representation of message ID"""
        mid = self.message_id
        return (mid >= 0 and mid <= len(qDltCtrlServiceId)) and qDltCtrlServiceId[mid] or ""

    @property
    def ctrl_service_id(self):
        """Returns service ID of the DLTMessage"""
        service_id = 0
        if self.is_type_control and self.datasize >= 4:
            ptr_int = ctypes.cast(self.databuffer, ctypes.POINTER(ctypes.c_uint32))
            service_id = ptr_int[0]
        return service_id

    @property
    def ctrl_service_id_string(self):
        """Returns string representation of service ID"""
        sid = self.ctrl_service_id
        if sid == DLT_SERVICE_ID_UNREGISTER_CONTEXT:
            return "unregister_context"
        elif sid == DLT_SERVICE_ID_CONNECTION_INFO:
            return "connection_info"
        elif sid == DLT_SERVICE_ID_TIMEZONE:
            return "timezone"
        elif sid == DLT_SERVICE_ID_MARKER:
            return "marker"
        return sid <= 20 and qDltCtrlServiceId[sid] or ""

    @property
    def ctrl_return_type(self):
        """Returns ctrl type of the DLTMessage"""
        return_type = 0
        if self.is_type_control and (self.is_type_control_response and self.datasize >= 6):
            return_type = self.databuffer[4]
        return return_type

    @property
    def ctrl_return_type_string(self):
        """Returns string representation of ctrl type"""
        return self.ctrl_return_type <= 8 and qDltCtrlReturnType[self.ctrl_return_type] or ""

    @property
    def type(self):
        """Returns message type of the DLTMessage"""
        return (self.extendedheader.msin & DLT_MSIN_MSTP) >> DLT_MSIN_MSTP_SHIFT

    @property
    def type_string(self):
        """Returns string representation of the message type"""
        mtype = self.type
        return (mtype >= 0 and mtype <= 7) and qDltMessageType[mtype] or ""

    @property
    def subtype(self):
        """Returns message subtype of the DLTMessage"""
        return (self.extendedheader.msin & DLT_MSIN_MTIN) >> DLT_MSIN_MTIN_SHIFT

    @property
    def subtype_string(self):
        """Returns string representation of the message subtype"""
        mtype = self.type
        msubtype = self.subtype

        if mtype == DLT_TYPE_LOG:
            return (msubtype >= 0 and msubtype <= 7) and qDltLogInfo[msubtype] or ""
        elif mtype == DLT_TYPE_APP_TRACE:
            return (msubtype >= 0 and msubtype <= 7) and qDltTraceType[msubtype] or ""
        elif mtype == DLT_TYPE_NW_TRACE:
            return (msubtype >= 0 and msubtype <= 7) and qDltNwTraceType[msubtype] or ""
        elif mtype == DLT_TYPE_CONTROL:
            return (msubtype >= 0 and msubtype <= 7) and qDltControlType[msubtype] or ""

        return ""

    @property
    def payload_decoded(self):
        """Decode the payload data

        :returns: Payload data
        :rtype: str
        """
        text = ""
        if self.is_mode_non_verbose and not self.is_type_control and self.noar == 0:
            buf = ctypes.create_string_buffer(b'\000' * DLT_DAEMON_TEXTSIZE)
            dltlib.dlt_message_payload(ctypes.byref(self), buf, DLT_DAEMON_TEXTSIZE, DLT_OUTPUT_ASCII, self.verbose)
            return "[{}] #{}#".format(self.message_id_string, buf.value[4:])

        if self.type == DLT_TYPE_CONTROL and self.subtype == DLT_CONTROL_RESPONSE:
            if self.ctrl_service_id == DLT_SERVICE_ID_MARKER:
                return "MARKER"

            text = "[%s %s] " % (self.ctrl_service_id_string, self.ctrl_return_type_string)
            service_id = self.ctrl_service_id

            if self.ctrl_service_id == DLT_SERVICE_ID_GET_SOFTWARE_VERSION:
                text += ctypes.string_at(self.databuffer, self.datasize)[9:]
            elif self.ctrl_service_id == DLT_SERVICE_ID_CONNECTION_INFO:
                if self.datasize == ctypes.sizeof(cDltServiceConnectionInfo):
                    conn_info = cDltServiceConnectionInfo.from_buffer(bytearray(self.databuffer[:self.datasize]))
                    if conn_info.state == DLT_CONNECTION_STATUS_DISCONNECTED:
                        text += "disconnected"
                    elif conn_info.state == DLT_CONNECTION_STATUS_CONNECTED:
                        text += "connected"
                    else:
                        text += "unknown"
                    text += " " + ctypes.string_at(conn_info.comid, DLT_ID_SIZE).decode("utf8")
                else:
                    text += ctypes.string_at(self.databuffer, self.datasize)[5:256+5]
            elif service_id == DLT_SERVICE_ID_TIMEZONE:
                text += ctypes.string_at(self.databuffer, self.datasize)[5:256+5]
            else:
                buf = ctypes.create_string_buffer(b'\000' * DLT_DAEMON_TEXTSIZE)
                dltlib.dlt_message_payload(ctypes.byref(self), buf, DLT_DAEMON_TEXTSIZE, DLT_OUTPUT_ASCII,
                                           self.verbose)
                text += buf.value.decode("utf8")
            return text

        if self.type == DLT_TYPE_CONTROL:
            return "[{}] {}".format(self.ctrl_service_id_string,
                                    ctypes.string_at(self.databuffer, self.datasize)[4:256+4])

        buf = ctypes.create_string_buffer(b'\000' * DLT_DAEMON_TEXTSIZE)
        dltlib.dlt_message_payload(ctypes.byref(self), buf, DLT_DAEMON_TEXTSIZE, DLT_OUTPUT_ASCII, self.verbose)
        return buf.value.decode("utf8")


class cDltStorageHeader(ctypes.Structure):
    """
    /**
     * The structure of the DLT file storage header. This header is used before each stored DLT message.
     */
    typedef struct
    {
        char pattern[DLT_ID_SIZE];        /**< This pattern should be DLT0x01 */
        uint32_t seconds;                    /**< seconds since 1.1.1970 */
        int32_t microseconds;            /**< Microseconds */
        char ecu[DLT_ID_SIZE];            /**< The ECU id is added, if it is not already in the DLT message itself */
    } PACKED DltStorageHeader;
    """
    _fields_ = [("pattern", ctypes.c_char * DLT_ID_SIZE),
                ("seconds", ctypes.c_uint32),
                ("microseconds", ctypes.c_int32),
                ("ecu", ctypes.c_char * DLT_ID_SIZE)]

    def __reduce__(self):
        return (cDltStorageHeader, (self.pattern, self.seconds, self.microseconds, self.ecu))


class cDltStandardHeader(ctypes.BigEndianStructure):
    """The structure of the DLT standard header. This header is used in each DLT message.

    typedef struct
    {
        uint8_t htyp;           /**< This parameter contains several informations, see definitions below */
        uint8_t mcnt;           /**< The message counter is increased with each sent DLT message */
        uint16_t len;           /**< Length of the complete message, without storage header */
    } PACKED DltStandardHeader;
    """
    _fields_ = [("htyp", ctypes.c_uint8),
                ("mcnt", ctypes.c_uint8),
                ("len", ctypes.c_ushort)]

    def __reduce__(self):
        return (cDltStandardHeader, (self.htyp, self.mcnt, self.len))


class cDltStandardHeaderExtra(ctypes.Structure):
    """The structure of the DLT extra header parameters. Each parameter is sent only if enabled in htyp.

    typedef struct
    {
        char ecu[DLT_ID_SIZE];       /**< ECU id */
        uint32_t seid;     /**< Session number */
        uint32_t tmsp;     /**< Timestamp since system start in 0.1 milliseconds */
    } PACKED DltStandardHeaderExtra;
    """
    _fields_ = [("ecu", ctypes.c_char * DLT_ID_SIZE),
                ("seid", ctypes.c_uint32),
                ("tmsp", ctypes.c_uint32)]

    def __reduce__(self):
        return (cDltStandardHeaderExtra, (self.ecu, self.seid, self.tmsp))


class cDltExtendedHeader(ctypes.Structure):
    """The structure of the DLT extended header. This header is only sent if enabled in htyp parameter.

    typedef struct
    {
        uint8_t msin;          /**< messsage info */
        uint8_t noar;          /**< number of arguments */
        char apid[DLT_ID_SIZE];          /**< application id */
        char ctid[DLT_ID_SIZE];          /**< context id */
    } PACKED DltExtendedHeader;
    """
    _fields_ = [("msin", ctypes.c_uint8),
                ("noar", ctypes.c_uint8),
                ("apid", ctypes.c_char * DLT_ID_SIZE),
                ("ctid", ctypes.c_char * DLT_ID_SIZE)]

    def __reduce__(self):
        return (cDltExtendedHeader, (self.msin, self.noar, self.apid, self.ctid))


class cDLTMessage(ctypes.Structure):
    """The structure of the DLT messages.

    typedef struct sDltMessage
    {
        /* flags */
        int8_t found_serialheader;

        /* offsets */
        int32_t resync_offset;

        /* size parameters */
        int32_t headersize;    /**< size of complete header including storage header */
        int32_t datasize;      /**< size of complete payload */

        /* buffer for current loaded message */
        uint8_t headerbuffer[sizeof(DltStorageHeader)+
                             sizeof(DltStandardHeader)+sizeof(DltStandardHeaderExtra)+sizeof(DltExtendedHeader)];
                             /**< buffer for loading complete header */
        uint8_t *databuffer;         /**< buffer for loading payload */
        int32_t databuffersize;

        /* header values of current loaded message */
        DltStorageHeader       *storageheader;  /**< pointer to storage header of current loaded header */
        DltStandardHeader      *standardheader; /**< pointer to standard header of current loaded header */
        DltStandardHeaderExtra headerextra;     /**< extra parameters of current loaded header */
        DltExtendedHeader      *extendedheader; /**< pointer to extended of current loaded header */
    } DltMessage;
    """

    _fields_ = [("found_serialheader", ctypes.c_int8),
                ("resync_offset", ctypes.c_int32),

                ("headersize", ctypes.c_int32),
                ("datasize", ctypes.c_int32),

                ("headerbuffer", ctypes.c_uint8 * (ctypes.sizeof(cDltStorageHeader) +
                                                   ctypes.sizeof(cDltStandardHeader) +
                                                   ctypes.sizeof(cDltStandardHeaderExtra) +
                                                   ctypes.sizeof(cDltExtendedHeader))),
                ("databuffer", ctypes.POINTER(ctypes.c_uint8)),
                ("databuffersize", ctypes.c_uint32),

                ("p_storageheader", ctypes.POINTER(cDltStorageHeader)),
                ("p_standardheader", ctypes.POINTER(cDltStandardHeader)),
                ("headerextra", cDltStandardHeaderExtra),
                ("p_extendedheader", ctypes.POINTER(cDltExtendedHeader))]


class cDltReceiver(ctypes.Structure):
    """The structure is used to organise the receiving of data including buffer handling.
    This structure is used by the corresponding functions.

    typedef struct
    {
        int32_t lastBytesRcvd;    /**< bytes received in last receive call */
        int32_t bytesRcvd;        /**< received bytes */
        int32_t totalBytesRcvd;   /**< total number of received bytes */
        char *buffer;         /**< pointer to receiver buffer */
        char *buf;            /**< pointer to position within receiver buffer */
        int fd;               /**< connection handle */
        int32_t buffersize;       /**< size of receiver buffer */
    } DltReceiver;
    """
    _fields_ = [("lastBytesRcvd", ctypes.c_int32),
                ("bytesRcvd", ctypes.c_int32),
                ("totalBytesRcvd", ctypes.c_int32),
                ("buffer", ctypes.POINTER(ctypes.c_char)),
                ("buf", ctypes.POINTER(ctypes.c_char)),
                ("fd", ctypes.c_int),
                ("buffersize", ctypes.c_int32)]


class cDltClient(ctypes.Structure):
    """
    typedef struct
    {
        DltReceiver receiver;  /**< receiver pointer to dlt receiver structure */
        int sock;              /**< sock Connection handle/socket */
        char *servIP;          /**< servIP IP adress/Hostname of TCP/IP interface */
        char *serialDevice;    /**< serialDevice Devicename of serial device */
        speed_t baudrate;      /**< baudrate Baudrate of serial interface, as speed_t */
        int serial_mode;       /**< serial_mode Serial mode enabled =1, disabled =0 */
    } DltClient;
    """
    _fields_ = [("receiver", cDltReceiver),
                ("sock", ctypes.c_int),
                ("servIP", ctypes.c_char_p),
                ("serialDevice", ctypes.c_char_p),
                ("baudrate", ctypes.c_int),
                ("serial_mode", ctypes.c_int)]
