<h1 align="center">📺 Vavoo IPTV Playlist Generator</h1>

[![License](https://img.shields.io/badge/License-MIT-green.svg)]
[![Donate](https://img.shields.io/badge/_-Donate-red.svg?logo=githubsponsors&labelColor=555555&style=for-the-badge)](https://ko-fi.com/lululla)


> [!WARNING]
> This project is for **educational and informational purposes only**. The author assumes no responsibility for any misuse. By using this software, you agree to comply with all applicable laws and regulations in your jurisdiction.

Automated M3U8 playlist generator for Italian IPTV channels from Vavoo sources, with full EPG mapping and logos.

## ✨ Features

- **Automated generation** of M3U8 playlists with Italian channels
- **Full EPG mapping** from `iptv-epg.org` and `epgshare01.online`
- **Channel logos** for all major networks (RAI, Mediaset, Sky, DAZN, etc.)
- **Smart categorization**: TV Sat, Cinema, Sport, Kids, News, Documentary
- **GitHub Actions** — playlist auto-updates daily, old runs auto-cleanup weekly
- **Tivùsat ordering** — channels follow the official numbering

## 🚀 Quick Start

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python generate_playlist.py --output playlist.m3u8
```

### CLI Options

```
--output PATH       Output file path (default: playlist.m3u8)
--epg-output PATH   Output path for merged EPG (e.g. epg.xml)
--groups GROUP...   Groups to include (default: Italy)
```

## 📁 Project Structure

```
vavoo-player/
├── .github/workflows/
│   ├── generate_playlist.yml   Daily playlist generation
│   ├── generate_epg.yml        EPG generation every 6 hours
│   └── cleanup_runs.yml        Weekly workflow runs cleanup
├── src/
│   ├── __init__.py
│   ├── playlist_generator.py   Core generator
│   ├── epg_manager.py          EPG data management
│   ├── epg_merger.py           EPG sources merger
│   └── data_manager.py         Channel & logo management
├── logos/                      Channel logos (PNG)
├── generate_playlist.py        CLI entry point
├── requirements.txt
├── GEMINI.MD
└── README.md
```

## 📡 EPG Sources

| Source | URL |
|--------|-----|
| Primary IT | `iptv-epg.org/files/epg-it.xml.gz` |
| Primary CH | `iptv-epg.org/files/epg-ch.xml.gz` |
| Backup IT | `epgshare01.online/epgshare01/epg_ripper_IT1.xml.gz` |
| Backup CH | `epgshare01.online/epgshare01/epg_ripper_CH1.xml.gz` |

## ⚙️ GitHub Actions

| Workflow | Schedule | Description |
|----------|----------|-------------|
| `generate_playlist.yml` | Daily at midnight | Generates and commits the playlist |
| `cleanup_runs.yml` | Sundays at 3 AM | Deletes workflow runs older than 7 days |

Both workflows can also be triggered manually via `workflow_dispatch`.

## 📜 License

For personal use only.
