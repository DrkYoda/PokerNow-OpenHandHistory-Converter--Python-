"""_summary_.

Raises:
    error.: _description_
    TimerError: _description_
    error.: _description_
    TimerError: _description_

Returns:
    _type_: _description_
"""
import time
from contextlib import ContextDecorator
from dataclasses import dataclass, field
from typing import Any, Callable, ClassVar, Dict, Optional


class TimerError(Exception):
    """A custom exception used to report errors in the use of Timer class."""


@dataclass
class Timer(ContextDecorator):
    """Time your code using Class, context manager, or decorator."""

    timers: ClassVar[Dict[str, float]] = {}
    name: Optional[str] = None
    text: str = '[Elapsed time: {0:0.6f} s]'
    logger: Optional[Callable[[str], None]] = print
    _start_time: Optional[float] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize: Add a timer to dict of timers."""
        if self.name:
            self.timers.setdefault(self.name, 0)

    def start(self) -> None:
        """Start new timer.

        Raises:
            TimerError: If a timer is already started, raise error.
        """
        if self._start_time is not None:
            raise TimerError('Timer is running. Use .stop() to stop it.')
        self._start_time = time.perf_counter()

    def stop(self) -> float:
        """Stop the timer, and report the elapsed time.

        Raises:
            TimerError: If a timer is not started, raise error.

        Returns:
            float: Elapsed time from start.
        """
        if self._start_time is None:
            raise TimerError(
                'Timer is not running. Use .start() to start it.',
            )

        # Calculate elapsed time.
        elapsed_time = time.perf_counter() - self._start_time
        self._start_time = None

        # Report elapsed time.
        if self.logger:
            self.logger(self.text.format(elapsed_time))
        if self.name:
            self.timers[self.name] += elapsed_time

        return elapsed_time

    def __enter__(self) -> 'Timer':
        """Start new timer as a context manager.

        Returns:
            _type_: _description_
        """
        self.start()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        """Stop the context manager timer."""
        self.stop()
