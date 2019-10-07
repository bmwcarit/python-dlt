# Copyright (C) 2017. BMW Car IT GmbH. All rights reserved.
"""Basic ctypes binding to the DLT library"""

# pylint: disable=invalid-name,wildcard-import

import ctypes
import os

import six

from dlt.core.core_base import *


API_VER = None


def get_version(loaded_lib):
    """Return the API version of the loaded libdlt.so library"""
    global API_VER  # pylint: disable=global-statement
    if API_VER is None:
        buf = ctypes.create_string_buffer(255)
        loaded_lib.dlt_get_version(ctypes.byref(buf), 255)
        # buf would be something like:
        # DLT Package Version: X.XX.X STABLE, Package Revision: vX.XX.XX build on Jul XX XXXX XX:XX:XX
        # -SYSTEMD -SYSTEMD_WATCHDOG -TEST -SHM
        if six.PY3:
            buf_split = buf.value.decode().split()
        else:
            buf_split = buf.value.split()

        API_VER = buf_split[3]

    return API_VER


def get_api_specific_file(version):
    """Return specific version api filename"""
    version_tuple = [int(num) for num in version.split('.')]
    if version_tuple[-1] != 0:
        # The mirror version does not exist, try to truncate
        version_tuple = version_tuple[:-1] + [0]
    name = 'core_{}.py'.format("".join((str(num) for num in version_tuple)))
    if not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), name)):
        raise ImportError("No module file: {}".format(name))

    return name


def check_libdlt_version(api_ver):
    """Check the version compatibility.

    python-dlt now only supports to run libdlt 2.18.0 or above.
    """
    ver_info = tuple(int(num) for num in api_ver.split('.'))
    if ver_info < (2, 18):
        raise ImportError("python-dlt only supports libdlt v2.18.0 or above")


API_VER = get_version(dltlib)
check_libdlt_version(API_VER)

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
api_specific_file = get_api_specific_file(API_VER)
overrides = __import__('dlt.core.{}'.format(api_specific_file[:-3]), globals(), locals(), ['*'])
locals().update(overrides.__dict__)
