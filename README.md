# ReaPCBooster - Smart Driver Manager & Updater

An open-source desktop utility designed to scan Windows hardware devices, detect outdated or missing drivers, and safely fetch certified updates directly from the official Microsoft Update Catalog.

---

## 💾 Download Windows Installer (Tıkla İndir)

[![Download ReaPCBooster](https://img.shields.io/badge/Download-ReaPCBooster_v1.0.0_Setup-blue?style=for-the-badge&logo=windows)](https://github.com/xavierlayne/ReaPCBooster/releases/download/v1.0.0/ReaPCBooster-Setup-x64.exe)

- **Doğrudan İndirme Bağlantısı (Direct Download):** [ReaPCBooster-Setup-x64.exe (v1.0.0)](https://github.com/xavierlayne/ReaPCBooster/releases/download/v1.0.0/ReaPCBooster-Setup-x64.exe)
- **Tüm Sürümler (GitHub Releases):** [Releases](https://github.com/xavierlayne/ReaPCBooster/releases)

---

## 🚀 Features

- **Hardware & Driver Inspection:** Scans all hardware components via Windows Management Instrumentation (WMI) and flags drivers older than 2 years.
- **Direct Microsoft Catalog Integration:** Fetches verified, hardware-matched driver packages without third-party middleman servers.
- **Automated Restore Points:** Automatically creates a Windows System Restore Point prior to installing any updates to ensure complete rollback safety.
- **Full Driver Backup:** One-click offline export of all third-party drivers to a local directory for easy restoration.
- **Standalone Binary:** Lightweight portable executable built with clean Python and Tkinter/CustomTkinter.

---

## ✨ Enhancements & Modifications by @xavierlayne

- **Clean-Room Rebranding:** Replaced all legacy proprietary brand names, logos, and graphics with clean, original `Rea PC Booster` design elements.
- **Prominent Attribution:** Developer profile badges and credits linked directly to [@xavierlayne](https://github.com/xavierlayne) across headers, dialogs, and metadata.
- **Precompiled Binary:** Packaged into a standalone `.exe` using PyInstaller for immediate out-of-the-box usage.

---

## 🛠️ Usage

### Running the Executable
Simply launch `dist/ReaPCBooster.exe` (or `ReaPCBooster.exe` from releases) with administrative privileges.

### Running from Source
```bash
git clone https://github.com/xavierlayne/ReaPCBooster.git
cd ReaPCBooster
python -m pip install -r requirements.txt
python main.py
```

---

## 📄 License & Maintainer

Distributed under the [MIT License](LICENSE).

- **Developer:** [@xavierlayne](https://github.com/xavierlayne)
