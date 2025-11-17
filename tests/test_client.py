import pytest
from unittest.mock import MagicMock, patch
from client_code import FileClient

# -----------------------------
# Test _recv_line()
# -----------------------------
def test_recv_line_basic():
    mock_sock = MagicMock()
    mock_sock.recv = MagicMock(side_effect=[b'H', b'e', b'l', b'l', b'o', b'\n'])

    client = FileClient()
    result = client._recv_line(mock_sock)

    assert result == "Hello"


def test_recv_line_empty():
    mock_sock = MagicMock()
    mock_sock.recv = MagicMock(return_value=b"")

    client = FileClient()
    result = client._recv_line(mock_sock)

    assert result == ""


# -----------------------------
# Test download_file(): file not found
# -----------------------------
@patch("socket.socket")
def test_download_file_not_found(mock_socket_class, tmp_path):
    mock_sock = MagicMock()
    mock_socket_class.return_value = mock_sock

    # simulate server response: NOT_FOUND
    mock_sock.recv = MagicMock(
        side_effect=[
            b'N', b'O', b'T', b'_', b'F', b'O', b'U', b'N', b'D', b'\n'
        ]
    )

    client = FileClient()

    client.download_file("abc.txt", local_path=str(tmp_path / "dl.txt"))
    # No exception = ok
