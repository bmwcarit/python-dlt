# Copyright (C) 2017. BMW Car IT GmbH. All rights reserved.
"""Basic size tests for ctype wrapper definitions, to protect against regressions"""
import ctypes
import importlib
import os
import unittest
from unittest.mock import patch, MagicMock

import dlt


class TestCoreStructures(unittest.TestCase):
    def setUp(self):
        self.size_map = {
            "cDltServiceConnectionInfo": 10,
            "cDltStorageHeader": 16,
            "cDltStandardHeader": 4,
            "cDltStandardHeaderExtra": 12,
            "cDltExtendedHeader": 10,
            "cDLTMessage": 120,
            "cDltReceiver": 72,
            "cDltClient": 144,
            "cDLTFilter": 604,
        }

    def test_sizeof(self):
        importlib.import_module("dlt.core")

        for clsname, expected in self.size_map.items():
            actual = ctypes.sizeof(getattr(dlt.core, clsname))
            self.assertEqual(
                actual,
                expected,
                msg="v{0}, sizeof {1}: {2} != {3}".format(
                    dlt.core.get_version(dlt.core.dltlib), clsname, actual, expected
                ),
            )


class TestImportSpecificVersion(unittest.TestCase):
    def setUp(self):
        self.original_api_version = dlt.core.API_VER
        self.version_answer = b"2.18.5"
        self.version_str = (
            b"DLT Package Version: 2.18.5 STABLE, Package Revision: v2.18.5_5_g33fbad1, "
            b"build on Sep  2 2020 11:55:50\n-SYSTEMD -SYSTEMD_WATCHDOG -TEST -SHM\n"
        )
        self.version_filename = "core_2185.py"
        self.version_truncate_str = "2.18.5"
        self.version_truncate_filename = "core_2180.py"

        dlt.core.API_VER = None

    def tearDown(self):
        dlt.core.API_VER = self.original_api_version

    def test_get_version(self):
        def mock_dlt_get_version(buf, buf_size):
            ver_cstr = ctypes.create_string_buffer(self.version_str)
            ctypes.memmove(buf, ver_cstr, len(ver_cstr))

        mock_loaded_lib = MagicMock()
        mock_loaded_lib.dlt_get_version = MagicMock(side_effect=mock_dlt_get_version)

        api_version = dlt.core.get_version(mock_loaded_lib)
        self.assertEqual(mock_loaded_lib.dlt_get_version.call_count, 1)

        self.assertEqual(api_version, self.version_answer.decode())
        self.assertEqual(dlt.core.API_VER, self.version_answer.decode())

    def test_get_api_specific_file(self):
        with patch.object(os.path, "exists", return_value=True):
            filename = dlt.core.get_api_specific_file(self.version_answer.decode())
            self.assertEqual(filename, self.version_filename)

    def test_get_api_specific_file_not_found(self):
        with patch.object(os.path, "exists", side_effect=[False, False]):
            with self.assertRaises(ImportError) as err_cm:
                dlt.core.get_api_specific_file(self.version_answer.decode())

            self.assertEqual(str(err_cm.exception), "No module file: {}".format(self.version_truncate_filename))

    def test_get_api_specific_file_truncate_minor_version(self):
        with patch.object(os.path, "exists", side_effect=[False, True]):
            filename = dlt.core.get_api_specific_file(self.version_truncate_str)
            self.assertEqual(filename, self.version_truncate_filename)
