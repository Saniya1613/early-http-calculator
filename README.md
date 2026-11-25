# Early HTTP/1.1 — Persistent Calculator

A no-framework TCP socket implementation of the assignment:

> Build a calculator that stays on the line.

## Requirements implemented

- HTTP/1.1 over a raw TCP socket.
- One TCP connection can carry many requests.
- `GET /add?a=2&b=3` → `200` with `5`.
- `GET /sub?a=10&b=4` → `200` with `6`.
- `GET /mul?a=6&b=7` → `200` with `42`.
- `GET /div?a=9&b=3` → `200` with `3`.
- Division by zero → `400`.
- Non-numeric arguments → `400`.
- Unknown operation such as `/pow` → `404`.
- Non-GET methods such as `POST` → `405`.
- Missing `Host` header → `400`.
- `Content-Length` is parsed and exactly that many request-body bytes are consumed.
- The connection remains open after successful requests.
- Malformed requests cause a `400` and close the connection because request framing can no longer be trusted.

## Run

```bash
python3 server.py 8080
```

In another terminal:

```bash
python3 client_test.py
```

You should see:

```text
All persistent-connection tests passed.
```

## Manual test with curl

Run:

```bash
curl -v "http://localhost:8080/add?a=2&b=3"
curl -v "http://localhost:8080/sub?a=10&b=4"
curl -v "http://localhost:8080/mul?a=6&b=7"
curl -v "http://localhost:8080/div?a=9&b=3"
curl -v "http://localhost:8080/div?a=1&b=0"
curl -v "http://localhost:8080/pow?a=2&b=8"
```

## Why Content-Length matters

With HTTP/1.0 in the earlier exercise, closing the socket could tell the receiver that the response was finished.

With a persistent HTTP/1.1 connection, EOF cannot be used between requests because the socket stays open.

Therefore the receiver needs an explicit message boundary. This implementation uses:

```text
headers
CRLF CRLF
Content-Length bytes of body
```

After exactly those bytes are consumed, the next byte belongs to the next HTTP request.

## Assignment checklist

- [x] Raw socket; no web framework
- [x] HTTP/1.1 request parsing
- [x] Persistent connection
- [x] Calculator operations
- [x] 200 / 400 / 404 / 405 responses
- [x] Host validation
- [x] Content-Length framing
- [x] Multiple requests over one TCP connection
