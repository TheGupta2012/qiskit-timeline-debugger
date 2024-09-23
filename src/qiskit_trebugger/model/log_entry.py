"""Defines a log entry for the debugger"""

from time import time


class LogEntry:
    """Class for a log entry of the debugger"""

    def __init__(self, levelname, msg, args):
        """Defines a log entry with the level of log,
           log message and the arguments

        Args:
            levelname (str): Level of severity for the log
            msg (str): log message
            args (list): list of arguments for the log
        """
        self.levelname = levelname
        self.msg = msg
        self.args = args
        self.time = time()

    def __repr__(self) -> str:
        return f"[{self.levelname}] {self.msg}"

    def get_args(self):
        """Get the arguments of log entry

        Returns:
            list: argument list
        """
        return self.args
