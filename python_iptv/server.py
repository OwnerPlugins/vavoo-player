"""
IPTV Web Player — Backend Server
Flask API: channels, EPG, stream proxy, subtitles
"""
import os
import re
import json
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin, quote

import requests
from flask import Flask, jsonify, request, Response, send_from_directory
from flask_cors import CORS

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAYLIST_PATH = os.path.join(BASE_DIR, "playlist.m3u8")
EPG_PATH = os.path.join(BASE_DIR, "epg.xml")
LOGOS_DIR = os.path.join(BASE_DIR, "logos")
FRONTEND_DIR = os.path.join(BASE_DIR, "web-player", "dist")
SUBS_DIR = os.path.join(BASE_DIR, "python_iptv", "subs")

import uuid
import subliminal
from babelfish import Language
subliminal.region.configure('dogpile.cache.memory')

app = Flask(__name__, static_folder=FRONTEND_DIR)
CORS(app)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_epg_cache = None
_epg_mtime = 0

def _parse_playlist():
    """Parse M3U8 → list of channel dicts."""
    channels = []
    if not os.path.exists(PLAYLIST_PATH):
        return channels
    with open(PLAYLIST_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF:"):
            info = line
            url = lines[i + 1].strip() if i + 1 < len(lines) else ""
            # Parse attributes
            tvg_id = _attr(info, "tvg-id")
            tvg_name = _attr(info, "tvg-name")
            tvg_logo = _attr(info, "tvg-logo")
            group = _attr(info, "group-title")
            # Display name is after the comma
            name = info.split(",", 1)[1].strip() if "," in info else tvg_name
            channels.append({
                "id": tvg_id or name,
                "name": name,
                "tvg_id": tvg_id,
                "tvg_name": tvg_name,
                "logo": tvg_logo,
                "group": group or "Other",
                "url": url,
            })
            i += 2
        else:
            i += 1
    return channels

def _attr(line, key):
    """Extract attribute value from EXTINF line."""
    pattern = rf'{key}="([^"]*)"'
    m = re.search(pattern, line)
    return m.group(1) if m else ""

def _get_epg():
    """Parse and cache EPG XML."""
    global _epg_cache, _epg_mtime
    if not os.path.exists(EPG_PATH):
        return {}
    mtime = os.path.getmtime(EPG_PATH)
    if _epg_cache and mtime == _epg_mtime:
        return _epg_cache
    
    log.info("Parsing EPG XML...")
    epg = {}
    try:
        tree = ET.parse(EPG_PATH)
        root = tree.getroot()
        # Parse channels
        for ch in root.findall("channel"):
            ch_id = ch.get("id", "")
            display = ch.find("display-name")
            icon = ch.find("icon")
            epg[ch_id] = {
                "id": ch_id,
                "name": display.text if display is not None else ch_id,
                "icon": icon.get("src", "") if icon is not None else "",
                "programs": [],
            }
        # Parse programs
        for prog in root.findall("programme"):
            ch_id = prog.get("channel", "")
            start = _parse_xmltv_time(prog.get("start", ""))
            stop = _parse_xmltv_time(prog.get("stop", ""))
            title_el = prog.find("title")
            desc_el = prog.find("desc")
            category_el = prog.find("category")
            icon_el = prog.find("icon")
            if ch_id in epg:
                epg[ch_id]["programs"].append({
                    "start": start.isoformat() if start else "",
                    "stop": stop.isoformat() if stop else "",
                    "start_ts": start.timestamp() if start else 0,
                    "stop_ts": stop.timestamp() if stop else 0,
                    "title": title_el.text if title_el is not None else "",
                    "desc": desc_el.text if desc_el is not None else "",
                    "category": category_el.text if category_el is not None else "",
                    "icon": icon_el.get("src", "") if icon_el is not None else "",
                })
    except Exception as e:
        log.error(f"EPG parse error: {e}")
    
    _epg_cache = epg
    _epg_mtime = mtime
    log.info(f"EPG loaded: {len(epg)} channels")
    return epg

def _parse_xmltv_time(s):
    """Parse XMLTV timestamp like 20260224200000 +0100"""
    if not s:
        return None
    try:
        s = s.strip()
        # Try with timezone offset
        if " " in s:
            return datetime.strptime(s, "%Y%m%d%H%M%S %z")
        return datetime.strptime(s, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    except Exception:
        return None

# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.route("/api/channels")
def api_channels():
    """Return all channels grouped by bouquet."""
    channels = _parse_playlist()
    groups = {}
    for ch in channels:
        g = ch["group"]
        if g not in groups:
            groups[g] = []
        groups[g].append(ch)
    return jsonify({"groups": groups, "total": len(channels)})

@app.route("/api/epg")
def api_epg():
    """Return EPG for a specific channel."""
    channel_id = request.args.get("channel_id", "")
    if not channel_id:
        return jsonify({"error": "channel_id required"}), 400
    
    epg = _get_epg()
    ch_epg = epg.get(channel_id, {})
    if not ch_epg:
        return jsonify({"channel_id": channel_id, "programs": [], "current": None, "next": None})
    
    now = datetime.now(timezone.utc).timestamp()
    programs = ch_epg.get("programs", [])
    current = None
    next_prog = None
    
    for p in programs:
        if p["start_ts"] <= now < p["stop_ts"]:
            # Prefer the most recently started overlapping program
            if not current or p["start_ts"] > current["start_ts"]:
                current = p
                
    if current:
        for p in programs:
            if p["start_ts"] >= current["stop_ts"]:
                next_prog = p
                break
    
    return jsonify({
        "channel_id": channel_id,
        "programs": programs,
        "current": current,
        "next": next_prog,
    })

@app.route("/api/epg/guide")
def api_epg_guide():
    """Return EPG guide for all channels (today)."""
    epg = _get_epg()
    now = datetime.now(timezone.utc).timestamp()
    guide = {}
    
    for ch_id, data in epg.items():
        current = None
        upcoming = []
        
        # 1. Find the most recently started current program
        for p in data.get("programs", []):
            if p["start_ts"] <= now < p["stop_ts"]:
                if not current or p["start_ts"] > current["start_ts"]:
                    current = p

        # 2. Add upcoming strictly after current stop_ts
        for p in data.get("programs", []):
            if current and p["start_ts"] < current["stop_ts"]:
                continue
            if p["start_ts"] > now and len(upcoming) < 5:
                upcoming.append(p)
                
        if current or upcoming:
            guide[ch_id] = {
                "name": data.get("name", ch_id),
                "current": current,
                "upcoming": upcoming[:5],
            }
    return jsonify(guide)

@app.route("/proxy/stream")
def proxy_stream():
    """Proxy HLS streams to bypass CORS."""
    url = request.args.get("url", "")
    if not url:
        return "url required", 400
    
    try:
        headers = {"User-Agent": "okhttp/4.11.0"}
        content_type_hint = ""
        
        # Determine if this is likely an m3u8 by URL alone
        url_lower = url.lower()
        is_segment = url_lower.endswith(".ts") or url_lower.endswith(".aac") or url_lower.endswith(".mp4")
        likely_m3u8 = ".m3u8" in url_lower or ".m3u" in url_lower
        
        if is_segment:
            # Binary segment — stream directly, never read as text
            r = requests.get(url, headers=headers, stream=True, timeout=15)
            ct = r.headers.get("Content-Type", "video/mp2t")
            return Response(
                r.iter_content(chunk_size=65536),
                content_type=ct,
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
        # Could be m3u8 or unknown — fetch and inspect
        r = requests.get(url, headers=headers, timeout=15)
        content_type = r.headers.get("Content-Type", "")
        content = r.text
        
        is_m3u8 = (
            likely_m3u8 or
            "mpegurl" in content_type.lower() or
            content.strip().startswith("#EXTM3U") or
            "#EXTINF:" in content[:500] or
            "#EXT-X-STREAM-INF" in content[:500]
        )
        
        if is_m3u8:
            # Rewrite all URLs to go through proxy with ABSOLUTE paths
            # MUST use r.url (final redirected URL), not the original url
            base_url = r.url.rsplit("/", 1)[0] + "/"
            host = request.host_url.rstrip("/")
            lines = content.split("\n")
            rewritten = []
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    if not stripped.startswith("http"):
                        stripped = urljoin(base_url, stripped)
                    stripped = f"{host}/proxy/stream?url={quote(stripped)}"
                elif stripped.startswith("#EXT-X-KEY") and "URI=" in stripped:
                    def rewrite_uri(m, _base=base_url, _host=host):
                        key_url = m.group(1)
                        if not key_url.startswith("http"):
                            key_url = urljoin(_base, key_url)
                        return f'URI="{_host}/proxy/stream?url={quote(key_url)}"'
                    stripped = re.sub(r'URI="([^"]*)"', rewrite_uri, stripped)
                rewritten.append(stripped)
            return Response(
                "\n".join(rewritten),
                content_type="application/vnd.apple.mpegurl",
                headers={"Access-Control-Allow-Origin": "*"}
            )
        
        # Unknown content — pass through as-is
        return Response(
            r.content,
            content_type=content_type or "application/octet-stream",
            headers={"Access-Control-Allow-Origin": "*"}
        )
    except Exception as e:
        log.error(f"Proxy error for {url}: {e}")
        return str(e), 502

@app.route("/api/subtitles")
def api_subtitles():
    """Search subtitles for a movie/show title using subliminal."""
    title = request.args.get("title", "")
    lang = request.args.get("lang", "it")
    if not title:
        return jsonify({"error": "title required"}), 400
    
    try:
        # Clean title from EPG junk like " (1a TV)", " (Replica)"
        clean_title = re.sub(r'\s*\(.*$', '', title).strip()
        
        # Ensure the subs directory exists
        if not os.path.exists(SUBS_DIR):
            os.makedirs(SUBS_DIR, exist_ok=True)
            
        video = subliminal.Video.fromname(clean_title)
        
        # Resolve correct babelfish Language object from 'it'/'en' codes
        try:
            sub_lang = Language.fromalpha2(lang) if len(lang) == 2 else Language(lang)
        except ValueError:
            sub_lang = Language.fromietf(lang)
            
        # Download best subtitles using babelfish Language
        best_subs = subliminal.download_best_subtitles([video], {sub_lang})
        subs_list = best_subs.get(video, [])
        
        results = []
        for s in subs_list[:10]:
            uid = str(uuid.uuid4())
            filename = f"{uid}.srt"
            local_path = os.path.join(SUBS_DIR, filename)
            
            with open(local_path, "wb") as f:
                f.write(s.content)
                
            results.append({
                "title": f"[{s.provider_name.upper()}] {clean_title}",
                "year": getattr(video, "year", ""),
                "lang": lang,
                "format": "srt",
                "download_url": f"/subs/{filename}",
                "rating": 5,
            })
            
        return jsonify({"title": title, "lang": lang, "results": results})
    except Exception as e:
        log.error(f"Subtitle search error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/subs/<filename>")
def serve_subs(filename):
    """Serve downloaded subtitle files locally over the proxy."""
    return send_from_directory(SUBS_DIR, filename)

# ---------------------------------------------------------------------------
# Static Frontend (SPA Routing)
# ---------------------------------------------------------------------------

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    if path.startswith("logos/"):
        return send_from_directory(BASE_DIR, path)

    # If the file exists in the build dir, serve it
    if path != "" and os.path.exists(os.path.join(FRONTEND_DIR, path)):
        return send_from_directory(FRONTEND_DIR, path)
    
    # Otherwise fallback to index.html for client-side routing
    return send_from_directory(FRONTEND_DIR, "index.html")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    log.info(f"Playlist: {PLAYLIST_PATH}")
    log.info(f"EPG: {EPG_PATH}")
    log.info(f"Logos: {LOGOS_DIR}")
    log.info(f"Frontend: {FRONTEND_DIR}")
    app.run(host="0.0.0.0", port=port, debug=False)
