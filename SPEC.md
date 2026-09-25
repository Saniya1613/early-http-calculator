# Protocol notes / spec

## Request

```text
METHOD SP request-target SP HTTP/1.1 CRLF
Host: hostname[:port] CRLF
Content-Length: N CRLF
Connection: keep-alive CRLF
CRLF
N body bytes
```

The assignment only needs GET requests for calculator operations, so the body is normally zero bytes.

## Response

```text
HTTP/1.1 STATUS REASON CRLF
Content-Type: text/plain; charset=utf-8 CRLF
Content-Length: N CRLF
Connection: keep-alive CRLF
CRLF
N body bytes
```

## Framing rule

The server must not use socket close as the normal end-of-request signal.

For each request:

1. Read through `\r\n\r\n`.
2. Parse `Content-Length`.
3. Consume exactly that many body bytes.
4. Process the request.
5. Send exactly one response.
6. Continue reading from the same socket.

This is the central point of the assignment.
