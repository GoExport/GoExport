from modules.logger import logger
from http.server import HTTPServer, SimpleHTTPRequestHandler
import helpers
import threading

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress logging

class Server:
    def __init__(self, host: str | None = None, port: int | None = None):
        self.prot = helpers.get_config("SERVER_PROTOCOL", "http")
        self.host = helpers.get_config("SERVER_HOST", host)
        self.port = helpers.get_config("SERVER_PORT", port)
        self.path = helpers.get_path(helpers.get_app_folder(), helpers.get_config("DEFAULT_SERVER_FILENAME"))

    def hostname(self):
        return f"{self.prot}://{self.host}:{self.port}"

    def start(self):
        handler = lambda *args, **kwargs: QuietHandler(*args, directory=self.path, **kwargs)
        self.httpd = HTTPServer((self.host, self.port), handler)
        logger.debug(f"Starting server on {self.hostname()} serving {self.path}")
        self.server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.server_thread.start()

    def stop(self, force: bool = True):
        logger.debug(f"Stopping server on {self.hostname()}")
        try:
            if force:
                # Forcefully close the server socket
                self.httpd.server_close()
            else:
                self.httpd.shutdown()
                self.server_thread.join()
        except Exception as e:
            logger.debug(f"Suppressed error during server stop: {e}")
        logger.debug("Server stopped")