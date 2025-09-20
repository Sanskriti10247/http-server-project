#!/usr/bin/env python3
import socket
import threading
import queue
import os
import json
import datetime
import argparse
from urllib.parse import unquote

# ------------------ Server Configuration ------------------
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
DEFAULT_THREAD_POOL_SIZE = 10
RESOURCE_DIR = os.path.join(os.getcwd(), "resources")
MAX_REQUEST_SIZE = 8192
MAX_CONNECTIONS = 50
KEEP_ALIVE_TIMEOUT = 30
MAX_KEEP_ALIVE_REQUESTS = 100

connection_queue = queue.Queue(maxsize=MAX_CONNECTIONS)


# ------------------ Logging ------------------
def log(message):
    now = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    print(f"{now} {message}")


# ------------------ HTTP Helpers ------------------
def rfc7231_date():
    """Return current date in RFC 7231 format (timezone-aware)."""
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S GMT"
    )


def make_response(status, headers=None, body=b"", keep_alive=False):
    """Build raw HTTP response."""
    reason_phrases = {
        200: "OK",
        201: "Created",
        400: "Bad Request",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        415: "Unsupported Media Type",
        500: "Internal Server Error",
        503: "Service Unavailable",
    }
    reason = reason_phrases.get(status, "Unknown")
    response = [f"HTTP/1.1 {status} {reason}"]
    if not headers:
        headers = {}

    # Standard headers
    headers.setdefault("Date", rfc7231_date())
    headers.setdefault("Server", "Multi-threaded HTTP Server")
    headers.setdefault("Content-Length", str(len(body)))

    # Connection headers
    if keep_alive:
        headers.setdefault("Connection", "keep-alive")
        headers.setdefault(
            "Keep-Alive", f"timeout={KEEP_ALIVE_TIMEOUT}, max={MAX_KEEP_ALIVE_REQUESTS}"
        )
    else:
        headers.setdefault("Connection", "close")

    # Build headers
    for k, v in headers.items():
        response.append(f"{k}: {v}")
    response.append("")

    # Encode
    response_bytes = "\r\n".join(response).encode("utf-8") + b"\r\n" + body
    return response_bytes


def safe_path(path):
    """Prevent path traversal attacks and absolute paths."""
    decoded = unquote(path).lstrip("/")

    # Block attempts to go above RESOURCE_DIR
    forbidden_patterns = ["..", "~", "//", "\\", ":"]
    for pattern in forbidden_patterns:
        if pattern in decoded:
            return None

    target = os.path.normpath(os.path.join(RESOURCE_DIR, decoded))
    # Ensure target stays inside RESOURCE_DIR
    if not target.startswith(RESOURCE_DIR):
        return None

    return target


# ------------------ Worker Thread ------------------
class Worker(threading.Thread):
    def __init__(self, thread_id, host, port):
        super().__init__(daemon=True)
        self.thread_id = thread_id
        self.host = host
        self.port = port

    def run(self):
        while True:
            client_socket, client_address = connection_queue.get()
            try:
                self.handle_client(client_socket, client_address)
            except Exception as e:
                log(f"[Thread-{self.thread_id}] Error: {e}")
            finally:
                client_socket.close()
                connection_queue.task_done()

    def handle_client(self, client_socket, client_address):
        log(f"[Thread-{self.thread_id}] Connection from {client_address}")
        client_socket.settimeout(KEEP_ALIVE_TIMEOUT)

        requests_handled = 0
        keep_alive = True

        while keep_alive and requests_handled < MAX_KEEP_ALIVE_REQUESTS:
            try:
                request_data = client_socket.recv(MAX_REQUEST_SIZE)
                if not request_data:
                    break

                request_text = request_data.decode("utf-8", errors="ignore")
                lines = request_text.split("\r\n")
                if len(lines) < 1:
                    client_socket.sendall(make_response(400))
                    return

                # Parse request line
                try:
                    method, path, version = lines[0].split()
                except ValueError:
                    client_socket.sendall(make_response(400))
                    return

                # Parse headers
                headers = {}
                for line in lines[1:]:
                    if not line:
                        break
                    if ":" in line:
                        key, value = line.split(":", 1)
                        headers[key.strip()] = value.strip()

                # Host header validation
                host_header = headers.get("Host", "").strip()
                if "Host" not in headers or host_header == "":
                    log(f"[Thread-{self.thread_id}] Missing or empty Host header ❌")
                    client_socket.sendall(make_response(400))
                    return

                expected_host = f"{self.host}:{self.port}"
                if headers["Host"] not in [
                    expected_host,
                    "localhost:" + str(self.port),
                    "127.0.0.1:" + str(self.port),
                ]:
                    log(f"[Thread-{self.thread_id}] Host mismatch: {headers['Host']} ❌")
                    client_socket.sendall(make_response(403))
                    return
                else:
                    log(f"[Thread-{self.thread_id}] Host validation: {headers['Host']} ✓")

                # Connection handling
                conn_header = headers.get("Connection", "").lower()
                if version == "HTTP/1.1" and conn_header != "close":
                    keep_alive = True
                elif version == "HTTP/1.0" and conn_header == "keep-alive":
                    keep_alive = True
                else:
                    keep_alive = False

                # Dispatch request
                if method == "GET":
                    self.handle_get(client_socket, path, headers, keep_alive)
                elif method == "POST":
                    self.handle_post(
                        client_socket, path, headers, request_text, request_data, keep_alive
                    )
                else:
                    client_socket.sendall(make_response(405, keep_alive=keep_alive))

                requests_handled += 1

            except socket.timeout:
                log(f"[Thread-{self.thread_id}] Keep-Alive timeout reached, closing connection")
                break

    # --- GET handler ---
    def handle_get(self, client_socket, path, headers, keep_alive):
        log(f"[Thread-{self.thread_id}] Request: GET {path}")

        # Disallowed files (explicit)
        disallowed_files = ["/config", "/.env", "/secret.txt"]
        if path in disallowed_files:
            log(f"[Thread-{self.thread_id}] Forbidden file access attempt: {path} ❌")
            client_socket.sendall(make_response(403, keep_alive=keep_alive))
            return

        if path == "/":
            path = "/index.html"

        target = safe_path(path)

        if not target:
            log(f"[Thread-{self.thread_id}] Forbidden path attempt: {path} ❌")
            client_socket.sendall(make_response(403, keep_alive=keep_alive))
            return
        elif not os.path.exists(target):
            log(f"[Thread-{self.thread_id}] File not found: {path} ❌")
            client_socket.sendall(make_response(404, keep_alive=keep_alive))
            return

        ext = os.path.splitext(target)[1].lower()
        if ext == ".html":
            content_type = "text/html; charset=utf-8"
            with open(target, "rb") as f:
                body = f.read()
            response = make_response(200, {"Content-Type": content_type}, body, keep_alive)
        elif ext in [".png", ".jpg", ".jpeg", ".txt"]:
            filename = os.path.basename(target)
            with open(target, "rb") as f:
                body = f.read()
            response = make_response(
                200,
                {
                    "Content-Type": "application/octet-stream",
                    "Content-Disposition": f'attachment; filename="{filename}"',
                },
                body,
                keep_alive,
            )
            log(f"[Thread-{self.thread_id}] Sending binary file: {filename} ({len(body)} bytes)")
        else:
            response = make_response(415, keep_alive=keep_alive)

        client_socket.sendall(response)

    # --- POST handler ---
    def handle_post(self, client_socket, path, headers, request_text, request_data, keep_alive):
        log(f"[Thread-{self.thread_id}] Request: POST {path}")

        if "Content-Type" not in headers or headers["Content-Type"] != "application/json":
            client_socket.sendall(make_response(415, keep_alive=keep_alive))
            return

        try:
            body = request_text.split("\r\n\r\n", 1)[1]
            data = json.loads(body)
        except Exception:
            client_socket.sendall(make_response(400, keep_alive=keep_alive))
            return

        # Save to uploads
        os.makedirs(os.path.join(RESOURCE_DIR, "uploads"), exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"upload_{timestamp}.json"
        filepath = os.path.join(RESOURCE_DIR, "uploads", filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        log(f"[Thread-{self.thread_id}] File created: /uploads/{filename}")

        response_body = json.dumps(
            {
                "status": "success",
                "message": "File created successfully",
                "filepath": f"/uploads/{filename}",
            }
        ).encode("utf-8")
        response = make_response(
            201, {"Content-Type": "application/json"}, response_body, keep_alive
        )
        client_socket.sendall(response)


# ------------------ Main Server ------------------
def start_server(host, port, pool_size):
    os.makedirs(os.path.join(RESOURCE_DIR, "uploads"), exist_ok=True)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(MAX_CONNECTIONS)

    log(f"HTTP Server started on http://{host}:{port}")
    log(f"Thread pool size: {pool_size}")
    log(f"Serving files from '{RESOURCE_DIR}' directory")
    log("Press Ctrl+C to stop the server")

    # Start worker threads
    for i in range(pool_size):
        Worker(i + 1, host, port).start()

    # Accept loop
    try:
        while True:
            client_socket, client_address = server_socket.accept()
            try:
                connection_queue.put((client_socket, client_address), block=False)
            except queue.Full:
                log("Warning: Thread pool saturated, dropping connection")
                client_socket.sendall(make_response(503, {"Retry-After": "5"}))
                client_socket.close()
    except KeyboardInterrupt:
        log("Shutting down server...")
        server_socket.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-threaded HTTP Server")
    parser.add_argument("port", nargs="?", type=int, default=DEFAULT_PORT)
    parser.add_argument("host", nargs="?", type=str, default=DEFAULT_HOST)
    parser.add_argument(
        "threads", nargs="?", type=int, default=DEFAULT_THREAD_POOL_SIZE
    )
    args = parser.parse_args()

    start_server(args.host, args.port, args.threads)
