"""
MIT License

Copyright DragonDreams GmbH 2024
Copyright modifications 2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

"""Minimal MJPEG HTTP server for the Lip Camera application."""


from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import logging
import threading
import time
from urllib.parse import urlparse


class _ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class MjpegCameraServer:
    """Publish the most recent JPEG image through HTTP and MJPEG endpoints."""

    _BOUNDARY = "lip_camera_frame"

    def __init__(self) -> None:
        self._logger = logging.getLogger("evcta.MjpegCameraServer")
        self._condition = threading.Condition()
        self._frame: bytes | None = None
        self._frame_number = 0
        self._server: _ReusableThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._bind_ip = "127.0.0.1"
        self._port = 8080

    @property
    def running(self) -> bool:
        return self._server is not None

    @property
    def bind_ip(self) -> str:
        return self._bind_ip

    @property
    def port(self) -> int:
        return self._port

    def start(self, bind_ip: str, port: int) -> None:
        """Start listening on the selected local IPv4 address and TCP port."""
        if self.running:
            return

        owner = self

        class RequestHandler(BaseHTTPRequestHandler):
            server_version = "LipCameraServer/1.0"

            def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
                path = urlparse(self.path).path
                if path in ("/", "/index.html"):
                    self._send_index()
                elif path == "/stream":
                    self._send_stream()
                elif path == "/snapshot.jpg":
                    self._send_snapshot()
                elif path == "/health":
                    self._send_health()
                else:
                    self.send_error(HTTPStatus.NOT_FOUND, "Not found")

            def log_message(self, fmt: str, *args: object) -> None:
                owner._logger.info("HTTP %s - %s", self.address_string(), fmt % args)

            def _send_index(self) -> None:
                page = (
                    "<!doctype html><html><head><meta charset='utf-8'>"
                    "<title>Lip Camera</title>"
                    "<style>body{background:#202124;color:#eee;font-family:sans-serif;"
                    "text-align:center}img{background:#404040;max-width:95vw;"
                    "max-height:85vh}</style></head><body>"
                    "<h1>Lip Camera</h1>"
                    "<img src='/stream' alt='camera stream'>"
                    "</body></html>"
                ).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(page)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(page)

            def _send_health(self) -> None:
                body = b"ok\n"
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def _send_snapshot(self) -> None:
                frame = owner.latest_frame()
                if frame is None:
                    self.send_error(HTTPStatus.SERVICE_UNAVAILABLE, "No camera frame available")
                    return
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(frame)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(frame)

            def _send_stream(self) -> None:
                self.send_response(HTTPStatus.OK)
                self.send_header(
                    "Content-Type",
                    "multipart/x-mixed-replace; boundary={}".format(owner._BOUNDARY),
                )
                self.send_header("Cache-Control", "no-store")
                self.send_header("Connection", "close")
                self.end_headers()
                last_number = -1
                try:
                    while owner.running:
                        frame, last_number = owner.wait_for_frame(last_number, timeout=2.0)
                        if frame is None:
                            continue
                        self.wfile.write(
                            ("--{}\r\n".format(owner._BOUNDARY)).encode("ascii")
                        )
                        self.wfile.write(b"Content-Type: image/jpeg\r\n")
                        self.wfile.write(
                            ("Content-Length: {}\r\n\r\n".format(len(frame))).encode("ascii")
                        )
                        self.wfile.write(frame)
                        self.wfile.write(b"\r\n")
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    return

        self._server = _ReusableThreadingHTTPServer((bind_ip, port), RequestHandler)
        self._bind_ip = bind_ip
        self._port = port
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="LipCameraMjpegServer",
            daemon=True,
        )
        self._thread.start()
        self._logger.info("MJPEG server started on %s:%s", bind_ip, port)

    def stop(self) -> None:
        """Stop the HTTP server and release waiting client streams."""
        server = self._server
        thread = self._thread
        if server is None:
            return

        self._server = None
        with self._condition:
            self._condition.notify_all()
        server.shutdown()
        server.server_close()
        if thread:
            thread.join(timeout=1.0)
        self._thread = None
        self._logger.info("MJPEG server stopped")

    def update_jpeg_frame(self, frame: bytes) -> None:
        """Install a newly encoded JPEG frame and wake connected clients."""
        if not self.running:
            return
        with self._condition:
            self._frame = frame
            self._frame_number += 1
            self._condition.notify_all()

    def latest_frame(self) -> bytes | None:
        with self._condition:
            return self._frame

    def wait_for_frame(self, last_number: int, timeout: float) -> tuple[bytes | None, int]:
        deadline = time.monotonic() + timeout
        with self._condition:
            while self.running and self._frame_number == last_number:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._condition.wait(timeout=remaining)
            return self._frame, self._frame_number
