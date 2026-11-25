#!/usr/bin/env python3
"""Tiny persistent-connection test client for the assignment."""

import socket


def read_response(sock):
    data = bytearray()

    while b"\r\n\r\n" not in data:
        chunk = sock.recv(4096)
        if not chunk:
            raise RuntimeError("server closed before response headers")
        data.extend(chunk)

    header_end = data.index(b"\r\n\r\n") + 4
    headers = data[:header_end].decode("iso-8859-1")
    body = bytearray(data[header_end:])

    content_length = 0
    for line in headers.split("\r\n"):
        if line.lower().startswith("content-length:"):
            content_length = int(line.split(":", 1)[1].strip())

    while len(body) < content_length:
        chunk = sock.recv(4096)
        if not chunk:
            raise RuntimeError("server closed before response body")
        body.extend(chunk)

    return headers, bytes(body[:content_length])


def request(sock, target, method="GET"):
    request_bytes = (
        f"{method} {target} HTTP/1.1\r\n"
        f"Host: localhost:8080\r\n"
        f"Content-Length: 0\r\n"
        f"Connection: keep-alive\r\n"
        f"\r\n"
    ).encode()

    sock.sendall(request_bytes)
    return read_response(sock)


def main():
    with socket.create_connection(("127.0.0.1", 8080)) as sock:
        cases = [
            ("/add?a=2&b=3", "200", "5"),
            ("/sub?a=10&b=4", "200", "6"),
            ("/mul?a=6&b=7", "200", "42"),
            ("/div?a=9&b=3", "200", "3"),
            ("/div?a=1&b=0", "400", "Division by zero"),
            ("/add?a=x&b=3", "400", "a and b must be integers"),
            ("/pow?a=2&b=8", "404", "Not Found"),
            ("/add", "400", "Missing a or b"),
        ]

        for target, expected_status, expected_body in cases:
            headers, body = request(sock, target)
            status = headers.split("\r\n", 1)[0].split(" ")
            actual_status = status[1]
            actual_body = body.decode().strip()

            assert actual_status == expected_status, (target, headers)
            assert actual_body == expected_body, (target, actual_body)

        # Required 405 case.
        headers, body = request(sock, "/add", method="POST")
        assert headers.startswith("HTTP/1.1 405")
        assert body.decode().strip() == "Method Not Allowed"

        print("All persistent-connection tests passed.")


if __name__ == "__main__":
    main()
