import sys

from twisted.logger import (Logger, LogLevel,
                            globalLogBeginner,
                            textFileLogObserver,
                            FilteringLogObserver,
                            LogLevelFilterPredicate)


logLevelFilterPredicate = LogLevelFilterPredicate(
        defaultLogLevel=LogLevel.info)

log = Logger()


def startLogging(console: bool = True, filepath: str = None):
    """
    Starts the global Twisted logger subsystem with maybe
    stdout and/or a file specified in the config file
    """
    global logLevelFilterPredicate

    observers = []
    if console:
        observers.append(FilteringLogObserver(
            observer=textFileLogObserver(sys.stdout),
            predicates=[logLevelFilterPredicate]))

    if filepath is not None and filepath != "":
        observers.append(FilteringLogObserver(
            observer=textFileLogObserver(open(filepath, 'a')),
            predicates=[logLevelFilterPredicate]))
    globalLogBeginner.beginLoggingTo(observers)


def setLogLevel(namespace: str = None, levelStr: str = 'info'):
    """
    Set a new log level for a given namespace
    LevelStr is: 'critical', 'error', 'warn', 'info', 'debug'
    """
    level = LogLevel.levelWithName(levelStr)
    logLevelFilterPredicate.setLogLevelForNamespace(namespace=namespace,
                                                    level=level)
