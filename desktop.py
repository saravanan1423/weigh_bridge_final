import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path
from tkinter import Button, Label, Tk

from werkzeug.serving import make_server


APP_TITLE = "Weighman WMS"
HOST = "127.0.0.1"
START_PORT = 5000
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800
DESKTOP_ZOOM = 0.9


def executable_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


os.environ.setdefault("WEIGHMAN_DATA_DIR", str(executable_dir()))

from app import app


def find_free_port(start_port=START_PORT):
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((HOST, port))
            except OSError:
                port += 1
                continue
            return port


class FlaskServer:
    def __init__(self, flask_app):
        self.port = find_free_port()
        self.url = f"http://{HOST}:{self.port}"
        self.server = make_server(HOST, self.port, flask_app, threaded=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.server.shutdown()
        self.thread.join(timeout=2)


def main():
    server = FlaskServer(app)
    server.start()

    try:
        try:
            import webview
        except Exception as exc:
            run_browser_fallback(server, f"PyWebView is not available: {exc}")
            return

        window = webview.create_window(
            APP_TITLE,
            server.url,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            min_size=(1024, 680),
        )

        def apply_default_zoom():
            scaled_size = 100 / DESKTOP_ZOOM
            window.evaluate_js(
                f"""
                (() => {{
                  const styleId = "pywebview-desktop-zoom";
                  document.getElementById(styleId)?.remove();
                  const style = document.createElement("style");
                  style.id = styleId;
                  style.textContent = `
                    body {{
                      overflow: hidden;
                    }}

                    .app {{
                      width: {scaled_size}vw !important;
                      height: {scaled_size}vh !important;
                      transform: scale({DESKTOP_ZOOM});
                      transform-origin: top left;
                    }}
                  `;
                  document.head.appendChild(style);
                }})();
                """
            )

        window.events.loaded += apply_default_zoom
        try:
            webview.start(debug=False)
        except Exception as exc:
            run_browser_fallback(server, f"PyWebView runtime failed: {exc}")
    finally:
        server.stop()


def run_browser_fallback(server, reason):
    webbrowser.open(server.url)

    root = Tk()
    root.title(APP_TITLE)
    root.geometry("420x160")
    root.resizable(False, False)
    root.protocol("WM_DELETE_WINDOW", root.destroy)

    Label(
        root,
        text="Weighman WMS is running in your browser.",
        font=("Segoe UI", 11, "bold"),
        pady=12,
    ).pack()
    Label(
        root,
        text=f"{reason}\n\nKeep this window open while using the app.",
        wraplength=380,
        justify="center",
        font=("Segoe UI", 9),
    ).pack()
    Button(root, text="Open App", command=lambda: webbrowser.open(server.url), width=14).pack(pady=8)

    root.mainloop()
    time.sleep(.2)


if __name__ == "__main__":
    main()
