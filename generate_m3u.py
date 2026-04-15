#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera playlist M3U da VAVOO.TO con ordinamento TIVUSAT e la apre con mpv"""

import json
import os
import sys
import subprocess
import re
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

VAVOO_API = "https://vavoo.to/mediahubmx-catalog.json"
AUTH_API = "https://www.lokke.app/api/app/ping"
M3U_PATH = os.path.join(os.path.dirname(__file__), "vavoo_playlist.m3u")
MPV_PATH = r"C:\Users\mdeangelis\Downloads\mpv-x86_64\mpv.exe"

TIVUSAT_ORDER = {
    "RAI 1": 1, "RAI 2": 2, "RAI 3": 3, "RETE 4": 4, "CANALE 5": 5, "ITALIA 1": 6, "LA7": 7, "TV8": 8, "NOVE": 9,
    "RAI 4": 10, "IRIS": 11, "LA5": 12, "RAI 5": 13, "RAI MOVIE": 14, "RAI PREMIUM": 15,
    "MEDIASET EXTRA": 17, "TV2000": 18, "CIELO": 19, "20 MEDIASET": 20, "RAI SPORT": 21,
    "RAI STORIA": 23, "RAI NEWS 24": 24, "TGCOM24": 25, "DMAX": 26, "REAL TIME": 31,
    "CINE34": 34, "FOCUS": 35, "RTL 102.5": 36, "WARNER TV": 37, "GIALLO": 38, "TOP CRIME": 39,
    "BOING": 40, "K2": 41, "RAI GULP": 42, "RAI YOYO": 43, "FRISBEE": 44, "CARTOONITO": 46, "SUPER!": 47,
    "SPIKE": 49, "SKY TG24": 50, "ITALIA 2": 66, "RADIO ITALIA TV": 70,
    "RSI LA 1": 71, "RSI LA 2": 72,
    "DAZN 1": 87, "DAZN 2": 88, "DAZN 3": 89,
    "SKY SPORT UNO": 90, "SKY SPORT ARENA": 91,
    "EUROSPORT 1": 92, "EUROSPORT 2": 93,
    "SKY SPORT CALCIO": 97, "SKY SPORT F1": 98,
    "SUPER TENNIS HD": 99, "SUPERTENNIS HD": 100,
    "SKY SPORT MOTOGP": 104, "SKY SPORT TENNIS": 105,
    "SKY SPORT GOLF": 111, "SKY SPORT NBA": 112
}

ITALIAN_RENAMES = {
    "LA 7": "LA7", "LA 5": "LA5", "8 TV": "TV8", "8TV": "TV8", "8": "TV8", "TV 8": "TV8",
    "CINE 34": "CINE34", "TV 2000": "TV2000", "TG COM 24": "TGCOM24", "TGCOM 24": "TGCOM24",
    "SKY TG 24": "SKY TG24", "SPORT ITALIA": "SPORTITALIA", "SPORTITALIA PLUS": "SPORTITALIA",
    "RTL 1025": "RTL 102.5", "RTL1025": "RTL 102.5", "DISCOVERY NOVE": "NOVE", "DISCOVERY K2": "K2",
    "DISCOVERY FOCUS": "FOCUS", "MEDIASET IRIS": "IRIS", "MEDIASET ITALIA 2": "ITALIA 2",
    "SKY CINEMA UNO 24": "SKY CINEMA UNO", "SKY CRIME": "TOP CRIME", "PREMIUM CRIME": "TOP CRIME",
    "SKY SPORT MOTOGP": "SKY SPORT MOTO GP", "SKY SPORTS F1": "SKY SPORT F1",
    "SKY SUPER TENNIS": "SUPER TENNIS", "CANALE 27": "TWENTYSEVEN", "27": "TWENTYSEVEN",
    "TWENTY SEVEN": "TWENTYSEVEN", "27 TWENTY SEVEN": "TWENTYSEVEN", "27 TWENTYSEVEN": "TWENTYSEVEN",
    "CINE 34 MEDIASET": "CINE34", "MEDIASET 20": "20 MEDIASET", "MEDIASET 1": "20 MEDIASET",
    "MOTORTREND": "MOTOR TREND", "LA 7 D": "LA7D", "HISTORY CHANNEL S": "HISTORY", "HISTORY  CHANNEL S": "HISTORY"
}

ITALIAN_BLACKLIST = ["RAI ITALIA", "STAR CRIME", "SKYSHOWTIME 1", "SKY SPORT FOOTBALL"]

def normalize_italian_name(name):
    n = name.upper().strip()
    for old, new in ITALIAN_RENAMES.items():
        if n == old.upper(): return new
    n = re.sub(r"\[.*?\]", "", n)
    n = re.sub(r"\(.*?\)", "", n)
    n = re.sub(r"\s+(HD|FHD|SD|4K|ITA|ITALIA|BACKUP|TIMVISION|PLUS)$", "", n)
    if not n.startswith("HISTORY"):
        n = re.sub(r"\s+\.[A-Z0-9]{1,3}$", "", n)
    n = re.sub(r"\s\+$", "", n)
    n = re.sub(r"\s+", " ", n)
    return n.strip()

def get_channel_priority(name):
    upper = name.upper()
    for ch, prio in TIVUSAT_ORDER.items():
        if upper == ch: return prio
    for ch, prio in TIVUSAT_ORDER.items():
        if ch in upper: return prio
    if "SKY" in upper: return 200
    if "DAZN" in upper: return 210
    if "PRIMA" in upper: return 300
    return 9999

def get_auth_signature():
    headers = {
        "user-agent": "okhttp/4.11.0", "accept": "application/json",
        "content-type": "application/json; charset=utf-8", "content-length": "1106", "accept-encoding": "gzip"
    }
    data = {
        "token": "ldCvE092e7gER0rVIajfsXIvRhwlrAzP6_1oEJ4q6HH89QHt24v6NNL_jQJO219hiLOXF2hqEfsUuEWitEIGN4EaHHEHb7Cd7gojc5SQYRFzU3XWo_kMeryAUbcwWnQrnf0-",
        "reason": "app-blur", "locale": "de", "theme": "dark",
        "metadata": {
            "device": {"type": "Handset", "brand": "google", "model": "Nexus", "name": "21081111RG", "uniqueId": "d10e5d99ab665233"},
            "os": {"name": "android", "version": "7.1.2", "abis": ["arm64-v8a"], "host": "android"},
            "app": {"platform": "android", "version": "1.1.0", "buildId": "97215000", "engine": "hbc85", "signatures": ["6e8a975e3cbf07d5de823a760d4c2547f86c1403105020adee5de67ac510999e"], "installer": "com.android.vending"},
            "version": {"package": "app.lokke.main", "binary": "1.1.0", "js": "1.1.0"},
            "platform": {"isAndroid": True, "isIOS": False, "isTV": False, "isWeb": False, "isMobile": True, "isWebTV": False, "isElectron": False}
        },
        "appFocusTime": 0, "playerActive": False, "playDuration": 0, "devMode": True, "hasAddon": True,
        "castConnected": False, "package": "app.lokke.main", "version": "1.1.0", "process": "app",
        "firstAppStart": 1772388338206, "lastAppStart": 1772388338206, "ipLocation": None, "adblockEnabled": False,
        "proxy": {"supported": ["ss", "openvpn"], "engine": "openvpn", "ssVersion": 1, "enabled": False, "autoServer": True, "id": "fi-hel"},
        "iap": {"supported": True}
    }
    try:
        resp = requests.post(AUTH_API, json=data, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json().get("addonSig")
    except Exception as e:
        print(f"Errore auth: {e}")
        return None

def fetch_group(group, auth_sig):
    headers = {
        "user-agent": "okhttp/4.11.0", "accept": "application/json",
        "content-type": "application/json; charset=utf-8", "accept-encoding": "gzip",
        "mediahubmx-signature": auth_sig
    }
    items = []
    cursor = 0
    while cursor is not None:
        try:
            data = {
                "language": "de", "region": "AT", "catalogId": "iptv", "id": "iptv",
                "adult": False, "search": "", "sort": "name", "filter": {"group": group},
                "cursor": cursor, "clientVersion": "3.0.2"
            }
            resp = requests.post(VAVOO_API, json=data, headers=headers, timeout=10)
            resp.raise_for_status()
            result = resp.json()
            for item in result.get("items", []):
                items.append({"url": item["url"], "name": item["name"], "group": item.get("group", group), "logo": item.get("logo", "")})
            cursor = result.get("nextCursor")
        except Exception as e:
            print(f"  Errore nel gruppo {group}: {e}")
            break
    return items

def resolve_stream_url(play_url, auth_sig, session=None):
    headers = {
        "user-agent": "MediaHubMX/2", "accept": "application/json",
        "content-type": "application/json; charset=utf-8", "content-length": "115",
        "accept-encoding": "gzip", "mediahubmx-signature": auth_sig
    }
    data = {"language": "de", "region": "AT", "url": play_url, "clientVersion": "3.0.2"}
    s = session or requests.Session()
    resp = s.post("https://vavoo.to/mediahubmx-resolve.json", json=data, headers=headers, timeout=10)
    resp.raise_for_status()
    result = resp.json()
    if result and len(result) > 0:
        return result[0].get("url")
    return None

def resolve_all_urls(channels, auth_sig, max_workers=10):
    session = requests.Session()
    resolved = []
    failed = 0
    def resolve_one(ch):
        try:
            stream_url = resolve_stream_url(ch["url"], auth_sig, session)
            if stream_url:
                return {**ch, "stream_url": stream_url}
            return None
        except Exception:
            return None
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(resolve_one, ch): ch for ch in channels}
        for future in as_completed(futures):
            ch = futures[future]
            try:
                result = future.result()
                if result:
                    resolved.append(result)
                else:
                    failed += 1
            except Exception:
                failed += 1
    session.close()
    return resolved, failed

def main():
    print("=== Generatore Playlist VAVOO.TO (TIVUSAT Order) ===\n")

    print("1. Ottenimento auth signature...")
    auth_sig = get_auth_signature()
    if not auth_sig:
        print("Errore: impossibile ottenere auth signature")
        sys.exit(1)
    print("   OK\n")

    print("2. Ottenimento gruppi...")
    try:
        resp = requests.get("https://www2.vavoo.to/live2/index?output=json", timeout=10)
        resp.raise_for_status()
        channels_raw = resp.json()
        groups = sorted(set(c["group"] for c in channels_raw))
    except Exception as e:
        print(f"Errore gruppi: {e}")
        sys.exit(1)
    print(f"   Trovati {len(groups)} gruppi\n")

    print("Quali gruppi includere? (es: 9 per Italy, 8 per Germany, o 'all' per tutti)")
    for i, g in enumerate(groups, 1):
        print(f"   {i:2d}. {g}")
    choice = input("> ").strip()

    if choice.lower() == "all":
        selected_groups = groups
    else:
        try:
            indices = [int(x.strip()) - 1 for x in choice.split(",")]
            selected_groups = [groups[i] for i in indices if 0 <= i < len(groups)]
        except (ValueError, IndexError):
            print("Selezione non valida, uso tutti i gruppi")
            selected_groups = groups

    print(f"\n3. Download canali per {len(selected_groups)} gruppi...")
    all_channels = []
    with ThreadPoolExecutor(max_workers=min(len(selected_groups), 5)) as executor:
        futures = {executor.submit(fetch_group, group, auth_sig): group for group in selected_groups}
        for future in as_completed(futures):
            group = futures[future]
            try:
                items = future.result()
                all_channels.extend(items)
                print(f"   [OK] {group}: {len(items)} canali")
            except Exception as e:
                print(f"   [ERRORE] {group}: {e}")

    print(f"\n   Totale canali grezzi: {len(all_channels)}")

    print("\n4. Elaborazione canali (rinomina, blacklist, ordinamento)...")
    seen = set()
    processed = []
    for ch in all_channels:
        name = normalize_italian_name(ch["name"])
        if not name: continue
        if any(bl in name for bl in ITALIAN_BLACKLIST): continue
        key = (name, ch["url"])
        if key in seen: continue
        seen.add(key)
        priority = get_channel_priority(name)
        logo = ch.get("logo", "")
        group = ch.get("group", "VAVOO")
        chno = priority if priority < 9999 else 0
        processed.append({
            "name": name, "url": ch["url"], "group": group,
            "logo": logo, "priority": priority, "chno": chno
        })

    processed.sort(key=lambda x: (x["priority"], x["name"]))
    print(f"   Canali unici dopo deduplica: {len(processed)}")

    print("\n5. Generazione playlist M3U (resolver URLs)...")
    user_agent = "okhttp/4.11.0"
    resolver_base = "https://vavoo-resolver.mic-deangelis.workers.dev/resolve?url="
    m3u_lines = ['#EXTM3U x-tvg-url="https://raw.githubusercontent.com/mich-de/vavoo-player/master/epg.xml"\n']
    for idx, ch in enumerate(processed, 1):
        url_encoded = quote(ch["name"].encode("utf-8"))
        chno = ch["chno"] if ch["chno"] > 0 else idx
        m3u_lines.append("#EXTVLCOPT:http-user-agent=%s\n" % user_agent)
        extinf = '#EXTINF:-1 tvg-id="%s" tvg-name="%s" tvg-chno="%s" tvg-logo="%s" group-title="%s",%s\n' % (
            url_encoded, url_encoded, chno, ch["logo"], ch["group"], ch["name"]
        )
        m3u_lines.append(extinf)
        resolver_url = resolver_base + quote(ch["url"], safe="")
        m3u_lines.append(resolver_url + "\n")

    with open(M3U_PATH, "w", encoding="utf-8") as f:
        f.writelines(m3u_lines)

    print(f"   Playlist salvata: {M3U_PATH}")
    print(f"   Canali totali: {len(processed)}")
    print(f"   Resolver: https://vavoo-resolver.mic-deangelis.workers.dev")

    print("\n6. Apertura con mpv...")
    mpv_cmd = MPV_PATH if os.path.exists(MPV_PATH) else "mpv"
    if not os.path.exists(MPV_PATH):
        try:
            subprocess.run(["mpv", "--version"], capture_output=True, timeout=5)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            print("   mpv non trovato. Installalo da https://mpv.io/installation/")
            print(f"   Playlist salvata in: {M3U_PATH}")
            return

    try:
        subprocess.Popen([mpv_cmd, "--playlist", M3U_PATH, "--user-agent=okhttp/4.11.0"])
        print(f"   Playlist aperta con mpv!")
    except Exception as e:
        print(f"   Errore: {e}")

if __name__ == "__main__":
    main()
