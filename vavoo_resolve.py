#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vavoo stream resolver for mpv - resolves play URLs on-the-fly"""

import sys
import json
import time
import requests
import subprocess
import os

AUTH_API = "https://www.lokke.app/api/app/ping"
RESOLVE_API = "https://vavoo.to/mediahubmx-resolve.json"
MPV_PATH = r"C:\Users\mdeangelis\Downloads\mpv-x86_64\mpv.exe"

_auth_cache = {"sig": None, "ts": 0}

def get_sig():
    if _auth_cache["sig"] and (time.time() - _auth_cache["ts"] < 540):
        return _auth_cache["sig"]
    data = {
        "token": "ldCvE092e7gER0rVIajfsXIvRhwlrAzP6_1oEJ4q6HH89QHt24v6NNL_jQJO219hiLOXF2hqEfsUuEWitEIGN4EaHHEHb7Cd7gojc5SQYRFzU3XWo_kMeryAUbcwWnQrnf0-",
        "reason": "app-blur", "locale": "de", "theme": "dark",
        "metadata": {"device": {"type": "Handset", "brand": "google", "model": "Nexus", "name": "21081111RG", "uniqueId": "d10e5d99ab665233"}, "os": {"name": "android", "version": "7.1.2", "abis": ["arm64-v8a"], "host": "android"}, "app": {"platform": "android", "version": "1.1.0", "buildId": "97215000", "engine": "hbc85", "signatures": ["6e8a975e3cbf07d5de823a760d4c2547f86c1403105020adee5de67ac510999e"], "installer": "com.android.vending"}, "version": {"package": "app.lokke.main", "binary": "1.1.0", "js": "1.1.0"}, "platform": {"isAndroid": True, "isIOS": False, "isTV": False, "isWeb": False, "isMobile": True, "isWebTV": False, "isElectron": False}},
        "appFocusTime": 0, "playerActive": False, "playDuration": 0, "devMode": True, "hasAddon": True, "castConnected": False, "package": "app.lokke.main", "version": "1.1.0", "process": "app", "firstAppStart": 1772388338206, "lastAppStart": 1772388338206, "ipLocation": None, "adblockEnabled": False, "proxy": {"supported": ["ss", "openvpn"], "engine": "openvpn", "ssVersion": 1, "enabled": False, "autoServer": True, "id": "fi-hel"}, "iap": {"supported": True}
    }
    r = requests.post(AUTH_API, json=data, headers={"user-agent": "okhttp/4.11.0", "accept": "application/json", "content-type": "application/json; charset=utf-8", "accept-encoding": "gzip"}, timeout=10)
    sig = r.json().get("addonSig")
    _auth_cache["sig"] = sig
    _auth_cache["ts"] = time.time()
    return sig

def resolve(play_url):
    sig = get_sig()
    r = requests.post(RESOLVE_API, json={"language": "de", "region": "AT", "url": play_url, "clientVersion": "3.0.2"}, headers={"user-agent": "MediaHubMX/2", "accept": "application/json", "content-type": "application/json; charset=utf-8", "content-length": "115", "accept-encoding": "gzip", "mediahubmx-signature": sig}, timeout=10)
    return r.json()[0]["url"]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: vavoo_resolve.py <play_url>")
        sys.exit(1)
    play_url = sys.argv[1]
    try:
        stream_url = resolve(play_url)
        mpv = MPV_PATH if os.path.exists(MPV_PATH) else "mpv"
        subprocess.run([mpv, "--user-agent=okhttp/4.11.0", "--cache=yes", "--demuxer-max-bytes=50MiB", "--demuxer-readahead-secs=30", stream_url])
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
