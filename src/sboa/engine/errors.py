"""Runtime helpers for SBOA, part of the BOA suite.

Written by Daniel Brosnan Blázquez.
"""

class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class InputError(Error):
    """Exception raised when the specified inputs have a wrong type.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message


class SboaLogPathNotAvailable(Error):
    """The SBOA log directory cannot be created or accessed."""
