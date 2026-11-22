"""Serve a built client on the organizer's computer (Python 3.11+, standard library)."""
import argparse
import functools
import http.client
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ORIGINS = {
    "rehearsal": "http://127.0.0.1:8765",
    "stand": "https://team25.hack.be-healthy.tech",
}
READS = {"session", "prepared", "state", "guest", "catalog", "scenario", "reconciliation"}
WRITES = {"messages", "transcriptions", "devices"}


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def list_directory(self, path):
        self.send_error(404)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self'; "
                         "script-src 'self'; style-src 'self' 'unsafe-inline'; "
                         "frame-ancestors 'none'; object-src 'none'; base-uri 'none'")
        super().end_headers()

    def do_GET(self):
        if self.path.startswith("/api/"):
            self.proxy()
        else:
            super().do_GET()

    def do_POST(self):
        self.proxy()

    def do_DELETE(self):
        self.proxy()

    def proxy(self):
        local = f"127.0.0.1:{self.server.server_port}"
        if self.headers.get("Host") != local or self.headers.get("Origin", "http://" + local) != "http://" + local:
            return self.send_error(403)
        path = urlsplit(self.path)
        allowed = {"GET": READS, "POST": WRITES, "DELETE": {"session"}}[self.command]
        if path.path not in {"/api/v1/" + name for name in allowed}:
            return self.send_error(404)
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            return self.send_error(400)
        if length < 0 or self.headers.get("Transfer-Encoding"):
            return self.send_error(400)
        if length > (5_000_000 if path.path.endswith("/transcriptions") else 16384):
            return self.send_error(413)
        headers = {k: self.headers[k] for k in ("Authorization", "Content-Type", "Idempotency-Key") if k in self.headers}
        upstream = urlsplit(self.server.upstream)
        factory = http.client.HTTPSConnection if upstream.scheme == "https" else http.client.HTTPConnection
        connection = factory(upstream.hostname, upstream.port, timeout=180)
        try:
            connection.request(self.command, self.path, self.rfile.read(length), headers)
            response = connection.getresponse()
            content = response.read()
            self.send_response(response.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            if self.server.upstream == ORIGINS["rehearsal"]:
                self.send_header("X-Sain-Rehearsal", "1")
            self.end_headers()
            self.wfile.write(content)
        except (OSError, http.client.HTTPException):
            self.send_error(502)
        finally:
            connection.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=ORIGINS, default="rehearsal")
    parser.add_argument("--port", type=int, default=4173)
    args = parser.parse_args()
    dist = Path(__file__).resolve().parent / "dist"
    if not (dist / "index.html").is_file():
        parser.error("Missing dist/index.html. Run npm ci and npm run build, or extract the built client.")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), functools.partial(Handler, directory=dist))
    server.upstream = ORIGINS[args.mode]
    print(f"SAIN {args.mode}: http://127.0.0.1:{server.server_port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
