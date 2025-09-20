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
# Default host (localhost) and port
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080

# Default number of worker threads
DEFAULT_THREAD_POOL_SIZE = 10

# Directory from which files will be served
RESOURCE_DIR = os.path.join(os.getcwd(), "resources")

# Maximum size for a single HTTP request (in bytes)
MAX_REQUEST_SIZE = 8192

# Maximum number of connections allowed in the waiting queue
MAX_CONNECTIONS = 50

# Timeout for keep-alive connections (seconds)
KEEP_ALIVE_TIMEOUT = 30

# Maximum number of requests allowed per keep-alive connection
MAX_KEEP_ALIVE_REQUESTS = 100

# Thread-safe queue to hold incoming client connections
connection_queue = queue.Queue(maxsize=MAX_CONNECTIONS)


# ------------------ Logging Utility ------------------
def log(message):
    """
    Prints messages to console with a timestamp.
    Helps in tracking requests and server activity.
    """
    now = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    print(f"{now} {message}")


# ------------------ HTTP Helper Functions ------------------
def rfc7231_date():
    """
    Return the current date in HTTP standard format (RFC 7231)
    Required for 'Date' header in HTTP responses.
    """
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S GMT"
    )


def make_response(status, headers=None, body=b"", keep_alive=False):
    """
    Build a raw HTTP response to send to the client.

    Args:
        status: HTTP status code (e.g., 200, 404)
        headers: Optional dictionary of HTTP headers
        body: Response body in bytes
        keep_alive: Whether connection should remain open

    Returns:
        Encoded HTTP response (bytes)
    """
    # Mapping of common HTTP status codes to reason phrases
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
    response = [f"HTTP/1.1 {status} {reason}"]  # Start with status line

    # Ensure headers dictionary exists
    if not headers:
        headers = {}

    # Add standard headers
    headers.setdefault("Date", rfc7231_date())
    headers.setdefault("Server", "Multi-threaded HTTP Server")
    headers.setdefault("Content-Length", str(len(body)))

    # Add connection headers depending on keep-alive
    if keep_alive:
        headers.setdefault("Connection", "keep-alive")
        headers.setdefault(
            "Keep-Alive", f"timeout={KEEP_ALIVE_TIMEOUT}, max={MAX_KEEP_ALIVE_REQUESTS}"
        )
    else:
        headers.setdefault("Connection", "close")

    # Convert headers dictionary to HTTP header lines
    for k, v in headers.items():
        response.append(f"{k}: {v}")
    response.append("")  # End of headers

    # Combine headers and body
    response_bytes = "\r\n".join(response).encode("utf-8") + b"\r\n" + body
    return response_bytes


def safe_path(path):
    """
    Safely resolve a requested path to prevent path traversal attacks.

    Args:
        path: URL path requested by client

    Returns:
        Absolute filesystem path if safe; None if unsafe
    """
    decoded = unquote(path).lstrip("/")  # Decode URL and remove leading /

    # Block unsafe patterns that may allow escaping RESOURCE_DIR
    forbidden_patterns = ["..", "~", "//", "\\", ":"]
    for pattern in forbidden_patterns:
        if pattern in decoded:
            return None

    # Build absolute path
    target = os.path.normpath(os.path.join(RESOURCE_DIR, decoded))
    
    # Ensure the target is inside RESOURCE_DIR
    if not target.startswith(RESOURCE_DIR):
        return None

    return target


# ------------------ Worker Thread Class ------------------
class Worker(threading.Thread):
    """
    Worker thread that continuously handles client connections
    from the shared connection queue.
    """

    def __init__(self, thread_id, host, port):
        super().__init__(daemon=True)  # Daemon threads exit when main thread exits
        self.thread_id = thread_id
        self.host = host
        self.port = port

    def run(self):
        """
        Main loop: continuously fetch connections from the queue
        and process requests.
        """
        while True:
            # Wait for a connection from the queue
            client_socket, client_address = connection_queue.get()
            try:
                self.handle_client(client_socket, client_address)
            except Exception as e:
                log(f"[Thread-{self.thread_id}] Error: {e}")
            finally:
                # Ensure socket is closed and queue task is marked done
                client_socket.close()
                connection_queue.task_done()

    def handle_client(self, client_socket, client_address):
        """
        Handles multiple requests from a single client (if keep-alive)
        """
        log(f"[Thread-{self.thread_id}] Connection from {client_address}")
        client_socket.settimeout(KEEP_ALIVE_TIMEOUT)

        requests_handled = 0
        keep_alive = True

        while keep_alive and requests_handled < MAX_KEEP_ALIVE_REQUESTS:
            try:
                # Receive HTTP request from client
                request_data = client_socket.recv(MAX_REQUEST_SIZE)
                if not request_data:
                    break  # Client disconnected

                request_text = request_data.decode("utf-8", errors="ignore")
                lines = request_text.split("\r\n")  # Split request into lines

                if len(lines) < 1:
                    client_socket.sendall(make_response(400))
                    return

                # ---------------- Parse request line ----------------
                try:
                    method, path, version = lines[0].split()
                except ValueError:
                    client_socket.sendall(make_response(400))
                    return

                # ---------------- Parse headers ----------------
                headers = {}
                for line in lines[1:]:
                    if not line:  # Empty line separates headers from body
                        break
                    if ":" in line:
                        key, value = line.split(":", 1)
                        headers[key.strip()] = value.strip()

                # ---------------- Host header validation ----------------
                host_header = headers.get("Host", "").strip()
                if "Host" not in headers or host_header == "":
                    log(f"[Thread-{self.thread_id}] Missing Host header ❌")
                    client_socket.sendall(make_response(400))
                    return

                # Allow only expected host names
                expected_host = f"{self.host}:{self.port}"
                if headers["Host"] not in [expected_host, "localhost:" + str(self.port), "127.0.0.1:" + str(self.port)]:
                    log(f"[Thread-{self.thread_id}] Host mismatch: {headers['Host']} ❌")
                    client_socket.sendall(make_response(403))
                    return
                else:
                    log(f"[Thread-{self.thread_id}] Host validation ✓")

                # ---------------- Connection management ----------------
                conn_header = headers.get("Connection", "").lower()
                if version == "HTTP/1.1" and conn_header != "close":
                    keep_alive = True
                elif version == "HTTP/1.0" and conn_header == "keep-alive":
                    keep_alive = True
                else:
                    keep_alive = False

                # ---------------- Dispatch request ----------------
                if method == "GET":
                    self.handle_get(client_socket, path, headers, keep_alive)
                elif method == "POST":
                    self.handle_post(client_socket, path, headers, request_text, request_data, keep_alive)
                else:
                    client_socket.sendall(make_response(405, keep_alive=keep_alive))

                requests_handled += 1

            except socket.timeout:
                log(f"[Thread-{self.thread_id}] Keep-Alive timeout reached")
                break

    # ---------------- GET Request Handler ----------------
    def handle_get(self, client_socket, path, headers, keep_alive):
        """
        Serve GET requests including HTML and binary files.
        """
        log(f"[Thread-{self.thread_id}] Request: GET {path}")

        # Block access to sensitive files
        disallowed_files = ["/config", "/.env", "/secret.txt"]
        if path in disallowed_files:
            log(f"[Thread-{self.thread_id}] Forbidden file access ❌")
            client_socket.sendall(make_response(403, keep_alive=keep_alive))
            return

        # Default file for root
        if path == "/":
            path = "/index.html"

        target = safe_path(path)

        if not target:
            log(f"[Thread-{self.thread_id}] Forbidden path ❌")
            client_socket.sendall(make_response(403, keep_alive=keep_alive))
            return
        elif not os.path.exists(target):
            log(f"[Thread-{self.thread_id}] File not found ❌")
            client_socket.sendall(make_response(404, keep_alive=keep_alive))
            return

        # Determine file type and serve accordingly
        ext = os.path.splitext(target)[1].lower()
        if ext == ".html":
            with open(target, "rb") as f:
                body = f.read()
            response = make_response(200, {"Content-Type": "text/html; charset=utf-8"}, body, keep_alive)
        elif ext in [".png", ".jpg", ".jpeg", ".txt"]:
            # Serve as binary with attachment headers
            filename = os.path.basename(target)
            with open(target, "rb") as f:
                body = f.read()
            response = make_response(
                200,
                {"Content-Type": "application/octet-stream", "Content-Disposition": f'attachment; filename="{filename}"'},
                body,
                keep_alive,
            )
            log(f"[Thread-{self.thread_id}] Sending file {filename} ({len(body)} bytes)")
        else:
            response = make_response(415, keep_alive=keep_alive)

        client_socket.sendall(response)

    # ---------------- POST Request Handler ----------------
    def handle_post(self, client_socket, path, headers, request_text, request_data, keep_alive):
        """
        Accept POST requests with JSON payload.
        Saves uploaded JSON to uploads folder with timestamped filename.
        """
        log(f"[Thread-{self.thread_id}] Request: POST {path}")

        # Validate content type
        if headers.get("Content-Type") != "application/json":
            client_socket.sendall(make_response(415, keep_alive=keep_alive))
            return

        # Extract JSON body
        try:
            body = request_text.split("\r\n\r\n", 1)[1]
            data = json.loads(body)
        except Exception:
            client_socket.sendall(make_response(400, keep_alive=keep_alive))
            return

        # Ensure uploads directory exists
        os.makedirs(os.path.join(RESOURCE_DIR, "uploads"), exist_ok=True)

        # Save JSON to file with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"upload_{timestamp}.json"
        filepath = os.path.join(RESOURCE_DIR, "uploads", filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        log(f"[Thread-{self.thread_id}] File created: /uploads/{filename}")

        # Send success response
        response_body = json.dumps({
            "status": "success",
            "message": "File created successfully",
            "filepath": f"/uploads/{filename}"
        }).encode("utf-8")

        response = make_response(201, {"Content-Type": "application/json"}, response_body, keep_alive)
        client_socket.sendall(response)


# ------------------ Main Server Function ------------------
def start_server(host, port, pool_size):
    """
    Start the HTTP server, spawn worker threads, and handle incoming connections.
    """
    # Ensure uploads folder exists
    os.makedirs(os.path.join(RESOURCE_DIR, "uploads"), exist_ok=True)

    # Create TCP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Reuse address
    server_socket.bind((host, port))
    server_socket.listen(MAX_CONNECTIONS)  # Start listening

    # Log server info
    log(f"HTTP Server started on http://{host}:{port}")
    log(f"Thread pool size: {pool_size}")
    log(f"Serving files from '{RESOURCE_DIR}' directory")
    log("Press Ctrl+C to stop the server")

    # Start worker threads
    for i in range(pool_size):
        Worker(i + 1, host, port).start()

    # Accept incoming connections
    try:
        while True:
            client_socket, client_address = server_socket.accept()
            try:
                # Add client connection to queue for worker threads
                connection_queue.put((client_socket, client_address), block=False)
            except queue.Full:
                # If queue is full, drop connection politely
                log("Warning: Thread pool saturated, dropping connection")
                client_socket.sendall(make_response(503, {"Retry-After": "5"}))
                client_socket.close()
    except KeyboardInterrupt:
        # Gracefully shutdown server
        log("Shutting down server...")
        server_socket.close()


# ------------------ Entry Point ------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-threaded HTTP Server")
    parser.add_argument("port", nargs="?", type=int, default=DEFAULT_PORT)
    parser.add_argument("host", nargs="?", type=str, default=DEFAULT_HOST)
    parser.add_argument("threads", nargs="?", type=int, default=DEFAULT_THREAD_POOL_SIZE)
    args = parser.parse_args()

    # Start server with given host, port, and thread pool size
    start_server(args.host, args.port, args.threads)
