import subprocess
import os
import re
import sys
import json
import ctypes
from ctypes import wintypes
from datetime import datetime
from typing import List, Dict, Optional, Any

class DriverDevice:
    def __init__(self):
        self.instance_id: str = ""
        self.description: str = ""
        self.class_name: str = ""
        self.manufacturer: str = ""
        self.status: str = ""
        self.driver_name: str = ""
        self.original_name: str = ""
        self.provider_name: str = ""
        self.driver_version: str = ""
        self.driver_date: Optional[datetime] = None
        self.driver_date_str: str = ""
        self.signer_name: str = ""
        self.matching_device_id: str = ""
        self.is_outdated: bool = False
        self.just_updated: bool = False
        self.status_label: str = "Güncel"
        self.age_days: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "description": self.description,
            "class_name": self.class_name,
            "manufacturer": self.manufacturer,
            "status": self.status,
            "driver_name": self.driver_name,
            "original_name": self.original_name,
            "provider_name": self.provider_name,
            "driver_version": self.driver_version,
            "driver_date": self.driver_date_str,
            "signer_name": self.signer_name,
            "is_outdated": self.is_outdated,
            "just_updated": self.just_updated,
            "status_label": self.status_label,
            "matching_device_id": self.matching_device_id,
            "age_days": self.age_days
        }

class DriverEngine:
    @staticmethod
    def is_admin() -> bool:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    @staticmethod
    def run_cmd(args: List[str]) -> str:
        try:
            res = subprocess.run(
                args,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            for enc in ("cp1254", "utf-8", "cp857"):
                try:
                    return res.stdout.decode(enc)
                except UnicodeDecodeError:
                    continue
            return res.stdout.decode("utf-8", errors="replace")
        except Exception as e:
            return f"Error: {e}"

    @classmethod
    def get_history_file(cls) -> str:
        appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
        db_dir = os.path.join(appdata, "ReaPCBooster")
        os.makedirs(db_dir, exist_ok=True)
        old_history = os.path.join(appdata, "DriverBooster", "update_history.json")
        new_history = os.path.join(db_dir, "update_history.json")
        if os.path.exists(old_history) and not os.path.exists(new_history):
            try:
                import shutil
                shutil.copy2(old_history, new_history)
            except Exception:
                pass
        return new_history

    @classmethod
    def get_update_history(cls) -> Dict[str, Any]:
        h_file = cls.get_history_file()
        if os.path.exists(h_file):
            try:
                with open(h_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    @classmethod
    def record_update_success(cls, identifier: str, details: Dict[str, Any]):
        if not identifier:
            return
        h_file = cls.get_history_file()
        history = cls.get_update_history()
        history[identifier] = {
            "timestamp": datetime.now().isoformat(),
            **details
        }
        try:
            with open(h_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    @classmethod
    def scan_devices(cls) -> List[DriverDevice]:
        raw_output = cls.run_cmd(["pnputil", "/enum-devices", "/connected", "/drivers"])
        devices = []
        blocks = raw_output.split("Instance ID:")
        now = datetime.now()
        history = cls.get_update_history()

        for b in blocks:
            b = b.strip()
            if not b:
                continue
            
            lines = [l.strip() for l in b.splitlines() if l.strip()]
            if not lines:
                continue

            first_line = lines[0]
            if "Microsoft PnP Utility" in first_line or "Microsoft Corporation" in first_line:
                continue

            dev = DriverDevice()
            dev.instance_id = first_line

            current_section = "device"
            driver_blocks = []
            cur_driver = {}

            for line in lines[1:]:
                line_str = line.strip()
                if not line_str:
                    continue
                
                if line_str == "Matching Drivers:":
                    current_section = "drivers"
                    continue

                if current_section == "device":
                    if ":" in line_str:
                        key, val = line_str.split(":", 1)
                        key = key.strip().lower()
                        val = val.strip()
                        if key == "device description":
                            dev.description = val
                        elif key == "class name":
                            dev.class_name = val
                        elif key == "manufacturer name":
                            dev.manufacturer = val
                        elif key == "status":
                            dev.status = val
                        elif key == "driver name":
                            dev.driver_name = val
                elif current_section == "drivers":
                    if line_str.startswith("Driver Name:"):
                        if cur_driver:
                            driver_blocks.append(cur_driver)
                        cur_driver = {"driver name": line_str.split(":", 1)[1].strip()}
                    elif ":" in line_str and cur_driver is not None:
                        k, v = line_str.split(":", 1)
                        cur_driver[k.strip().lower()] = v.strip()

            if cur_driver:
                driver_blocks.append(cur_driver)

            # Pick active driver
            active_drv = None
            for d in driver_blocks:
                status = d.get("driver status", "").lower()
                if "installed" in status or "best ranked" in status:
                    active_drv = d
                    break
            
            if not active_drv and driver_blocks:
                active_drv = driver_blocks[0]

            if active_drv:
                dev.original_name = active_drv.get("original name", "")
                dev.provider_name = active_drv.get("provider name", "")
                dev.signer_name = active_drv.get("signer name", "")
                dev.matching_device_id = active_drv.get("matching device id", "")
                
                drv_ver_raw = active_drv.get("driver version", "")
                parts = drv_ver_raw.split()
                if parts:
                    date_candidate = parts[0]
                    dev.driver_date_str = date_candidate
                    dev.driver_version = " ".join(parts[1:]) if len(parts) > 1 else ""
                    
                    for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d"):
                        try:
                            d_obj = datetime.strptime(date_candidate, fmt)
                            dev.driver_date = d_obj
                            dev.age_days = (now - d_obj).days
                            break
                        except ValueError:
                            pass

                # Outdated Evaluation:
                prov_lower = (dev.provider_name or "").lower()
                signer_lower = (dev.signer_name or "").lower()
                ver_str = dev.driver_version or ""
                date_str = dev.driver_date_str or ""
                
                # Standard Microsoft in-box drivers (WAN Miniport, Volume, System Timer, Motherboard resources, etc.)
                # Microsoft sets in-box drivers canonically to 06/21/2006 on Windows 10/11. They are NOT outdated.
                is_ms_inbox = (
                    (prov_lower in ["microsoft", "microsoft windows", "microsoft corporation"] or "microsoft" in signer_lower)
                    and (ver_str.startswith("10.0.") or "2006" in date_str)
                )

                # Check update history
                is_recently_updated = False
                for k in [dev.instance_id, dev.matching_device_id, dev.description]:
                    if k and k in history:
                        is_recently_updated = True
                        break

                if is_recently_updated:
                    dev.just_updated = True
                    dev.is_outdated = False
                    dev.status_label = "Yeni Güncellendi"
                elif is_ms_inbox:
                    dev.is_outdated = False
                    dev.status_label = "Güncel (Windows)"
                elif dev.age_days and dev.age_days > 730:
                    dev.is_outdated = True
                    dev.status_label = "Eski Sürüm"
                else:
                    dev.is_outdated = False
                    dev.status_label = "Güncel"

            if not dev.description:
                dev.description = dev.instance_id

            devices.append(dev)

        return devices

    @classmethod
    def install_and_update_driver(cls, inf_path: str, hardware_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Multi-Engine Driver Installation & Hardware Binding Pipeline:
        1. SetupAPI / NewDev UpdateDriverForPlugAndPlayDevices (forces live hardware driver replacement)
        2. DiInstallDriver (forces INF installation and binds to all matching devices)
        3. Cloned DrvInstall DpInstX64 (IObit DIFxAPI installer)
        4. pnputil /add-driver /install & pnputil /scan-devices
        """
        inf_path = os.path.abspath(inf_path)
        if not os.path.isfile(inf_path):
            return {"success": False, "error": f"INF dosyası bulunamadı: {inf_path}"}

        success = False
        methods_tried = []
        output_logs = []

        # Engine 1: Windows NewDev UpdateDriverForPlugAndPlayDevicesW
        if hardware_id:
            try:
                newdev = ctypes.WinDLL("newdev.dll")
                newdev.UpdateDriverForPlugAndPlayDevicesW.argtypes = [
                    wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(wintypes.BOOL)
                ]
                newdev.UpdateDriverForPlugAndPlayDevicesW.restype = wintypes.BOOL

                reboot_needed = wintypes.BOOL(False)
                # INSTALLFLAG_FORCE = 0x00000001
                res = newdev.UpdateDriverForPlugAndPlayDevicesW(
                    None,
                    hardware_id,
                    inf_path,
                    1,
                    ctypes.byref(reboot_needed)
                )
                if res:
                    success = True
                    methods_tried.append("UpdateDriverForPlugAndPlayDevices: Başarılı")
                else:
                    err = ctypes.GetLastError()
                    methods_tried.append(f"UpdateDriverForPlugAndPlayDevices: Hata {err}")
            except Exception as e:
                methods_tried.append(f"UpdateDriverForPlugAndPlayDevices: {e}")

        # Engine 2: Windows DiInstallDriverW
        try:
            newdev = ctypes.WinDLL("newdev.dll")
            newdev.DiInstallDriverW.argtypes = [
                wintypes.HWND, wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(wintypes.BOOL)
            ]
            newdev.DiInstallDriverW.restype = wintypes.BOOL

            reboot_needed = wintypes.BOOL(False)
            # DIIRFLAG_FORCE_INF = 0x00000002
            res2 = newdev.DiInstallDriverW(None, inf_path, 2, ctypes.byref(reboot_needed))
            if res2:
                success = True
                methods_tried.append("DiInstallDriver: Başarılı")
            else:
                err = ctypes.GetLastError()
                methods_tried.append(f"DiInstallDriver: Hata {err}")
        except Exception as e:
            methods_tried.append(f"DiInstallDriver: {e}")

        # Engine 3: IObit Cloned DpInstX64
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        dpinst_exe = os.path.join(base_dir, "DrvInstall", "DpInstX64.exe")
        if os.path.exists(dpinst_exe):
            try:
                inf_dir = os.path.dirname(inf_path)
                cmd = [dpinst_exe, "/s", "/f", "/path", inf_dir]
                dp_res = subprocess.run(cmd, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                if dp_res.returncode == 0:
                    success = True
                    methods_tried.append("IObit DpInstX64: Başarılı")
                else:
                    methods_tried.append(f"IObit DpInstX64: Kod {dp_res.returncode}")
            except Exception as e:
                methods_tried.append(f"IObit DpInstX64: {e}")

        # Engine 4: Native Windows PnP Utility
        pnp_out = cls.run_cmd(["pnputil", "/add-driver", inf_path, "/install"])
        output_logs.append(pnp_out)
        if "successfully added" in pnp_out.lower() or "başarıyla eklendi" in pnp_out.lower():
            success = True
            methods_tried.append("pnputil: Başarılı")

        # Rescan hardware changes
        cls.run_cmd(["pnputil", "/scan-devices"])

        if success and hardware_id:
            cls.record_update_success(hardware_id, {
                "inf": os.path.basename(inf_path),
                "path": inf_path
            })

        return {
            "success": success,
            "methods": methods_tried,
            "output": "\n".join(methods_tried) + "\n" + "\n".join(output_logs)
        }

    @classmethod
    def export_drivers(cls, backup_dir: str) -> Dict[str, Any]:
        os.makedirs(backup_dir, exist_ok=True)
        out = cls.run_cmd(["pnputil", "/export-driver", "*", backup_dir])
        return {
            "success": True,
            "output": out,
            "directory": os.path.abspath(backup_dir)
        }

    @classmethod
    def create_restore_point(cls, description: str = "ReaPCBoosterRestorePoint") -> Dict[str, Any]:
        ps = f'Checkpoint-Computer -Description "{description}" -RestorePointType "DEVICE_DRIVER_INSTALL"'
        out = cls.run_cmd(["powershell", "-NoProfile", "-Command", ps])
        return {"output": out}
