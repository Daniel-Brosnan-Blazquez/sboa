"""Runtime helpers for SBOA, part of the BOA suite.

Written by Daniel Brosnan Blázquez.
"""

import datetime
import logging
from functools import wraps

from sboa.logging import Log

logger = Log(name=__name__).logger


def debug(method):
    """
    Function for profiling methods when logging level is DEBUG

    :param method: method to be profiled
    :type method: function

    :return: returned value of the method
    :rtype: int
    """
    @wraps(method)
    def _wrapper(*args, **kwargs):
        logger.debug("Method {} is going to be executed.".format(method.__name__))
        if logger.level == logging.DEBUG:
            start = datetime.datetime.now()
        # end if
        exit_value = method(*args, **kwargs)
        if logger.level == logging.DEBUG:
            stop = datetime.datetime.now()
            logger.debug("Method {} lasted {} seconds.".format(method.__name__, (stop - start).total_seconds()))
        # end if
        return exit_value

    return _wrapper
