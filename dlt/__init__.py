# Copyright (C) 2015. BMW Car IT GmbH. All rights reserved.
"""DLT support module"""

import collections
import logging
import subprocess

if not hasattr(subprocess, "TimeoutExpired"):
    import subprocess32 as subprocess  # pylint: disable=import-error


LOGGER = logging.getLogger(__name__)
ProcessResult = collections.namedtuple("ProcessResult", ("stdout", "stderr", "returncode"))


def run_command(command, timeout=60, shell=True):
    """Run command in a shell and return stdout, stderr and return code

    :param str|list command: a command to run
    :param int timeout: timeout for the command
    :param bool shell: shell switch
    :returns: process result
    :rtype: subprocess compatible ProcessResult
    :raises RuntimeError: If timeout expires.
    """
    process = subprocess.Popen(
        command, shell=shell, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.terminate()
        raise RuntimeError("Timeout %d seconds reached for command '%s'" % (timeout, command))
    if isinstance(stdout, bytes):
        stdout = stdout.decode("utf-8")
    if isinstance(stderr, bytes):
        stderr = stderr.decode("utf-8")
    return ProcessResult(stdout, stderr, process.returncode)
