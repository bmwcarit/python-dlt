# Copyright (C) 2015. BMW Car IT GmbH. All rights reserved.
"""Static checks for python-dlt"""

from dlt import run_command

from nose.tools import assert_equal


def test_check_pep8():
    command = ["pycodestyle", "dlt"]
    stdout, stderr, return_code = run_command(command, shell=False)
    assert_equal(return_code, 0, "Stdout: {}\nStderr: {}".format(stdout, stderr))


def test_check_pylint():
    command = ["pylint", "--rcfile", "setup.cfg", "dlt"]
    stdout, stderr, return_code = run_command(command, shell=False)
    assert_equal(return_code, 0, "Stdout: {}\nStderr: {}".format(stdout, stderr))
