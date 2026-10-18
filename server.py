import http.server
import socketserver
import json
import urllib.parse
import os
import sys
import threading
from typing import Dict, Any

from engine import DriverEngine
from catalog import MicrosoftCatalog
from booster import SystemBooster

if getattr(sys, 'frozen', False):
    BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STATIC_DIR = os.path.join(BASE_DIR, "static")

class DriverUpdaterHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/":
            self.path = "/index.html"
            return super().do_GET()

        elif path == "/api/scan":
            devices = DriverEngine.scan_devices()
            dev_dicts = [d.to_dict() for d in devices]
            total = len(devices)
            outdated_count = sum(1 for d in devices if d.is_outdated)
            ok_count = total - outdated_count
            oem_count = sum(1 for d in devices if d.driver_name.lower().startswith("oem"))

            data = {
                "devices": dev_dicts,
                "stats": {
                    "total": total,
                    "outdated": outdated_count,
                    "ok": ok_count,
                    "oem": oem_count
                }
            }
            self.send_json(data)
            return

        elif path == "/api/search":
            q = query.get("q", [""])[0]
            if not q:
                self.send_json([])
                return
            results = MicrosoftCatalog.search(q, max_results=12)
            self.send_json(results)
            return

        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("content-length", 0))
        body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            payload = json.loads(body)
        except Exception:
            payload = {}

        if path == "/api/backup":
            dest = payload.get("path")
            if not dest:
                dest = os.path.join(os.environ.get("USERPROFILE", "C:"), "DriverBackups")
            res = DriverEngine.export_drivers(dest)
            self.send_json(res)
            return

        elif path == "/api/restore_point":
            res = DriverEngine.create_restore_point()
            self.send_json(res)
            return

        elif path == "/api/install_update":
            uid = payload.get("id")
            if not uid:
                self.send_json({"success": False, "error": "Gecersiz Guncelleme Kimligi"})
                return

            urls = MicrosoftCatalog.get_download_urls(uid)
            if not urls:
                self.send_json({"success": False, "error": "Indirme baglantisi alinamadi"})
                return

            cab_url = urls[0]
            downloads_dir = os.path.join(BASE_DIR, "downloads", uid)
            cab_file = os.path.join(downloads_dir, "package.cab")
            dl_ok = MicrosoftCatalog.download_file(cab_url, cab_file)
            if not dl_ok:
                self.send_json({"success": False, "error": "CAB dosyasi indirilemedi"})
                return

            extract_dir = os.path.join(downloads_dir, "extracted")
            ext_ok = MicrosoftCatalog.extract_cab(cab_file, extract_dir)
            if not ext_ok:
                self.send_json({"success": False, "error": "Paket acilamadi"})
                return

            # Find .inf file
            inf_files = []
            for root, _, files in os.walk(extract_dir):
                for f in files:
                    if f.lower().endswith(".inf"):
                        inf_files.append(os.path.join(root, f))

            if not inf_files:
                self.send_json({"success": False, "error": "Paket icinde .inf surucu dosyasi bulunamadi"})
                return

            install_res = DriverEngine.install_driver(inf_files[0])
            self.send_json({
                "success": install_res.get("success", False),
                "output": install_res.get("output", ""),
                "inf": inf_files[0]
            })
            return

        elif path == "/api/boost/game":
            active = payload.get("active", True)
            res = SystemBooster.game_boost(active)
            self.send_json(res)
            return

        elif path == "/api/boost/network":
            res = SystemBooster.optimize_network()
            self.send_json(res)
            return

        elif path == "/api/boost/clean":
            res = SystemBooster.clean_temp_files()
            self.send_json(res)
            return

        self.send_error(404, "Endpoint bulunamadi")

    def send_json(self, data: Any):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

def start_server(port: int = 8765):
    server = socketserver.ThreadingTCPServer(("127.0.0.1", port), DriverUpdaterHandler)
    server.serve_forever()

if __name__ == "__main__":
    print("[*] Sunucu 127.0.0.1:8765 adresinde calisiyor...")
    start_server(8765)
