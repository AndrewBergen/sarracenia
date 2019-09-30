""" This file is part of MetPx-Sarracenia.

MetPx-Sarracenia documentation: https://github.com/MetPX/sarracenia

sr_post_unit_test.py : test utility tool used for sr_post

PyCharm

Code contributed by:
 Benoit Lapointe - Shared Services Canada - 2019-09-30
"""
import unittest


class MyTestCase(unittest.TestCase):
    def test_something(self):
        self.assertEqual(True, False)


def suite():
    """ Create the test suite that include all sr_config test cases

    :return: sr_config test suite
    """
    sr_config_suite = unittest.TestSuite()
    sr_config_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(MyTestCase))
    return sr_config_suite


if __name__ == '__main__':
    unittest.main()
