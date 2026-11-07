# -*- coding: utf-8 -*-
"""Локальный просмотр сайта: http://localhost:8000/ (для 1_ПОСМОТРЕТЬ_САЙТ.bat)."""
import functools
import http.server
import socketserver
import sys
import threading
import webbrowser

from common import DOCS


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):  # тишина в консоли
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_error(self, code, message=None, explain=None):
        if code == 404 and (DOCS / "404.html").exists():
            body = (DOCS / "404.html").read_bytes()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)
        else:
            super().send_error(code, message, explain)


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = False


def serve(open_browser=True, log=print):
    handler = functools.partial(Handler, directory=str(DOCS))
    httpd = None
    for port in range(8000, 8030):
        try:
            httpd = Server(("127.0.0.1", port), handler)
            break
        except OSError:
            continue
    if httpd is None:
        log("Не получилось запустить просмотр: заняты порты 8000-8029. Закрой старые окна просмотра.")
        return 1
    url = f"http://localhost:{httpd.server_address[1]}/"
    log("")
    log(f"Сайт открыт у тебя на компьютере: {url}")
    log("Пока это окно открыто — сайт работает. Чтобы остановить, закрой окно (или нажми Ctrl+C).")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(serve(open_browser="--no-open" not in sys.argv))
