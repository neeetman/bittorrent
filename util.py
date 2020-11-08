import asyncio
from functools import reduce

from async_timeout import timeout as async_timeout

def collapse(data):
    """ Given an homogenous list, returns the items of that list
    concatenated together. """

    return reduce(lambda x, y: x + y, data)

def slice(string, n):
    """ Given a string and a number n, cuts the string up, returns a
    list of strings, all size n. """
    return [string[i:i + n] for i in range(0, len(string), n)]

class PerfectInterval():
    """Remove processing time from intervals"""

    def __init__(self):
        self._last_timestamp = 0

    def __call__(self, seconds):
        now = asyncio.get_event_loop().time()
        if self._last_timestamp <= 0:
            self._last_timestamp = int(now)
            return seconds
        else:
            expected = self._last_timestamp + seconds
            diff = now - expected
            interval = max(seconds - diff, 0)
            self._last_timestamp = expected


class SleepUneasy():
    """Asynchronous sleep() that can be aborted"""

    def __init__(self):
        self._interrupt = asyncio.Event()
        self._perfint = PerfectInterval()

    async def sleep(self, seconds):
        """Sleep for `seconds` or until `interrupt` is called"""
        self._interrupt.clear()
        # Remove processing time from seconds
        seconds = self._perfint(seconds)
        try:
            async with async_timeout(seconds):
                await self._interrupt.wait()
        except asyncio.TimeoutError:
            pass  # Interval passed without interrupt
        finally:
            self._interrupt.clear()

    def interrupt(self):
        """Stop sleeping"""
        self._interrupt.set()

