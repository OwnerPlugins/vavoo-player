#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mini server per risolvere URL Vavoo on-the-fly (redirect, non proxy)"""

import json
import os
import sys
import time
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import quote, unquote, parse_qs, urlparse

AUTH_API = "https://www.lokke.app/api/app/ping"
RESOLVE_API = "https://vavoo.to/mediahubmx-resolve.json"
PORT = 18920

_auth_cache = {"sig": None, "ts": 0}
_lock = threading.Lock()

def get_sig():
    with _lock:
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
    with _lock:
        _auth_cache["sig"] = sig
        _auth_cache["ts"] = time.time()
    return sig

def resolve(play_url):
    sig = get_sig()
    r = requests.post(RESOLVE_API, json={"language": "de", "region": "AT", "url": play_url, "clientVersion": "3.0.2"}, headers={"user-agent": "MediaHubMX/2", "accept": "application/json", "content-type": "application/json; charset=utf-8", "content-length": "115", "accept-encoding": "gzip", "mediahubmx-signature": sig}, timeout=10)
    return r.json()[0]["url"]

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/play":
            params = parse_qs(parsed.query)
            play_url = params.get("url", [None])[0]
            if play_url:
                try:
                    stream_url = resolve(unquote(play_url))
                    print(f"  -> {stream_url[:80]}...")
                    self.send_response(302)
                    self.send_header("Location", stream_url)
                    self.send_header("User-Agent", "okhttp/4.11.0")
                    self.end_headers()
                    return
                except Exception as e:
                    print(f"  Errore: {e}")
                    self.send_response(500)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(f"Errore: {e}".encode())
                    return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        pass

def generate_playlist(channels, port):
    lines = ['#EXTM3U x-tvg-url="https://raw.githubusercontent.com/mich-de/vavoo-player/master/epg.xml"\n']
    for idx, ch in enumerate(channels, 1):
        name = ch["name"]
        logo = ch.get("logo", "")
        group = ch.get("group", "VAVOO")
        chno = ch.get("chno", idx)
        play_url = ch["url"]
        proxy_url = f"http://127.0.0.1:{port}/play?url={quote(play_url, safe='')}"
        url_encoded = quote(name.encode("utf-8"))
        lines.append("#EXTVLCOPT:http-user-agent=okhttp/4.11.0\n")
        lines.append('#EXTINF:-1 tvg-id="%s" tvg-name="%s" tvg-chno="%s" tvg-logo="%s" group-title="%s",%s\n' % (
            url_encoded, url_encoded, chno, logo, group, name
        ))
        lines.append(proxy_url + "\n")
    return "".join(lines)

def start_server(port):
    server = HTTPServer(("127.0.0.1", port), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server

if __name__ == "__main__":
    print(f"Server Vavoo su http://127.0.0.1:{PORT}")
    server = start_server(PORT)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nServer fermato")
        server.shutdown()
