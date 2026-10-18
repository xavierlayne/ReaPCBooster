import sys
import os
import argparse

from engine import DriverEngine
from catalog import MicrosoftCatalog
import gui

def run_cli(args):
    if args.scan:
        print("[*] Sistemdeki donanimlar ve suruculer taraniyor...")
        devices = DriverEngine.scan_devices()
        print(f"[+] Toplam {len(devices)} aygit tespit edildi.\n")
        print(f"{'DURUM':<12} | {'KATEGORI':<15} | {'SURUM':<18} | {'TARIH':<12} | {'AYGIT ADI'}")
        print("-" * 90)
        for d in devices:
            if args.outdated_only and not d.is_outdated:
                continue
            status = "ESKI (2y+)" if d.is_outdated else "GUNCEL"
            print(f"{status:<12} | {d.class_name[:14]:<15} | {d.driver_version[:17]:<18} | {d.driver_date_str:<12} | {d.description}")
        print("-" * 90)

    elif args.backup:
        backup_path = args.backup
        print(f"[*] Suruculer yedekleniyor: {backup_path}")
        res = DriverEngine.export_drivers(backup_path)
        print(f"[+] Sonuc: {'Basarili' if res.get('success') else 'Tamamlandi'}")
        print(res.get("output"))

    elif args.search:
        print(f"[*] Microsoft Update Katalogunda araniyor: {args.search}")
        results = MicrosoftCatalog.search(args.search)
        if not results:
            print("[-] Uygun guncelleme bulunamadi.")
        else:
            print(f"[+] {len(results)} paket bulundu:\n")
            for idx, r in enumerate(results, 1):
                print(f"{idx}. {r.get('title')}")
                print(f"   Uyumlu: {r.get('products')}")
                print(f"   Surum: {r.get('version')} | Tarih: {r.get('last_updated')} | Boyut: {r.get('size')}")
                print(f"   ID: {r.get('id')}\n")

    elif args.install:
        print(f"[*] Surucu paketi kuruluyor: {args.install}")
        res = DriverEngine.install_driver(args.install)
        print(f"[+] Kurulum ciktisi:\n{res.get('output')}")

def ensure_admin():
    import ctypes
    try:
        if not ctypes.windll.shell32.IsUserAnAdmin():
            # If not elevated, relaunch with runas
            if getattr(sys, 'frozen', False):
                exe = sys.executable
                params = " ".join(f'"{a}"' for a in sys.argv[1:])
            else:
                exe = sys.executable
                params = f'"{__file__}" ' + " ".join(f'"{a}"' for a in sys.argv[1:])
            ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
            sys.exit(0)
    except Exception:
        pass

def main():
    ensure_admin()
    parser = argparse.ArgumentParser(description="ReaPCBooster - Surucu Yoneticisi ve Guncelleyici")
    parser.add_argument("--scan", action="store_true", help="Sistem donanim ve suruculerini konsolda listele")
    parser.add_argument("--outdated-only", action="store_true", help="Yalnizca eski/guncelleme gereken suruculeri listele")
    parser.add_argument("--backup", type=str, help="Tum ucuncu parti suruculeri belirtilen klasore yedekle")
    parser.add_argument("--search", type=str, help="Microsoft Katalogunda donanim veya surucu ara")
    parser.add_argument("--install", type=str, help="Belirtilen .inf surucu dosyasini kur")

    args = parser.parse_args()

    if args.scan or args.backup or args.search or args.install:
        run_cli(args)
    else:
        # Launch Native Desktop GUI directly
        gui.main()

if __name__ == "__main__":
    main()
