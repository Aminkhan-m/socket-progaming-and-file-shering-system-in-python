"""
Client for FileServer

Supports:
 - Chat messages (MSG) with the server
 - Uploading files (PUT)
 - Downloading files (GET)
"""

import socket
import pathlib

BUFFER_SIZE = 4096


class FileClient:
    def __init__(self, host="127.0.0.1", port=5001):
        self.host = host
        self.port = port

    def _connect(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.host, self.port))
        return sock

    def send_message_once(self, text: str):
        """Send a single message and print server reply."""
        with self._connect() as sock:
            sock.sendall(f"MSG {text}\n".encode())
            response = self._recv_line(sock)
            print(f"[Server] {response}")

    def chat(self):
        """
        Chat mode: let the user send multiple messages to the server.
        Each message is sent as MSG <text>, reply is printed.
        Type 'exit' to leave chat mode.
        """
        print("\n[Chat] Type your messages. Type 'exit' to stop.\n")
        while True:
            text = input("You: ").strip()
            if text.lower() in ("exit", "quit"):
                print("[Chat] Leaving chat mode.\n")
                break

            # For each message we open a short connection (simple and safe)
            with self._connect() as sock:
                sock.sendall(f"MSG {text}\n".encode())
                reply = self._recv_line(sock)
                print(f"Server: {reply}")

    def upload_file(self, local_path, remote_name=None):
        """Upload file to the server."""
        path = pathlib.Path(local_path)
        if not path.exists() or not path.is_file():
            print("[Client] File not found.")
            return

        if remote_name is None:
            remote_name = path.name

        size = path.stat().st_size

        with self._connect() as sock:
            sock.sendall(f"PUT {remote_name}\n".encode())

            response = self._recv_line(sock)
            if response != "SEND_SIZE":
                print("[Client] Unexpected server response:", response)
                return

            sock.sendall(f"SIZE {size}\n".encode())

            with open(path, "rb") as f:
                while True:
                    chunk = f.read(BUFFER_SIZE)
                    if not chunk:
                        break
                    sock.sendall(chunk)

            status = self._recv_line(sock)
            print(f"[Client] {status}")

    def download_file(self, remote_name, local_name=None):
        """Download file from the server."""
        if local_name is None:
            local_name = remote_name

        with self._connect() as sock:
            sock.sendall(f"GET {remote_name}\n".encode())
            response = self._recv_line(sock)

            if not response:
                print("[Client] No response from server.")
                return

            if response.startswith("NOT_FOUND"):
                print("[Client] File not found on server.")
                return

            if not response.startswith("FOUND "):
                print("[Client] Unexpected response:", response)
                return

            try:
                size = int(response.split(" ", 1)[1])
            except Exception:
                print("[Client] Invalid size in response:", response)
                return

            remaining = size
            with open(local_name, "wb") as f:
                while remaining > 0:
                    chunk = sock.recv(min(BUFFER_SIZE, remaining))
                    if not chunk:
                        break
                    f.write(chunk)
                    remaining -= len(chunk)

            if remaining == 0:
                print(f"[Client] Downloaded '{local_name}' ({size} bytes).")
            else:
                print("[Client] Download incomplete.")

    @staticmethod
    def _recv_line(sock):
        data = bytearray()
        while True:
            ch = sock.recv(1)
            if not ch or ch == b"\n":
                break
            data.extend(ch)
        return data.decode(errors="ignore").strip()


if __name__ == "__main__":
    client = FileClient(host="127.0.0.1", port=5001)

    while True:
        print("\n--- CLIENT MENU ---")
        print("1) Chat with server (send text messages)")
        print("2) Upload file to server")
        print("3) Download file from server")
        print("4) Exit")
        choice = input("Enter choice (1-4): ").strip()

        if choice == "1":
            client.chat()

        elif choice == "2":
            path = input("Enter local file path to upload: ").strip()
            name = input("Enter name to save on server (or press Enter to use same name): ").strip()
            client.upload_file(path, name if name else None)

        elif choice == "3":
            server_name = input("Enter filename on server: ").strip()
            local_name = input("Enter local save name (or press Enter to use same name): ").strip()
            client.download_file(server_name, local_name if local_name else None)

        elif choice == "4":
            print("Goodbye!")
            break

        else:
            print("Invalid choice. Please try again.")
