"""
Simple HTTP server for the SonarChart viewer.
Serves the viewer.html and tile files locally.
Usage: python3 serve.py [port]
"""

import http.server
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Suppress 404 logs for missing tiles (expected behavior)."""
    def log_message(self, format, *args):
        if "404" not in str(args):
            super().log_message(format, *args)

print(f"Serving at http://localhost:{PORT}")
print(f"Open http://localhost:{PORT}/viewer.html in your browser")
http.server.HTTPServer(("", PORT), QuietHandler).serve_forever()
