#===============================================================================
# Imports
#===============================================================================
import sys
import unittest


#===============================================================================
# Helper Methods
#===============================================================================
def run_suite(suite, testclass=None):
    """Run tests from a unittest.TestSuite-derived class."""
    if verbose:
        runner = unittest.TextTestRunner(sys.stdout, verbosity=2)
    else:
        runner = BasicTestRunner()

    class TestFailed(Exception):
        """Test failed."""

    result = runner.run(suite)
    if not result.wasSuccessful():
        if len(result.errors) == 1 and not result.failures:
            err = result.errors[0][1]
        elif len(result.failures) == 1 and not result.errors:
            err = result.failures[0][1]
        else:
            if testclass is None:
                msg = "errors occurred; run in verbose mode for details"
            else:
                msg = "errors occurred in %s.%s" \
                      % (testclass.__module__, testclass.__name__)
            raise TestFailed(msg)
        raise TestFailed(err)


def run_unittest(*classes):
    """Run tests from unittest.TestCase-derived classes."""
    if '-v' in sys.argv:
        global verbose
        verbose = True
    suite = unittest.TestSuite()
    for cls in classes:
        if isinstance(cls, (unittest.TestSuite, unittest.TestCase)):
            suite.addTest(cls)
        else:
            suite.addTest(unittest.makeSuite(cls))
    if len(classes)==1:
        testclass = classes[0]
    else:
        testclass = None
    run_suite(suite, testclass)


def run_doctest(module, verbosity=None):
    """Run doctest on the given module.  Return (#failures, #tests).

    If optional argument verbosity is not specified (or is None), pass
    test_support's belief about verbosity on to doctest.  Else doctest's
    usual behavior is used (it searches sys.argv for -v).
    """

    import doctest

    if verbosity is None:
        verbosity = verbose
    else:
        verbosity = None

    # Direct doctest output (normally just errors) to real stdout; doctest
    # output shouldn't be compared by regrtest.
    save_stdout = sys.stdout
    sys.stdout = get_original_stdout()
    try:
        f, t = doctest.testmod(module, verbose=verbosity)
        if f:
            raise TestFailed("%d of %d doctests failed" % (f, t))
    finally:
        sys.stdout = save_stdout
    if verbose:
        print 'doctest (%s) ... %d tests with zero failures' % \
              (module.__name__, t)
    return f, t

#===============================================================================
# Helper Classes
#===============================================================================
class BasicTestRunner:
    def run(self, test):
        result = unittest.TestResult()
        test(result)
        return result


# vim:set ts=8 sw=4 sts=4 tw=78 et:
