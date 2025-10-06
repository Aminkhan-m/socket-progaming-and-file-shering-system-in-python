"""
@file client.py
@brief TCP client for file sharing.
@details
Supports:
 - Uploading (PUT) local files to server.
 - Downloading (GET) files from server.
 - Works with all file types (text, image, video, audio, PDF).
"""

import socket
import pathlib

BUFFER_SIZE = 4096


class FileClient:
    """
    @class FileClient
    @brief TCP client for uploading/downloading files.
    """

    def __init__(self, server_host: str = "127.0.0.1", server_port: int = 5001, download_dir: str = "downloads"):
        """
        @brief Construct a FileClient.
        @param server_host The server's IP address.
        @param server_port The server's port number.
        @param download_dir Directory to save downloaded files.
        """
        self.server_host = server_host
        self.server_port = server_port
        self.download_dir = pathlib.Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def request_file(self, filename: str):
        """
        @brief Request (download) a file from server.
        @param filename The name of the file to download.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.server_host, self.server_port))
            s.sendall(f"GET {filename}\n".encode())

            header = self._recv_line(s)
            if not header:
                print("[Client] No response from server.")
                return

            if header.strip() == "NOT_FOUND":
                print(f"[Client] File {filename} not found on server.")
                return

            if header.startswith("FOUND "):
                size = int(header.split(" ", 1)[1])
                out_path = self.download_dir / f"downloaded_{pathlib.Path(filename).name}"
                remaining = size
                with open(out_path, "wb") as f:
                    while remaining > 0:
                        chunk = s.recv(min(BUFFER_SIZE, remaining))
                        if not chunk:
                            break
                        f.write(chunk)
                        remaining -= len(chunk)

                if remaining == 0:
                    print(f"[Client] Downloaded {filename} -> {out_path} ({size} bytes).")
                else:
                    print(f"[Client] Download incomplete: {remaining} bytes missing.")
            else:
                print(f"[Client] Unexpected response: {header}")

    def upload_file(self, local_path: str, remote_name: str = None):
        """
        @brief Upload a local file to the server.
        @param local_path The path to the file on client.
        @param remote_name Optional new name for saving on server.
        """
        lp = pathlib.Path(local_path)
        if not lp.exists() or not lp.is_file():
            print(f"[Client] Local file not found: {local_path}")
            return

        remote_name = remote_name or lp.name
        size = lp.stat().st_size

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.server_host, self.server_port))
            s.sendall(f"PUT {remote_name}\n".encode())

            resp = self._recv_line(s)
            if resp.strip() != "SEND_SIZE":
                print(f"[Client] Unexpected server response: {resp}")
                return

            s.sendall(f"SIZE {size}\n".encode())

            with open(lp, "rb") as f:
                while chunk := f.read(BUFFER_SIZE):
                    s.sendall(chunk)

            final = self._recv_line(s)
            print(f"[Client] Server response: {final.strip()}")

    def _recv_line(self, sock: socket.socket) -> str:
        """
        @brief Read a line from socket (until newline).
        @param sock Socket connection to server.
        @return Decoded string line.
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
    - Upload:   python client.py put localfile.mp4
    - Download: python client.py get report.pdf
    """
    import sys

    if len(sys.argv) >= 3 and sys.argv[1] == "get":
        filename = sys.argv[2]
        client = FileClient()
        client.request_file(filename)

    elif len(sys.argv) >= 3 and sys.argv[1] == "put":
        local = sys.argv[2]
        remote = sys.argv[3] if len(sys.argv) >= 4 else None
        client = FileClient()
        client.upload_file(local, remote)

    else:
        print("Usage:")
        print("  python client.py get <filename_on_server>")
        print("  python client.py put <local_path> [remote_name]")
