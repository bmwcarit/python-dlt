# Copyright (C) 2017. BMW Car IT GmbH. All rights reserved.
"""Basic size tests for ctype wrapper definitions, to protect against regressions"""
import ctypes
from nose.tools import assert_equal

from dlt.core import *


class TestCoreStructures(object):

    @classmethod
    def setup_class(cls):
        cls.size_map = {'cDltServiceConnectionInfo' : 10,
                        'cDltStorageHeader' : 16,
                        'cDltStandardHeader' : 4,
                        'cDltStandardHeaderExtra' : 12,
                        'cDltExtendedHeader' : 10,
                        'cDLTMessage' : 120,
                        'cDltReceiver' : 40,
                        'cDltClient' : 72
                       }

        api_version = get_version(dltlib)
        if api_version == '2.15.0':
            cls.size_map.update({'cDltClient': 80})
        elif api_version == '2.16.0':
            cls.size_map.update({'cDltClient': 96})


    def test_sizeof(self):
        for clsname, expected in self.size_map.items():
            acutal = ctypes.sizeof(globals()[clsname])
            assert_equal(acutal, expected,
                         "v{0}, sizeof {1}: {2} != {3}".format(get_version(dltlib), clsname, acutal, expected))
