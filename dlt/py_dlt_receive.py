# Copyright (C) 2017. BMW Car IT GmbH. All rights reserved.
"""DLT Receive using py_dlt"""

import argparse
import logging
import time

from dlt.dlt import DLT_UDP_MULTICAST_FD_BUFFER_SIZE, DLT_UDP_MULTICAST_BUFFER_SIZE
from dlt.dlt_broker import DLTBroker

logging.basicConfig(format="%(asctime)s %(name)s %(levelname)-8s %(message)s")
root_logger = logging.getLogger()  # pylint: disable=invalid-name
logger = logging.getLogger("py-dlt-receive")  # pylint: disable=invalid-name


def parse_args():
    """Parse command line arguments"""
    logger.info("Parsing arguments")
    parser = argparse.ArgumentParser(description="Receive DLT messages")
    parser.add_argument("--host", required=True, help="hostname or ip address to connect to")
    parser.add_argument("--file", required=True, help="The file into which the messages will be written")
    parser.add_argument(
        "--udp-fd-buffer-size",
        dest="udp_fd_buffer_size",
        default=DLT_UDP_MULTICAST_FD_BUFFER_SIZE,
        type=int,
        help=f"Set the socket buffer size in udp multicast mode. default: {DLT_UDP_MULTICAST_FD_BUFFER_SIZE} bytes",
    )
    parser.add_argument(
        "--udp-buffer-size",
        dest="udp_buffer_size",
        default=DLT_UDP_MULTICAST_BUFFER_SIZE,
        type=int,
        help=f"Set the DltReceiver buffer size in udp multicast mode. default: {DLT_UDP_MULTICAST_BUFFER_SIZE} bytes",
    )
    return parser.parse_args()


def dlt_receive(options):
    """Receive DLT messages via DLTBroker"""
    logger.info("Creating DLTBroker instance")
    broker = DLTBroker(
        ip_address=options.host,
        filename=options.file,
        udp_fd_buffer_size_bytes=options.udp_buffer_size,
        udp_buffer_size_bytes=options.udp_fd_buffer_size,
    )

    logger.info("Starting DLTBroker")
    broker.start()  # start the loop
    try:
        logger.info("Receiving messages...")
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        logger.info("Interrupted...")
    finally:
        logger.info("Stopping DLT broker")
        broker.stop()
        logger.info("Stopped DLT broker")


def main():
    """Main function"""
    root_logger.setLevel(level=logging.INFO)

    options = parse_args()
    logger.info("Parsed arguments: %s", options)

    dlt_receive(options)


if __name__ == "__main__":
    main()
