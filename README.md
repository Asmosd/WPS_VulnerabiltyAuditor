# WPS-Auditor

A lightweight Python script that automates the discovery of WPS-enabled networks using `wash`, and attempts to exploit them using `reaver`.

> ⚠️ **This tool is intended for educational and authorized penetration testing only. Do not use it on networks you do not own or lack explicit permission to test.**

## 📦 Requirements

- Python 3.x
- Arch Linux (tested)
- `reaver-wps` (includes both `reaver` and `wash`)
- Optionally: `aircrack-ng` (for tools like `airmon-ng` if you need to set monitor mode)

Install dependencies on Arch:
```bash
sudo pacman -S reaver-wps aircrack-ng
