""" This file is part of MetPx-Sarracenia.

MetPx-Sarracenia documentation: https://github.com/MetPX/sarracenia

sr_post_unit_test.py : test utility tool used for sr_post

PyCharm

Code contributed by:
 Benoit Lapointe - Shared Services Canada - 2019-09-30
"""
import io
import json
import logging
import os
import stat
import sys
import tempfile
import unittest
from math import ceil
from pathlib import Path

import appdirs

from sarra.sr_message import sr_message
from sarra.sr_post import sr_post


class PartitionningTestCase(unittest.TestCase):
    """ The parent class of all partitionning/reassembling process (p/r.p) test cases

    It handles base configs used in all tests
    """
    post = None
    fpath = None

    @classmethod
    def setUpClass(cls) -> None:
        """ Setup basic config file with basic include.

        :return: None
        """
        cls.testdir = Path(tempfile.gettempdir(), __name__)
        test_conf_name = "{}.conf".format(cls.__name__)
        cls.fpath = Path(appdirs.user_config_dir(str(Path('sarra', 'post'))), test_conf_name)
        with cls.fpath.open('w') as f:
            f.write('post_broker            amqp://tsource@${FLOWBROKER}/\n')
            f.write('post_exchange_suffix   post\n')
            f.write('post_topic_prefix      v03.post\n')
            f.write('path                   {}\n'.format(cls.testdir))
            f.write('post_base_url          ftp://anonymous@localhost:2121\n')
            f.write('outlet                 json')
        logging.disable()
        cls.post = sr_post(config=str(cls.fpath))
        cls.post.msg = sr_message(cls.post)
        cls.post.connect()
        cls.post.blocksize = 1000
        logging.disable(logging.NOTSET)
        cls.fname = '{}.py'.format(__name__)
        cls.lstat = os.stat(cls.fname)
        cls.fsiz = cls.lstat[stat.ST_SIZE]

    @classmethod
    def tearDownClass(cls) -> None:
        """ Remove configs for sr_config tests.

        :return: None
        """
        cls.fpath.unlink()
        # cls.testdir.rmdir()

    @staticmethod
    def capture(command, *args, **kwargs):
        """ Catch the whole std output generated from a command

        :param command: to be executed to gets its output
        :return: every lines generated during the execution
        """
        out, sys.stdout = sys.stdout, io.StringIO()
        try:
            command(*args, **kwargs)
            sys.stdout.seek(0)
            return sys.stdout.readlines()
        finally:
            sys.stdout = out


class HeadersTestCase(PartitionningTestCase):
    """ Test case related to parts string header standard """
    def setUp(self) -> None:
        logging.disable()
        stdout = self.capture(self.post.post_file_in_parts, self.fname, self.lstat)
        logging.disable(logging.NOTSET)
        self.headers = [json.loads(l)[3] for l in stdout]


class HeadersTest(HeadersTestCase):
    def test_parts_exist(self):
        """ test that the part string get created """
        for msg in self.headers:
            self.assertIn('parts', msg)

    def test_blocks_exist(self):
        """ test that the part string get created """
        for msg in self.headers:
            self.assertIn('blocks', msg)


class V02PartsTest(HeadersTestCase):
    """ Test that v02 parts string header is consistent with standard """
    def setUp(self) -> None:
        super(V02PartsTest, self).setUp()
        self.parts_list = [h['parts'].split(',') for h in self.headers]

    def test_parts_size(self):
        """ test that all information was included in the parts string """
        for parts in self.parts_list:
            self.assertEqual(5, len(parts))

    def test_method(self):
        """ test element method of parts string """
        for parts in self.parts_list:
            self.assertIn(parts[0], ['i', '1'])

    def test_bsz(self):
        """ test element bsz of parts string """
        for parts in self.parts_list:
            self.assertEqual(self.post.set_blocksize(self.post.blocksize, self.fsiz), int(parts[1]))

    def test_blktot(self):
        """ test element blktot of parts string """
        for parts in self.parts_list:
            self.assertEqual(ceil(self.fsiz / float(parts[1])), int(parts[2]))

    def test_brem(self):
        """ test element remainder of parts string """
        for parts in self.parts_list:
            self.assertEqual(self.fsiz % int(parts[1]), int(parts[3]))

    def test_bno(self):
        """ test element that all blocks of parts string are there """
        for parts in self.parts_list:
            self.assertLess(int(parts[4]), int(parts[2]))


class V03BlocksTest(HeadersTestCase):
    """ Test case related to parts string header standard """
    def setUp(self) -> None:
        super(V03BlocksTest, self).setUp()
        self.blocks_list = [h['blocks'] for h in self.headers]

    def test_blocks_size(self):
        """ test that all information was included in the blocks dictionnary"""
        for blocks in self.blocks_list:
            self.assertEqual(5, len(blocks))

    def test_method(self):
        """ test element method of parts string """
        for blocks in self.blocks_list:
            self.assertIn(blocks['method'], ['inplace'])

    def test_size(self):
        """ test element bsz of parts string """
        for blocks in self.blocks_list:
            self.assertEqual(self.post.set_blocksize(self.post.blocksize, self.fsiz), int(blocks['size']))

    def test_count(self):
        """ test element blktot of parts string """
        for blocks in self.blocks_list:
            self.assertEqual(ceil(self.fsiz / float(blocks['size'])), int(blocks['count']))

    def test_remainder(self):
        """ test element blktot of parts string """
        for blocks in self.blocks_list:
            self.assertEqual(self.fsiz % int(blocks['size']), int(blocks['remainder']))

    def test_number(self):
        """ test element blktot of parts string """
        self.assertEqual(int(self.blocks_list[0]['count']), len(set([b['number'] for b in self.blocks_list])))


class V02OnePartTest(V02PartsTest):
    """ Test case related to parts string header standard """
    def setUp(self) -> None:
        self.post.blocksize = 1
        logging.disable()
        stdout = self.capture(self.post.post_file, self.fname, self.lstat)
        logging.disable(logging.NOTSET)
        self.headers = [json.loads(l)[3] for l in stdout]
        self.parts_list = [h['parts'].split(',') for h in self.headers]


class V03OneBlockTest(V03BlocksTest):
    """ Test case related to parts string header standard """
    def setUp(self) -> None:
        self.post.blocksize = 1
        super(V03OneBlockTest, self).setUp()


class SetBlocksizeTest(PartitionningTestCase):
    def test_set_blocksize_negative(self):
        bsiz = self.post.set_blocksize(-1, self.fsiz)
        self.assertEqual(self.fsiz, bsiz)

    def test_set_blocksize_0(self):
        bsiz = self.post.set_blocksize(0, self.fsiz)
        self.assertEqual(self.fsiz, bsiz)

    def test_set_blocksize_1(self):
        bsiz = self.post.set_blocksize(1, self.fsiz)
        self.assertEqual(self.fsiz, bsiz)

    def test_set_blocksize_greater(self):
        bsiz = self.post.set_blocksize(2, self.fsiz)
        self.assertEqual(2, bsiz)


def suite():
    """ Create the test suite that include all sr_config test cases

    :return: sr_config test suite
    """
    sr_config_suite = unittest.TestSuite()
    sr_config_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(HeadersTest))
    sr_config_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(V02PartsTest))
    sr_config_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(V03BlocksTest))
    sr_config_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(V02OnePartTest))
    sr_config_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(V03OneBlockTest))
    sr_config_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(SetBlocksizeTest))
    return sr_config_suite


if __name__ == '__main__':
    unittest.main()
