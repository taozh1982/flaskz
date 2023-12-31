from datetime import datetime
from threading import Timer

__all__ = ['set_interval', 'set_timeout', 'run_at']


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

    .. versionadded:: 1.0

    Example:
        t = set_interval(10000, print, ('Hello, World!',)) # 10s
        # t.cancel()    # Stop the timer

    :param interval: time interval in milliseconds
    :param function: callback function, which should do exception catching*
    :param args:
    :param kwargs:
    :param immediately: If True, the function will be executed immediately, otherwise it will be executed after the interval time
    :param daemon: if true, the timer will be daemon(Daemon threads are abruptly stopped at shutdown)
    :return:
    """
    t = _IntervalTimer(interval, function, args=args, kwargs=kwargs, immediately=immediately, daemon=daemon)
    return t


def set_timeout(interval, function, args=None, kwargs=None, daemon=True):
    """
    Set a timer which executes a function once the timer expires(milliseconds).

     .. versionadded:: 1.0

    Example:
        t = set_timeout(10000, print, ('Hello, World!',)) # 10s
        # t.cancel()    # Stop the timer

    :param interval: delay time in milliseconds before the specified function is executed
    :param function: the function to be executed
    :param args: the args of the function
    :param kwargs: the kwargs of the function
    :param daemon: whether the timer is a daemon thread, default True(Daemon thread stops abruptly when main thread is shut down)
    :return:
    """
    t = Timer(interval / 1000, function, args=args, kwargs=kwargs)
    t.daemon = daemon
    t.start()
    return t


def run_at(at_time, function, args=None, kwargs=None, daemon=True, time_format='%Y-%m-%d %H:%M:%S'):
    """
    Call a function at the specified datetime.

    .. versionadded:: 1.6.1

    Example:
        t1 = run_at('2023-06-28 14:53:00', print, ['run_at'])   # time str
        # t1.cancel()    # Stop the timer

        t2 = run_at(1629811200, print, ['run_at'])  # timestamp
        # t2.cancel()    # Stop the timer

    :param at_time: the specified datetime(str/timestamp)
    :param function: the function to be executed
    :param args: the args of the function
    :param kwargs: the kwargs of the function
    :param daemon: whether the timer is a daemon thread, default True(Daemon thread stops abruptly when main thread is shut down)
    :param time_format: the format of the specified datetime
    :return:
    """
    time_type = type(at_time)
    if time_type is str:
        at_time = datetime.strptime(at_time, time_format)
    elif time_type is int:
        at_time = datetime.fromtimestamp(at_time)
    now = datetime.now()
    timeout_ms = (at_time - now).total_seconds()
    if timeout_ms < 0:
        return False
    elif timeout_ms == 0:
        function(*(args if args is not None else []), **(kwargs if kwargs is not None else {}))
        return

    return set_timeout(timeout_ms * 1000, function, args=args, kwargs=kwargs, daemon=daemon)
