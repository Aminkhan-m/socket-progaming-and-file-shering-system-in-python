"""
@file server.py
@brief Multi-client file server for sharing files and text messages.

This server supports:
 - Uploading files to the server (PUT)
 - Downloading files from the server (GET)
 - Exchanging text messages with clients (MSG)
 - Handling multiple clients at the same time using threads
 - Works with any file type (video, audio, PDF, image, text)
"""

import socket
import threading
import pathlib
from typing import Tuple

BUFFER_SIZE = 4096


class FileServer:
    """A multi-threaded TCP server for file sharing and messaging."""

    def __init__(self, host: str = "0.0.0.0", port: int = 5001, storage_dir: str = "server_files") -> None:
        self.host = host
        self.port = port
        self.storage_dir = pathlib.Path(storage_dir)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._stop_event = threading.Event()
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def start(self) -> None:
        """Start the server and accept client connections."""
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        print(f"[Server] Listening on {self.host}:{self.port}")
        print(f"[Server] Storage directory: {self.storage_dir.resolve()}")

        try:
            while not self._stop_event.is_set():
                client_sock, addr = self.sock.accept()
                print(f"[Server] New connection from {addr}")
                thread = threading.Thread(target=self._handle_client, args=(client_sock, addr), daemon=True)
                thread.start()
        except KeyboardInterrupt:
            print("[Server] KeyboardInterrupt received. Stopping server...")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the server."""
        self._stop_event.set()
        try:
            self.sock.close()
        except Exception:
            pass
        print("[Server] Server stopped.")

    def _handle_client(self, client_sock: socket.socket, addr: Tuple[str, int]) -> None:
        """Handle one client connection."""
        with client_sock:
            try:
                command_line = self._recv_line(client_sock)
                if not command_line:
                    return

                parts = command_line.strip().split(" ", 1)
                command = parts[0].upper()
                rest = parts[1] if len(parts) > 1 else ""

                if command == "GET":
                    self._serve_get(client_sock, rest)
                elif command == "PUT":
                    self._serve_put(client_sock, rest)
                elif command == "MSG":
                    self._handle_message(client_sock, addr, rest)
                else:
                    client_sock.sendall(b"ERR Unknown command\n")
            except Exception as e:
                print(f"[Server] Error while handling {addr}: {e}")

    def _handle_message(self, client_sock: socket.socket, addr: Tuple[str, int], message: str) -> None:
        """Handle text messages sent from clients."""
        print(f"[Message from {addr}] {message}")
        reply = f"Server reply: Received your message -> {message}"
        client_sock.sendall((reply + "\n").encode())

    def _serve_get(self, client_sock: socket.socket, filename: str) -> None:
        """Send file to the client."""
        safe_path = (self.storage_dir / pathlib.Path(filename)).resolve()
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

        with open(safe_path, "rb") as f:
            while chunk := f.read(BUFFER_SIZE):
                client_sock.sendall(chunk)
        print(f"[Server] Sent '{filename}' ({size} bytes).")

    def _serve_put(self, client_sock: socket.socket, filename: str) -> None:
        """Receive file from the client."""
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
            print(f"[Server] Received '{filename}' ({size} bytes).")
        else:
            client_sock.sendall(b"ERR Incomplete transfer\n")

    def _recv_line(self, sock: socket.socket) -> str:
        """Read a single \\n-terminated line from the socket."""
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
    server = FileServer(host="0.0.0.0", port=5001, storage_dir="server_files")
    server.start()
