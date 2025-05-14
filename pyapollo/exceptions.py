"""
This module contains the exceptions class used in the project.
"""


class BasicException(BaseException):
    def __init__(self, msg: str):
        self._msg = msg


class ServerNotResponseException(BasicException):
    pass
