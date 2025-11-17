# Directory: tests/
# File: test_server_recv_line.py
# Pytest unit tests for the FileServer._recv_line method

import socket
import types
import pytest
from server_code import FileServer

class FakeSocket:
    """A fake socket that returns predefined bytes for recv()."""
def __init__(self, data: bytes):
    self._data = data
    self._index = 0

def recv(self, n: int) -> bytes:
    if self._index >= len(self._data):
        return b""
    chunk = self._data[self._index : self._index + n]
    self._index += n
    return chunk

def test_recv_line_normal():
    """Test receiving a normal line ending with \n."""
    fake = FakeSocket(b"Hello World\nExtra")
    server = FileServer()
    result = server._recv_line(fake)
    assert result == "Hello World"

def test_recv_line_no_newline():
    """Test behavior when no newline is found (socket closes)."""
    fake = FakeSocket(b"Partial line with no newline")
    server = FileServer()
    result = server._recv_line(fake)
    assert result == "Partial line with no newline"

def test_recv_line_empty():
    """Test receiving empty input."""
    fake = FakeSocket(b"")
    server = FileServer()
    result = server._recv_line(fake)
    assert result == ""

def test_recv_line_long_line():
    """Test max length behavior (>4096 chars)."""
    long_data = b"A" * 5000  # longer than the limit
    fake = FakeSocket(long_data)
    server = FileServer()
    result = server._recv_line(fake) # Should truncate at 4096 chars
    assert len(result) == 4096
    assert result == "A" * 4096
