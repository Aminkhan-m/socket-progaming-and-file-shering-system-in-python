
"""
@file server.py
@brief Multi-client file server for sharing files.
@details
This server supports:
 - Multiple concurrent clients (each in its own thread).
 - Uploading (PUT) files to server.
 - Downloading (GET) files from server.
 - Handles all file types: video, audio, PDF, images, text.
 - Transfers files in chunks (4096 bytes) to support large files.
"""

import socket
import threading
import pathlib
from typing import Tuple

# Buffer size for each chunk transfer
BUFFER_SIZE = 4096


class FileServer:
    """
    @class FileServer
    @brief A multi-threaded TCP file server.
    @details
    - Accepts multiple clients simultaneously.
    - Supports GET and PUT commands.
    - Stores files in a local directory.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 5001, storage_dir: str = "server_files"):
        """
        @brief Construct a FileServer.
        @param host Host IP address to bind (default: all interfaces).
        @param port Port number to listen on.
        @param storage_dir Directory where uploaded/downloaded files are stored.
        """
        self.host = host
        self.port = port
        self.storage_dir = pathlib.Path(storage_dir)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._stop_event = threading.Event()

        # Ensure storage directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def start(self):
        """
        @brief Start the server and accept client connections.
        @details
        - Binds the socket to host:port.
        - Listens for incoming connections.
        - Each client is handled in its own thread.
        """
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        print(f"[Server] Listening on {self.host}:{self.port}, storage: {self.storage_dir.resolve()}")

        try:
            while not self._stop_event.is_set():
                client_sock, addr = self.sock.accept()
                print(f"[Server] Accepted connection from {addr}")
                thread = threading.Thread(target=self._handle_client, args=(client_sock, addr), daemon=True)
                thread.start()
        except KeyboardInterrupt:
            print("[Server] KeyboardInterrupt received — stopping.")
        finally:
            self.stop()

    def stop(self):
        """
        @brief Stop the server and close the listening socket.
        """
        self._stop_event.set()
        try:
            self.sock.close()
        except Exception:
            pass
        print("[Server] Stopped.")

    def _handle_client(self, client_sock: socket.socket, addr: Tuple[str, int]):
        """
        @brief Handle a single client connection.
        @param client_sock The socket object for this client.
        @param addr The client address tuple (IP, port).
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
                print(f"[Server] Exception handling {addr}: {e}")

    def _serve_get(self, client_sock: socket.socket, filename: str):
        """
        @brief Serve a GET request (send file to client).
        @param client_sock Connected client socket.
        @param filename Name of the requested file.
        """
        safe_path = (self.storage_dir / pathlib.Path(filename)).resolve()

        if not str(safe_path).startswith(str(self.storage_dir.resolve())):
            client_sock.sendall(b"ERR Invalid filename\n")
            return

        if not safe_path.exists() or not safe_path.is_file():
            client_sock.sendall(b"NOT_FOUND\n")
            return

        size = safe_path.stat().st_size
        client_sock.sendall(f"FOUND {size}\n".encode())

        with open(safe_path, "rb") as f:
            while chunk := f.read(BUFFER_SIZE):
                client_sock.sendall(chunk)

        print(f"[Server] Sent {filename} ({size} bytes).")

    def _serve_put(self, client_sock: socket.socket, filename: str):
        """
        @brief Serve a PUT request (receive file from client).
        @param client_sock Connected client socket.
        @param filename Name of the file to save on the server.
        """
        client_sock.sendall(b"SEND_SIZE\n")
        size_line = self._recv_line(client_sock)
        if not size_line or not size_line.startswith("SIZE "):
            client_sock.sendall(b"ERR Missing size\n")
            return

        try:
            size = int(size_line.strip().split(" ", 1)[1])
        except Exception:
            client_sock.sendall(b"ERR Invalid size\n")
            return

        safe_path = (self.storage_dir / pathlib.Path(filename)).resolve()
        safe_path.parent.mkdir(parents=True, exist_ok=True)

        remaining = size
        with open(safe_path, "wb") as f:
            while remaining > 0:
                chunk = client_sock.recv(min(BUFFER_SIZE, remaining))
                if not chunk:
                    break
                f.write(chunk)
                remaining -= len(chunk)

        if remaining == 0:
            client_sock.sendall(b"OK\n")
            print(f"[Server] Received {filename} ({size} bytes).")
        else:
            client_sock.sendall(b"ERR Incomplete transfer\n")

    def _recv_line(self, sock: socket.socket) -> str:
        """
        @brief Read a line (terminated with \n) from a socket.
        @param sock The socket to read from.
        @return The decoded line as string.
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
        return data.decode(errors="ignore")


if __name__ == "__main__":
    """
    Quick manual demo:
    Run: python server.py
    """
    server = FileServer(host="0.0.0.0", port=5001, storage_dir="server_files")
    server.start()
