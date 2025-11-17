import pytest
from unittest.mock import MagicMock
from server_code import FileServer

# -----------------------------
# Test _recv_line()
# -----------------------------
def test_server_recv_line_basic():
    mock_sock = MagicMock()
    mock_sock.recv = MagicMock(side_effect=[b'G', b'E', b'T', b'\n'])

    server = FileServer()
    line = server._recv_line(mock_sock)

    assert line == "GET"


# -----------------------------
# Test PUT with invalid SIZE line
# -----------------------------
def test_server_put_invalid_size(tmp_path):
    server = FileServer(storage_dir=tmp_path)

    mock_sock = MagicMock()

    # First server will read "SIZE ???"
    mock_sock.recv = MagicMock(
        side_effect=[
            b'S', b'I', b'Z', b'E', b' ', b'x', b'\n'  # invalid integer
        ]
    )

    server._serve_put(mock_sock, "test.bin")

    # Server must send error
    mock_sock.sendall.assert_any_call(b"ERR Invalid size\n")
