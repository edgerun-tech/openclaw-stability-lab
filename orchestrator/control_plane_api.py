#!/usr/bin/env python3
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

from orchestrator import control_plane as cp


def read_json(handler: BaseHTTPRequestHandler):
    n = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(n) if n > 0 else b"{}"
    return json.loads(raw.decode("utf8"))


def write_json(handler: BaseHTTPRequestHandler, code: int, obj: dict):
    body = json.dumps(obj).encode("utf8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        p = urlparse(self.path).path
        if p == "/health":
            return write_json(self, 200, {"ok": True})
        return write_json(self, 404, {"error": "not found"})

    def do_POST(self):
        p = urlparse(self.path).path
        conn = cp.connect()
        cp.init_db(conn)

        try:
            if p == "/register-worker":
                req = read_json(self)
                worker = req["worker"]
                profiles = req.get("profiles", [])
                cp.register_worker(conn, worker, profiles)
                return write_json(self, 200, {"ok": True})

            if p == "/claim-job":
                req = read_json(self)
                worker = req["worker"]
                lease = int(req.get("leaseSeconds", 1800))
                job = cp.claim_job(conn, worker, lease)
                return write_json(self, 200, {"job": job or {}})

            if p == "/submit-result":
                req = read_json(self)
                cp.submit_result(
                    conn,
                    req["jobId"],
                    req["worker"],
                    req["verdict"],
                    req.get("commit", ""),
                    req.get("report", ""),
                    req.get("logs", ""),
                )
                return write_json(self, 200, {"ok": True})

            if p == "/requeue-expired":
                n = cp.requeue_expired(conn)
                return write_json(self, 200, {"requeued": n})

            if p == "/render-board":
                cp.render_board(conn)
                return write_json(self, 200, {"ok": True})

            return write_json(self, 404, {"error": "not found"})
        except Exception as e:
            return write_json(self, 500, {"error": str(e)})


def main():
    server = HTTPServer(("127.0.0.1", 8091), Handler)
    print("control-plane api listening on 127.0.0.1:8091")
    server.serve_forever()


if __name__ == "__main__":
    main()
