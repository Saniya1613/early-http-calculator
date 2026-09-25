#!/usr/bin/env python3
"""
Persistent HTTP/1.1 calculator server.

Run:
    python3 server.py 8080

The server uses one TCP connection for multiple HTTP requests.
It reads exactly through the end of the headers, then consumes exactly
Content-Length bytes (when present), and leaves the connection open.
"""

import re
import socket
import sys
from urllib.parse import urlsplit, parse_qs

HOST = "0.0.0.0"
DEFAULT_PORT = 8080
MAX_HEADER_BYTES = 16 * 1024
MAX_BODY_BYTES = 64 * 1024
MAX_REQUEST_LINE = 4096


class HTTPError(Exception):
    def __init__(self, status, reason):
        self.status = status
        self.reason = reason


def read_until_headers_end(conn):
    """Read until CRLF CRLF, without consuming bytes beyond the headers."""
    data = bytearray()

    while b"\r\n\r\n" not in data:
        chunk = conn.recv(4096)
        if not chunk:
            if not data:
                return None
            raise HTTPError(400, "Malformed HTTP request")

        data.extend(chunk)

        if len(data) > MAX_HEADER_BYTES:
            raise HTTPError(400, "Headers too large")

    header_end = data.index(b"\r\n\r\n") + 4
    return bytes(data[:header_end]), bytes(data[header_end:])


def parse_request(header_bytes):
    try:
        text = header_bytes.decode("iso-8859-1")
    except UnicodeDecodeError:
        raise HTTPError(400, "Malformed HTTP request")

    lines = text.split("\r\n")
    if len(lines) < 3 or lines[-1] != "":
        raise HTTPError(400, "Malformed HTTP request")

    request_line = lines[0]
    if len(request_line) > MAX_REQUEST_LINE:
        raise HTTPError(400, "Request line too long")

    parts = request_line.split(" ")
    if len(parts) != 3:
        raise HTTPError(400, "Malformed request line")

    method, target, version = parts
    if version != "HTTP/1.1":
        raise HTTPError(400, "Only HTTP/1.1 is supported")

    headers = {}
    for line in lines[1:-2]:
        if ":" not in line:
            raise HTTPError(400, "Malformed header")

        name, value = line.split(":", 1)
        name = name.strip().lower()
        value = value.strip()

        if not name:
            raise HTTPError(400, "Malformed header")

        # Reject duplicate Content-Length rather than guessing.
        if name == "content-length" and name in headers:
            raise HTTPError(400, "Duplicate Content-Length")

        headers[name] = value

    if "host" not in headers or not headers["host"]:
        raise HTTPError(400, "Host header required")

    content_length = 0
    if "content-length" in headers:
        try:
            content_length = int(headers["content-length"])
        except ValueError:
            raise HTTPError(400, "Invalid Content-Length")

        if content_length < 0 or content_length > MAX_BODY_BYTES:
            raise HTTPError(400, "Invalid Content-Length")

    if "transfer-encoding" in headers:
        raise HTTPError(400, "Transfer-Encoding is not supported")

    return method, target, headers, content_length


def consume_body(conn, initial_body, content_length):
    """Consume exactly Content-Length bytes from this request."""
    if content_length == 0:
        return

    body = bytearray(initial_body)

    if len(body) > content_length:
        # Extra bytes belong to the next request. In practice the initial
        # read is header-delimited, so this is mainly defensive.
        raise HTTPError(400, "Request framing error")

    while len(body) < content_length:
        chunk = conn.recv(min(4096, content_length - len(body)))
        if not chunk:
            raise HTTPError(400, "Incomplete request body")
        body.extend(chunk)


def calculate(path):
    parsed = urlsplit(path)
    operation = parsed.path

    if operation not in {"/add", "/sub", "/mul", "/div"}:
        raise HTTPError(404, "Not Found")

    params = parse_qs(parsed.query, keep_blank_values=True)

    if "a" not in params or "b" not in params:
        raise HTTPError(400, "Missing a or b")

    if len(params["a"]) != 1 or len(params["b"]) != 1:
        raise HTTPError(400, "Each parameter must appear once")

    try:
        a = int(params["a"][0])
        b = int(params["b"][0])
    except ValueError:
        raise HTTPError(400, "a and b must be integers")

    if operation == "/add":
        result = a + b
    elif operation == "/sub":
        result = a - b
    elif operation == "/mul":
        result = a * b
    else:
        if b == 0:
            raise HTTPError(400, "Division by zero")
        result = int(a / b)

    return str(result)


def make_response(status, reason, body):
    body_bytes = body.encode("utf-8")
    return (
        f"HTTP/1.1 {status} {reason}\r\n"
        f"Content-Type: text/plain; charset=utf-8\r\n"
        f"Content-Length: {len(body_bytes)}\r\n"
        f"Connection: keep-alive\r\n"
        f"\r\n"
    ).encode("ascii") + body_bytes


def handle_request(conn, header_bytes, initial_body):
    method, target, headers, content_length = parse_request(header_bytes)

    # The request boundary is determined by Content-Length, not by EOF.
    consume_body(conn, initial_body, content_length)

    if method != "GET":
        return make_response(405, "Method Not Allowed", "Method Not Allowed\n")

    try:
        result = calculate(target)
        return make_response(200, "OK", result + "\n")
    except HTTPError as exc:
        return make_response(exc.status, exc.reason, exc.reason + "\n")


def serve_client(conn, addr):
    print(f"connected: {addr}")

    with conn:
        while True:
            try:
                parsed = read_until_headers_end(conn)
                if parsed is None:
                    break

                header_bytes, initial_body = parsed

                # We deliberately do not close after one response.
                response = handle_request(conn, header_bytes, initial_body)
                conn.sendall(response)

            except HTTPError as exc:
                try:
                    conn.sendall(make_response(exc.status, exc.reason, exc.reason + "\n"))
                except OSError:
                    pass
                # A malformed request makes the framing uncertain, so close.
                break
            except (ConnectionResetError, BrokenPipeError, OSError):
                break

    print(f"disconnected: {addr}")


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, port))
        server_socket.listen(20)

        print(f"calculator server listening on {HOST}:{port}")

        while True:
            conn, addr = server_socket.accept()
            serve_client(conn, addr)


if __name__ == "__main__":
    main()
