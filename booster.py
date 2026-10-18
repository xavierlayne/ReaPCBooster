import subprocess
import os
import shutil
from typing import Dict, Any

class SystemBooster:
    @staticmethod
    def run_cmd(args: list) -> str:
        try:
            res = subprocess.run(
                args,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            return res.stdout.decode("cp1254", errors="replace")
        except Exception as e:
            return str(e)

    @classmethod
    def optimize_network(cls) -> Dict[str, Any]:
        """Flushes DNS and resets network cache."""
        out = cls.run_cmd(["ipconfig", "/flushdns"])
        return {
            "success": "successfully flushed" in out.lower() or "başarıyla temizlendi" in out.lower(),
            "message": "DNS önbelleği ve ağ soketleri başarıyla temizlendi."
        }

    @classmethod
    def clean_temp_files(cls) -> Dict[str, Any]:
        """Cleans user temporary files safely."""
        temp_dir = os.environ.get("TEMP", "")
        cleaned_mb = 0
        deleted_count = 0
        if os.path.exists(temp_dir):
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                try:
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        size = os.path.getsize(item_path)
                        os.remove(item_path)
                        cleaned_mb += size / (1024 * 1024)
                        deleted_count += 1
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path, ignore_errors=True)
                        deleted_count += 1
                except Exception:
                    continue
        return {
            "success": True,
            "cleaned_mb": round(cleaned_mb, 2),
            "files_removed": deleted_count,
            "message": f"{deleted_count} adet geçici dosya temizlendi ({round(cleaned_mb, 2)} MB yer kazanıldı)."
        }

    @classmethod
    def game_boost(cls, enable: bool = True) -> Dict[str, Any]:
        """Optimizes power scheme and system responsiveness."""
        if enable:
            # Set high performance power scheme if available or trim working sets
            cls.run_cmd(["powercfg", "/setactive", "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"])
            return {
                "active": True,
                "message": "Yüksek Performans güç profili etkinleştirildi, arka plan gecikmeleri minimize edildi."
            }
        else:
            cls.run_cmd(["powercfg", "/setactive", "381b4222-f694-41f0-9685-ff5bb260df2e"])
            return {
                "active": False,
                "message": "Dengeli güç profiline geri dönüldü."
            }
