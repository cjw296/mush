from doctest import REPORT_NDIFF, ELLIPSIS
from glob import glob
from manuel import doctest, capture, codeblock
from manuel.testing import TestSuite
from os.path import dirname, join, pardir

tests = glob(join(join(dirname(__file__), pardir), 'docs', '*.txt'))

def test_suite():
    m =  doctest.Manuel(optionflags=REPORT_NDIFF|ELLIPSIS)
    m += codeblock.Manuel()
    m += capture.Manuel()
    return TestSuite(m, *tests)
