"""
@file client.py
@brief TCP client for uploading and downloading files to/from the FileServer.

This client connects to the FileServer over TCP and allows:
 - Uploading files (PUT command)
 - Downloading files (GET command)
 - Works with all file types: videos, audio, PDFs, images, and text
 - Handles large files by sending and receiving data in chunks (4096 bytes)

Example usage:

  # Download a file from the server
  python client.py --host 127.0.0.1 --port 5001 get report.pdf

  # Upload a local file to the server
  python client.py --host 127.0.0.1 --port 5001 put video.mp4
"""

import socket
import pathlib
from typing import Optional

BUFFER_SIZE = 4096  # number of bytes to send or receive per chunk


class FileClient:
    """
    A simple TCP client that can connect to the FileServer
    to upload and download files.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 5001) -> None:
        self.host = host
        self.port = port

    def _connect(self) -> socket.socket:
        """Establish a connection to the FileServer and return the socket."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.host, self.port))
        return sock

    def download_file(self, remote_name: str, local_path: Optional[str] = None) -> None:
        """
        Download a file from the server using the GET command.

        :param remote_name: Name of the file on the server.
        :param local_path: Optional local filename to save it as.
        """
        if local_path is None:
            local_path = remote_name

        local_path = str(local_path)

        with self._connect() as sock:
            # Ask the server for the file
            sock.sendall(f"GET {remote_name}\n".encode())

            # Wait for the server’s response
            response = self._recv_line(sock)
            if not response:
                print("[Client] No response from server.")
                return

            if response.startswith("NOT_FOUND"):
                print(f"[Client] The file '{remote_name}' does not exist on the server.")
                return

            if not response.startswith("FOUND "):
                print(f"[Client] Unexpected response: {response}")
                return

            # Extract file size
            try:
                size = int(response.strip().split(" ", 1)[1])
            except Exception:
                print(f"[Client] Invalid size in response: {response}")
                return

            remaining = size
            path_obj = pathlib.Path(local_path)
            path_obj.parent.mkdir(parents=True, exist_ok=True)

            # Receive file data
            with open(path_obj, "wb") as f:
                while remaining > 0:
                    chunk = sock.recv(min(BUFFER_SIZE, remaining))
                    if not chunk:
                        break
                    f.write(chunk)
                    remaining -= len(chunk)

            if remaining == 0:
                print(f"[Client] Download complete: '{local_path}' ({size} bytes).")
            else:
                print("[Client] Download incomplete or interrupted.")

    def upload_file(self, local_path: str, remote_name: Optional[str] = None) -> None:
        """
        Upload a local file to the server using the PUT command.

        :param local_path: Path to the file on your computer.
        :param remote_name: Optional name to save as on the server.
        """
        path_obj = pathlib.Path(local_path)
        if not path_obj.exists() or not path_obj.is_file():
            print(f"[Client] Local file not found: {local_path}")
            return

        if remote_name is None:
            remote_name = path_obj.name

        file_size = path_obj.stat().st_size

        with self._connect() as sock:
            # Tell the server we want to upload
            sock.sendall(f"PUT {remote_name}\n".encode())

            # Wait for the server to ask for the file size
            response = self._recv_line(sock)
            if response != "SEND_SIZE":
                print(f"[Client] Unexpected response: {response}")
                return

            # Send the size and start transferring the file
            sock.sendall(f"SIZE {file_size}\n".encode())

            with open(path_obj, "rb") as f:
                remaining = file_size
                while remaining > 0:
                    chunk = f.read(BUFFER_SIZE)
                    if not chunk:
                        break
                    sock.sendall(chunk)
                    remaining -= len(chunk)

            # Wait for confirmation
            status = self._recv_line(sock)
            if status == "OK":
                print(f"[Client] Upload complete: '{local_path}' ({file_size} bytes).")
            else:
                print(f"[Client] Server reported an error: {status}")

    @staticmethod
    def _recv_line(sock: socket.socket) -> str:
        """Read one line from the server, terminated with '\\n'."""
        data = bytearray()
        while True:
            ch = sock.recv(1)
            if not ch or ch == b"\n":
                break
            data.extend(ch)
            if len(data) > 4096:
                break
        return data.decode(errors="ignore").strip()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Client for the FileServer (GET / PUT).")
    parser.add_argument("--host", default="127.0.0.1", help="Server IP address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5001, help="Server port number (default: 5001)")
    parser.add_argument("command", choices=["get", "put"], help="Choose 'get' to download or 'put' to upload")
    parser.add_argument("source", help="File path (for 'put') or filename (for 'get')")
    parser.add_argument("dest", nargs="?", help="Optional: rename output file or destination name")

    args = parser.parse_args()
    client = FileClient(host=args.host, port=args.port)

    if args.command == "get":
        client.download_file(remote_name=args.source, local_path=args.dest)
    else:
        client.upload_file(local_path=args.source, remote_name=args.dest)



