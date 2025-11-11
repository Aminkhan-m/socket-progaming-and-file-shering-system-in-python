"""
@file server.py
@brief Multi-client file server for sharing files.

This server accepts multiple client connections at the same time and supports:
 - Uploading files to the server (PUT command)
 - Downloading files from the server (GET command)
 - Works with any file type: videos, audio, PDFs, images, text, etc.
 - Transfers files in chunks (4096 bytes), so it can handle large files safely.
"""

import socket
import threading
import pathlib
from typing import Tuple

# Number of bytes to send/receive in each chunk
BUFFER_SIZE = 4096


class FileServer:
    """
    A simple multi-threaded TCP file server.

    Each client is handled in its own thread, so multiple clients can upload or
    download files at the same time. All files are stored in a local directory
    on the server.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 5001, storage_dir: str = "server_files") -> None:
        """
        Create a new FileServer instance.

        :param host: IP address to bind to (default: "0.0.0.0" = all interfaces).
        :param port: TCP port number to listen on.
        :param storage_dir: Directory where files will be stored on the server.
        """
        self.host = host
        self.port = port
        self.storage_dir = pathlib.Path(storage_dir)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._stop_event = threading.Event()

        # Make sure the storage directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def start(self) -> None:
        """
        Start the file server and wait for client connections.

        The server:
         - Binds to (host, port)
         - Listens for incoming connections
         - Starts a new thread for every client
        """
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        print(f"[Server] Listening on {self.host}:{self.port}")
        print(f"[Server] Storage directory: {self.storage_dir.resolve()}")

        try:
            while not self._stop_event.is_set():
                client_sock, addr = self.sock.accept()
                print(f"[Server] New connection from {addr}")
                thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_sock, addr),
                    daemon=True,
                )
                thread.start()
        except KeyboardInterrupt:
            print("[Server] KeyboardInterrupt received. Stopping server...")
        finally:
            self.stop()

    def stop(self) -> None:
        """
        Stop the server and close the listening socket.
        """
        self._stop_event.set()
        try:
            self.sock.close()
        except Exception:
            pass
        print("[Server] Server stopped.")

    def _handle_client(self, client_sock: socket.socket, addr: Tuple[str, int]) -> None:
        """
        Handle a single client connection.

        The client sends one command line:
            GET <filename>
        or
            PUT <filename>

        Based on the command, we either send or receive a file.
        """
        with client_sock:
            try:
                command_line = self._recv_line(client_sock)
                if not command_line:
                    return

                parts = command_line.strip().split(" ", 1)
                command = parts[0].upper()
                filename = parts[1] if len(parts) > 1 else ""

                if command == "GET":
                    self._serve_get(client_sock, filename)
                elif command == "PUT":
                    self._serve_put(client_sock, filename)
                else:
                    client_sock.sendall(b"ERR Unknown command\n")
            except Exception as e:
                print(f"[Server] Error while handling {addr}: {e}")

    def _serve_get(self, client_sock: socket.socket, filename: str) -> None:
        """
        Handle a GET request: send a file to the client.

        Protocol:
          - Client sends:  GET <filename>\\n
          - Server replies:
              NOT_FOUND\\n              if file does not exist
              or
              FOUND <size>\\n           if file exists, followed by <size> bytes of file data
        """
        requested_path = pathlib.Path(filename)
        safe_path = (self.storage_dir / requested_path).resolve()

        # Simple protection against path traversal (.., etc.)
        storage_root = self.storage_dir.resolve()
        if not str(safe_path).startswith(str(storage_root)):
            client_sock.sendall(b"ERR Invalid filename\n")
            return

        if not safe_path.exists() or not safe_path.is_file():
            client_sock.sendall(b"NOT_FOUND\n")
            print(f"[Server] File not found: {filename}")
            return

        size = safe_path.stat().st_size
        client_sock.sendall(f"FOUND {size}\n".encode())

        # Send the file in chunks
        with open(safe_path, "rb") as f:
            while True:
                chunk = f.read(BUFFER_SIZE)
                if not chunk:
                    break
                client_sock.sendall(chunk)

        print(f"[Server] Sent file '{filename}' ({size} bytes).")

    def _serve_put(self, client_sock: socket.socket, filename: str) -> None:
        """
        Handle a PUT request: receive a file from the client.

        Protocol:
          - Client sends:  PUT <filename>\\n
          - Server replies: SEND_SIZE\\n
          - Client sends:  SIZE <number_of_bytes>\\n
                           followed by <number_of_bytes> bytes of file data
          - Server replies:
              OK\\n                    on success
              or
              ERR <message>\\n        on error
        """
        client_sock.sendall(b"SEND_SIZE\n")
        size_line = self._recv_line(client_sock)

        if not size_line or not size_line.startswith("SIZE "):
            client_sock.sendall(b"ERR Missing size\n")
            print("[Server] PUT failed: client did not send SIZE correctly.")
            return

        try:
            size_str = size_line.strip().split(" ", 1)[1]
            size = int(size_str)
        except Exception:
            client_sock.sendall(b"ERR Invalid size\n")
            print(f"[Server] PUT failed: invalid size line: {size_line}")
            return

        target_path = (self.storage_dir / pathlib.Path(filename)).resolve()
        target_path.parent.mkdir(parents=True, exist_ok=True)

        remaining = size
        with open(target_path, "wb") as f:
            while remaining > 0:
                chunk = client_sock.recv(min(BUFFER_SIZE, remaining))
                if not chunk:
                    break
                f.write(chunk)
                remaining -= len(chunk)

        if remaining == 0:
            client_sock.sendall(b"OK\n")
            print(f"[Server] Received file '{filename}' ({size} bytes).")
        else:
            client_sock.sendall(b"ERR Incomplete transfer\n")
            print(f"[Server] Incomplete upload of '{filename}'. Missing {remaining} bytes.")

    def _recv_line(self, sock: socket.socket) -> str:
        """
        Read a single line from the socket, terminated by '\\n'.

        Returns the line as a string without the newline at the end.
        If the connection closes before a newline is received, it
        returns whatever was read so far (or an empty string).
        """
        data = bytearray()
        while True:
            ch = sock.recv(1)
            if not ch:
                break
            if ch == b"\n":
                break
            data.extend(ch)
            if len(data) > 4096:
                break
        return data.decode(errors="ignore").strip()


if __name__ == "__main__":
    # Simple way to start the server:
    #   python server.py
    #
    # It will listen on 0.0.0.0:5001 and store files in the "server_files" folder.
    server = FileServer(host="0.0.0.0", port=5001, storage_dir="server_files")
    server.start()

