# -*- coding: utf-8 -*-
"""Logging Filters."""


import logging

class FilterExceptions(logging.Filter):
    """Filter out the specified exceptions with specified logging level."""

    def __init__(self, ignore_exceptions):
        """
        Configure filtering out of the specified exceptions with specified logging level.

        ignore_exceptions: a tuple of tuples ((exception type, loglevel))
                           example: (("requests.exceptions.ReadTimeout", "WARNING"),)
        """
        logging_level_names = {level_name:
                               (getattr(logging, level_name) if isinstance(level_name, str) else level_name)
                               for level_name in logging._levelNames}  #pylint: disable=protected-access
        self._ignore_exceptions = []
        for (exc_type, exc_level) in ignore_exceptions:
            exception_idx = exc_type.rfind('.')
            module, exception = exc_type[:exception_idx], exc_type[exception_idx+1:]
            try:
                self._ignore_exceptions.append((logging_level_names[exc_level],
                                                getattr(__import__(module), exception)))
            except KeyError:
                raise ValueError('The logging level provided ({}) is invalid. Valid options: {}'
                      .format(exc_level, logging_level_names.keys()))
            except (ImportError, AttributeError):
                raise ValueError('The exception path does not exist ({}.{}).'.format(module, exception))
        super(FilterExceptions, self).__init__()

    def filter(self, record):
        """Filter out the specified exceptions with specified logging level."""
        if record.exc_info:
            for filter_level, filter_exc in self._ignore_exceptions:
                if record.exc_info[0] is filter_exc and record.levelno == filter_level:
                    return False
        return True
