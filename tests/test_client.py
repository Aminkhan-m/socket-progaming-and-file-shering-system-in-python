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
    # 模拟一个 socket 对象
    mock_sock = MagicMock()

    # 让 socket() 返回这个 mock
    mock_socket_class.return_value = mock_sock

    # 让 with socket as s: 能正常工作
    mock_sock.__enter__.return_value = mock_sock
    mock_sock.__exit__.return_value = False

    # 模拟 connect()
    mock_sock.connect = MagicMock()

    # 模拟 server 响应: NOT_FOUND\n
    mock_sock.recv = MagicMock(
        side_effect=[
            b'N', b'O', b'T', b'_', b'F', b'O', b'U', b'N', b'D', b'\n',
            b''  # 防止阻塞
        ]
    )

    client = FileClient()

    # 执行下载（不应该抛异常）
    client.download_file("abc.txt", local_path=str(tmp_path / "dl.txt"))

    # 文件不应该被创建
    assert not (tmp_path / "dl.txt").exists()
