"""A small web page for trying attacks by hand: python -m lab.web

Open http://localhost:8000, pick or type an attack, switch defences on and
off, and see whether the secret leaks. It uses the same Bot, defences and
scorer as the experiment, just one message at a time.
"""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import requests

from lab.bot import SECRET, Bot, Defences
from lab.models import FakeModel, OllamaModel
from lab.runner import load_attacks
from lab.scoring import leaked

PAGE = Path(__file__).with_name("demo.html")


class Handler(BaseHTTPRequestHandler):
    model = None  # set in main()
    attacks = []  # set in main()

    def do_GET(self):
        if self.path == "/":
            self.send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/attacks":
            self.send_json(200, {"secret": SECRET, "attacks": self.attacks})
        else:
            self.send(404, b"Not found", "text/plain")

    def do_POST(self):
        if self.path != "/api/chat":
            return self.send(404, b"Not found", "text/plain")

        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        defences = Defences(
            hardened_prompt=bool(body.get("hardened_prompt")),
            input_filter=bool(body.get("input_filter")),
            output_filter=bool(body.get("output_filter")),
        )
        try:
            reply, blocked_by = Bot(self.model, defences).reply(body.get("message", ""))
        except requests.ConnectionError:
            return self.send_json(502, {"error": "Couldn't reach Ollama. Start it with: ollama serve"})
        except RuntimeError as error:
            return self.send_json(502, {"error": str(error)})

        self.send_json(200, {"reply": reply, "blocked_by": blocked_by, "leaked": leaked(reply, SECRET)})

    def send_json(self, status, data):
        self.send(status, json.dumps(data).encode(), "application/json")

    def send(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(description="Try prompt injections by hand in your browser.")
    parser.add_argument("--model", default="llama3.2:3b",
                        help="Ollama model to attack (default: %(default)s)")
    parser.add_argument("--port", type=int, default=8000,
                        help="port to serve the page on (default: %(default)s)")
    parser.add_argument("--fake", action="store_true",
                        help="use the fake offline model instead of Ollama")
    args = parser.parse_args()

    Handler.model = FakeModel(SECRET) if args.fake else OllamaModel(args.model)
    Handler.attacks = load_attacks("attacks.yaml")

    # 127.0.0.1 means only this computer can open the page, not other
    # devices on your network.
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Open http://localhost:{args.port}  (Ctrl+C to stop)", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
