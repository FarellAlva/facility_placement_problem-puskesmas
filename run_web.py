"""
Skrip Peluncur Aplikasi Web OpenStreetMap Spatial (run_web.py)
Menjalankan server HTTP lokal dan membuka antarmuka web modern di browser:
http://localhost:8000/web/index.html
"""

import os
import sys
import webbrowser
import socket
from http.server import HTTPServer, SimpleHTTPRequestHandler


def find_free_port(start_port=8000, max_port=8100):
    for port in range(start_port, max_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) != 0:
                return port
    return start_port


def run_server():
    port = find_free_port()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    server_address = ('', port)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    url = f"http://localhost:{port}/web/index.html"

    print("=" * 75)
    print("🚀 SPATIAL HEALTH INTELLIGENCE — APLIKASI WEB OPENSTREETMAP HARAPAN INDAH")
    print("=" * 75)
    print(f"Server aktif di : {url}")
    print("Tekan Ctrl+C di terminal ini untuk menghentikan server.")
    print("=" * 75)

    # Buka peramban web otomatis
    try:
        webbrowser.open(url)
    except Exception:
        pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer dihentikan.")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
