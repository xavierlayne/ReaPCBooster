import urllib.request
import urllib.parse
import re
import os
import subprocess
from typing import List, Dict, Any, Optional

class MicrosoftCatalog:
    BASE_SEARCH_URL = "https://www.catalog.update.microsoft.com/Search.aspx?q="
    DOWNLOAD_DIALOG_URL = "https://www.catalog.update.microsoft.com/DownloadDialog.aspx"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    @classmethod
    def clean_search_term(cls, term: str) -> str:
        cleaned = re.sub(r'\([^)]*\)', '', term).strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)
        # Avoid terms that are too generic
        return cleaned

    @classmethod
    def search(cls, query: str, max_results: int = 15) -> List[Dict[str, Any]]:
        query = cls.clean_search_term(query)
        url = cls.BASE_SEARCH_URL + urllib.parse.quote(query)
        req = urllib.request.Request(url, headers=cls.HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            return [{"error": f"Arama bağlantı hatası: {e}"}]

        results = []
        table_m = re.search(r'<table[^>]*id=["\']ctl00_catalogBody_updateMatches["\'][^>]*>([\s\S]*?)</table>', html)
        if not table_m:
            return results

        table_html = table_m.group(1)
        rows = re.findall(r'<tr[^>]*>([\s\S]*?)</tr>', table_html)
        clean = lambda s: re.sub(r'<[^>]+>', '', s).strip()

        for r in rows:
            btn = re.search(r'id=["\']([a-f0-9\-]{36})["\']', r)
            if not btn:
                continue
            uid = btn.group(1)
            tds = re.findall(r'<td[^>]*>([\s\S]*?)</td>', r)
            cleaned = [clean(t) for t in tds]
            if len(cleaned) >= 6:
                results.append({
                    "id": uid,
                    "title": cleaned[1] if len(cleaned) > 1 else "",
                    "products": cleaned[2] if len(cleaned) > 2 else "",
                    "classification": cleaned[3] if len(cleaned) > 3 else "",
                    "last_updated": cleaned[4] if len(cleaned) > 4 else "",
                    "version": cleaned[5] if len(cleaned) > 5 else "",
                    "size": cleaned[6].split()[0] + " " + cleaned[6].split()[1] if len(cleaned[6].split()) >= 2 else cleaned[6]
                })
                if len(results) >= max_results:
                    break

        return results

    @classmethod
    def get_download_urls(cls, update_id: str) -> List[str]:
        post_data = f'updateIDs=[{{"size":0,"languages":"","uidInfo":"{update_id}","updateID":"{update_id}"}}]'.encode("utf-8")
        req = urllib.request.Request(
            cls.DOWNLOAD_DIALOG_URL,
            data=post_data,
            headers={
                **cls.HEADERS,
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            return []

        urls = re.findall(r'https?://[a-zA-Z0-9\.\-_/]+windowsupdate\.com/[a-zA-Z0-9\.\-_/]+\.cab', html, re.IGNORECASE)
        if not urls:
            urls = re.findall(r'https?://[^\'"]+\.cab', html, re.IGNORECASE)
        
        # Deduplicate while preserving order
        return list(dict.fromkeys(urls))

    @classmethod
    def download_file(cls, url: str, dest_path: str, progress_callback=None) -> bool:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
            req = urllib.request.Request(url, headers=cls.HEADERS)
            with urllib.request.urlopen(req, timeout=30) as response, open(dest_path, "wb") as out_file:
                total_length = response.headers.get("content-length")
                total_bytes = int(total_length) if total_length else 0
                downloaded = 0
                chunk_size = 65536
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    downloaded += len(chunk)
                    out_file.write(chunk)
                    if progress_callback and total_bytes:
                        progress_callback(downloaded, total_bytes)
            return True
        except Exception:
            return False

    @classmethod
    def extract_cab(cls, cab_path: str, extract_to: str) -> bool:
        os.makedirs(extract_to, exist_ok=True)
        try:
            cmd = ["expand", os.path.abspath(cab_path), "-F:*", os.path.abspath(extract_to)]
            res = subprocess.run(
                cmd,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            return res.returncode == 0
        except Exception:
            return False
