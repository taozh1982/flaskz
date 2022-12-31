from threading import Timer

__all__ = ['set_timeout', 'set_interval']


class _IntervalTimer(object):
    def __init__(self, interval, function, args=None, kwargs=None, immediately=False, daemon=True):
        self._timer = None
        self.interval = interval  # milliseconds
        self.function = function
        self.timer_daemon = daemon
        self.args = args if args is not None else []
        self.kwargs = kwargs if kwargs is not None else {}
        self.is_started = False
        if immediately is True:
            self._run()
        else:
            self.start()

    def _run(self):
        self.is_started = False
        if self.function(*self.args, **self.kwargs) is not False:  # The callback function should do exception catching
            self.start()

    def start(self):
        if not self.is_started:
            self._timer = set_timeout(self.interval, self._run, daemon=self.timer_daemon)
            self.is_started = True

    def cancel(self):
        if self._timer:
            self._timer.cancel()
            self._timer = None
            self.is_started = False

    def stop(self):
        self.cancel()


def set_interval(interval, function, args=None, kwargs=None, immediately=False, daemon=True):
    """
    Execute a function periodically at a specified time interval(milliseconds).
    The result of the function execution is False, then the loop is interrupted.

        t = set_interval(10, print, ('Hello, World!',))
        # t.cancel()    # Stop the timer

    .. versionadded:: 1.0

    :param daemon: if true, the timer will be daemon(Daemon threads are abruptly stopped at shutdown)
    :param interval: time interval in milliseconds
    :param function: callback function, which should do exception catching*
    :param args:
    :param kwargs:
    :param immediately: If True, the function will be executed immediately, otherwise it will be executed after the interval time
    :return:
    """
    t = _IntervalTimer(interval, function, args=args, kwargs=kwargs, immediately=immediately, daemon=daemon)
    return t


def set_timeout(interval, function, args=None, kwargs=None, daemon=True):
    """
    Set a timer which executes a function once the timer expires(milliseconds).

        t = set_timeout(10, print, ('Hello, World!',))
        # t.cancel()    # Stop the timer

     .. versionadded:: 1.0

    :param daemon: if true, the timer will be daemon(Daemon threads are abruptly stopped at shutdown)
    :param interval: delay time in milliseconds before the specified function is executed
    :param function:
    :param args:
    :param kwargs:
    :return:
    """
    t = Timer(interval / 1000, function, args=args, kwargs=kwargs)
    t.daemon = daemon
    t.start()
    return t
