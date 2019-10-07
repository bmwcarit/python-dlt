# Copyright (C) 2015. BMW Car IT GmbH. All rights reserved.
"""Static checks for python-dlt"""

import os
import unittest

from nose.tools import assert_equal

from dlt import run_command


def search_bin_path(search_bin, search_path):
    for path in search_path:
        if all(os.path.exists(os.path.join(path, bin_name)) for bin_name in search_bin):
            return path

    raise ValueError("Could not find path for {}".format(search_bin))


class TestCodingStyleCheck(unittest.TestCase):
    def setUp(self):
        search_bin = ['pycodestyle', 'pylint']
        search_path = ['/opt/nativesysroot/usr/bin', '/usr/local/bin']

        tox_bin_path = os.getenv('PATH').split(':')[0]
        if tox_bin_path.startswith(os.path.join(os.getcwd(), '.tox')):
            search_path.append(tox_bin_path)

        self.prefix_path = search_bin_path(search_bin, search_path)

    def test_check_pycodestyle(self):
        command = [os.path.join(self.prefix_path, "pycodestyle"), "dlt"]
        stdout, stderr, return_code = run_command(command, shell=False)
        assert_equal(return_code, 0, "Stdout: {}\nStderr: {}".format(stdout, stderr))

    def test_check_pylint(self):
        command = [os.path.join(self.prefix_path, "pylint"), "--rcfile", "setup.cfg", "dlt"]
        stdout, stderr, return_code = run_command(command, shell=False)
        assert_equal(return_code, 0, "Stdout: {}\nStderr: {}".format(stdout, stderr))
