# Copyright (C) 2017. BMW Car IT GmbH. All rights reserved.
"""Basic ctypes binding to the DLT library"""

# pylint: disable=invalid-name,wildcard-import

import ctypes
import os

from dlt.core.core_base import *


API_VER = None


def get_version(loaded_lib):
    """Return the API version of the loaded libdlt.so library"""
    global API_VER  # pylint: disable=global-statement
    if API_VER is None:
        buf = (ctypes.c_char * 255)()
        loaded_lib.dlt_get_version(ctypes.byref(buf), 255)
        # buf would be something like:
        # DLT Package Version: X.XX.X STABLE, Package Revision: vX.XX.XX build on Jul XX XXXX XX:XX:XX
        # -SYSTEMD -SYSTEMD_WATCHDOG -TEST -SHM
        API_VER = buf.value.split()[3]
    return API_VER


API_VER = get_version(dltlib).decode("ascii")

# Load version specific definitions, if such a file exists, possibly
# overriding above definitions
#
# The intent is to have version specific implementations to be able to
# provide declarations *incrementally*.
#
# For instance if version 2.17.0 introduces new changes in addition to
# retaining all changes from 2.16.0, then core_2170.py would import
# core_2160.py and declare only version specific changes/overrides. The
# loading logic here below should not require changes.
#
# This allows the implementation below to import just one final module
# (as opposed to loading multiple implementations in a specific order)
# to provide new/overriding implementations.

api_specific_file = 'core_{}.py'.format(API_VER.replace('.', ''))
if os.path.exists(os.path.join(os.path.dirname(__file__), api_specific_file)):
    overrides = __import__('dlt.core.{}'.format(api_specific_file[:-3]), globals(), locals(), ['*'])
    locals().update(overrides.__dict__)
