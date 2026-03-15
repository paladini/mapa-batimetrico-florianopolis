"""
Simple HTTP server for the bathymetric data viewer.
Usage: python3 serve.py [port]
"""

import http.server
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

print(f"Serving at http://localhost:{PORT}")
print(f"Open http://localhost:{PORT}/viewer.html")
http.server.HTTPServer(("", PORT), http.server.SimpleHTTPRequestHandler).serve_forever()
