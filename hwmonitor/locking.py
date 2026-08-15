"""Windows mutex guard used to prevent overlapping scheduled runs."""

from __future__ import annotations

import ctypes


ERROR_ALREADY_EXISTS = 183


class AlreadyRunningError(RuntimeError):
    """Raised when another monitor process already owns the mutex."""


class WindowsMutex:
    def __init__(self, name: str) -> None:
        self._name = name
        self._handle = None

    def __enter__(self) -> "WindowsMutex":
        kernel32 = ctypes.windll.kernel32
        self._handle = kernel32.CreateMutexW(None, False, self._name)
        if not self._handle:
            raise OSError("Unable to create Windows monitor mutex")
        if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(self._handle)
            self._handle = None
            raise AlreadyRunningError("Another monitor run is still active")
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self._handle:
            ctypes.windll.kernel32.ReleaseMutex(self._handle)
            ctypes.windll.kernel32.CloseHandle(self._handle)
            self._handle = None
