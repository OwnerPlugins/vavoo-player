"""
Playlist Generator - Fetches channels from Vavoo API and generates M3U8 playlists.

Improvements:
- Configuration-driven (config.json) for all settings
- Parallel channel fetching with ThreadPoolExecutor
- Improved name normalization with fuzzy matching fallback
- Catchup/timeshift support in M3U8 output
- Channel number (tvg-chno) assignment
- Duplicate detection and consolidation
- Playlist statistics/summary output
- Better error handling with retries
- Type hints throughout
"""

import json
import logging
import os
import re
import sys
import time
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import requests

from src.data_manager import DataManager

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load configuration from JSON file with fallback defaults."""
    config_path = path or CONFIG_PATH
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    logging.warning(f"Config file not found at {config_path}, using defaults")
    return {}


@dataclass
class ChannelInfo:
    """Represents a processed channel entry."""
    name: str
    url: str
    group: str
    logo: str
    norm_name: str = ""
    tvg_id: str = ""
    tvg_name: str = ""
    clean_name: str = ""
    priority: int = 9999
    categories: List[str] = field(default_factory=lambda: ["Other"])
    channel_number: int = 0
    catchup_source: str = ""
    catchup_days: int = 0
    no_epg: bool = False
    logo_override: str = ""


class PlaylistGenerator:
    """Handles fetching channels from Vavoo API and generating M3U8 playlists."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config = load_config(config_path)
        self._api_cfg = self.config.get("api", {})
        self._auth_cfg = self.config.get("auth", {})
        self._fetch_cfg = self.config.get("fetching", {})
        self._output_cfg = self.config.get("output", {})
        self._catchup_cfg = self._output_cfg.get("catchup", {})
        self._auth_cache: Dict[str, Any] = {"sig": None, "timestamp": 0}
        self.dm = DataManager()
        self._logos_cache: Optional[Dict[str, str]] = None
        self._session = self._create_session()
        self._stats: Dict[str, Any] = {
            "fetched": 0,
            "deduplicated": 0,
            "blacklisted": 0,
            "renamed": 0,
            "epg_matched": 0,
            "logo_resolved": 0,
            "channels_written": 0,
            "categories": {},
        }
        self._auth_cache: Dict[str, Any] = {"sig": None, "timestamp": 0}
        self.dm = DataManager()
        self._logos_cache: Optional[Dict[str, str]] = None
        self._session = self._create_session()
        self._stats: Dict[str, Any] = {
            "fetched": 0,
            "deduplicated": 0,
            "blacklisted": 0,
            "renamed": 0,
            "epg_matched": 0,
            "logo_resolved": 0,
            "channels_written": 0,
            "categories": {},
        }

    def _create_session(self) -> requests.Session:
        """Create a reusable HTTP session with connection pooling."""
        session = requests.Session()
        session.headers.update({"User-Agent": self._api_cfg.get("user_agent", "okhttp/4.11.0")})
        return session

    def _get_auth_signature(self) -> Optional[str]:
        """Performs handshake to get the addon signature with retry logic."""
        url = f"{self._api_cfg.get('base_url', 'https://www.vavoo.tv/api')}/app/ping"
        headers = {
            "user-agent": self._api_cfg.get("user_agent", "okhttp/4.11.0"),
            "accept": "application/json",
            "content-type": "application/json; charset=utf-8",
            "accept-encoding": "gzip",
        }

        device_id = self._auth_cfg.get("device_id", "d10e5d99ab665233")
        data = {
            "token": self._auth_cfg.get("token", ""),
            "reason": "app-blur",
            "locale": self._auth_cfg.get("locale", "de"),
            "theme": self._auth_cfg.get("theme", "dark"),
            "metadata": {
                "device": {"type": "Handset", "brand": "google", "model": "Nexus", "name": "21081111RG", "uniqueId": device_id},
                "os": {"name": "android", "version": "7.1.2", "abis": ["arm64-v8a", "armeabi-v7a", "armeabi"], "host": "android"},
                "app": {"platform": "android", "version": "3.1.20", "buildId": "289515000", "engine": "hbc85", "signatures": ["6e8a975e3cbf07d5de823a760d4c2547f86c1403105020adee5de67ac510999e"], "installer": "app.revanced.manager.flutter"},
                "version": {"package": "tv.vavoo.app", "binary": "3.1.20", "js": "3.1.20"},
            },
            "appFocusTime": 0,
            "playerActive": False,
            "playDuration": 0,
            "devMode": False,
            "hasAddon": True,
            "castConnected": False,
            "package": "tv.vavoo.app",
            "version": "3.1.20",
            "process": "app",
            "firstAppStart": 1743962904623,
            "lastAppStart": 1743962904623,
            "ipLocation": "",
            "adblockEnabled": True,
            "proxy": {"supported": ["ss", "openvpn"], "engine": "ss", "ssVersion": 1, "enabled": True, "autoServer": True, "id": "pl-waw"},
            "iap": {"supported": False},
        }

        max_retries = self._api_cfg.get("max_retries", 3)
        retry_delay = self._api_cfg.get("retry_delay_seconds", 2)

        for attempt in range(max_retries):
            try:
                logging.info("Requesting authentication signature...")
                response = self._session.post(url, json=data, headers=headers, timeout=self._api_cfg.get("timeout_seconds", 15), verify=False)
                response.raise_for_status()
                sig = response.json().get("addonSig")
                if sig:
                    self._auth_cache["sig"] = sig
                    self._auth_cache["timestamp"] = time.time()
                    logging.info("Signature received successfully.")
                return sig
            except Exception as e:
                logging.warning(f"Auth attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
        logging.error("All authentication attempts failed")
        return None

    def get_signature(self, max_age_seconds: Optional[int] = None) -> Optional[str]:
        """Returns a valid signature, refreshing if expired."""
        if max_age_seconds is None:
            max_age_seconds = self._api_cfg.get("signature_max_age_seconds", 600)
        if self._auth_cache["sig"] and (time.time() - self._auth_cache["timestamp"] < max_age_seconds):
            return self._auth_cache["sig"]
        return self._get_auth_signature()

    def _fetch_group(self, group: str, sig: str) -> List[Dict[str, Any]]:
        """Fetch channels for a single group with pagination."""
        channels = []
        cursor = 0
        timeout = self._api_cfg.get("timeout_seconds", 15)
        client_version = self._api_cfg.get("client_version", "3.0.2")
        catalog_url = self._api_cfg.get("catalog_url", "https://vavoo.to/mediahubmx-catalog.json")

        while True:
            data = {
                "language": "en",
                "region": "US",
                "catalogId": "iptv",
                "id": "iptv",
                "adult": False,
                "search": "",
                "sort": "name",
                "filter": {"group": group},
                "cursor": cursor,
                "clientVersion": client_version,
            }
            headers = {
                "user-agent": self._api_cfg.get("user_agent", "okhttp/4.11.0"),
                "accept": "application/json",
                "content-type": "application/json; charset=utf-8",
                "mediahubmx-signature": sig,
            }

            try:
                r = self._session.post(catalog_url, json=data, headers=headers, timeout=timeout, verify=False)
                r.raise_for_status()
                res = r.json()
                items = res.get("items", [])
                if not items:
                    break

                for item in items:
                    url = item.get("url")
                    name = item.get("name")
                    if url:
                        channels.append({
                            "name": name,
                            "url": url,
                            "group": group,
                            "logo": item.get("logo"),
                        })

                cursor = res.get("nextCursor")
                if cursor is None:
                    break
            except Exception as e:
                logging.error(f"Error fetching {group}: {e}")
                break

        return channels

    def fetch_all_channels(self, target_groups: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Fetches channels from the API using parallel fetching."""
        if target_groups is None:
            target_groups = self._fetch_cfg.get("default_groups", ["Italy"])

        sig = self.get_signature()
        if not sig:
            logging.error("Could not obtain signature. Aborting fetch.")
            return []

        all_channels: List[Dict[str, Any]] = []
        seen_urls: Set[Tuple[str, str]] = set()
        max_workers = self._fetch_cfg.get("max_workers", 5)

        logging.info(f"Fetching {len(target_groups)} groups with {max_workers} workers...")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_group = {executor.submit(self._fetch_group, group, sig): group for group in target_groups}

            for future in as_completed(future_to_group):
                group = future_to_group[future]
                try:
                    group_channels = future.result()
                    for ch in group_channels:
                        seen_key = (ch["name"], ch["url"])
                        if seen_key not in seen_urls:
                            all_channels.append(ch)
                            seen_urls.add(seen_key)
                    logging.info(f" > Found {len(group_channels)} channels in {group}")
                except Exception as e:
                    logging.error(f"Error processing group {group}: {e}")

        self._stats["fetched"] = len(all_channels)

        rsi_channels = self._search_rsi_channels(sig)
        for rsi_ch in rsi_channels:
            seen_key = (rsi_ch["name"], rsi_ch["url"])
            if seen_key not in seen_urls:
                all_channels.append(rsi_ch)
                seen_urls.add(seen_key)

        logging.info(f"Total channels fetched: {len(all_channels)}")
        return all_channels

    def _search_rsi_channels(self, sig: str) -> List[Dict[str, Any]]:
        """Searches specifically for RSI channels in likely groups."""
        target_names = self._fetch_cfg.get("rsi_target_names", ["RSI LA 1", "RSI LA 2", "RSI LA1", "RSI LA2"])
        search_groups = self._fetch_cfg.get("rsi_search_groups", ["Italy", "Germany", "Vavoo", "Switzerland", "Swiss", "Other"])
        search_queries = self._fetch_cfg.get("rsi_search_queries", ["RSI LA", "RSI LA 1", "RSI LA 2", "RSI", "LA 1", "LA 2"])
        timeout = self._api_cfg.get("timeout_seconds", 15)
        client_version = self._api_cfg.get("client_version", "3.0.2")
        catalog_url = self._api_cfg.get("catalog_url", "https://vavoo.to/mediahubmx-catalog.json")

        found = []
        seen_urls: Set[str] = set()

        logging.info("Attempting targeted search for RSI channels...")

        for group in search_groups:
            for query in search_queries:
                cursor = 0
                while True:
                    data = {
                        "language": "en",
                        "region": "US",
                        "catalogId": "iptv",
                        "id": "iptv",
                        "adult": False,
                        "search": query,
                        "sort": "name",
                        "filter": {"group": group},
                        "cursor": cursor,
                        "clientVersion": client_version,
                    }
                    headers = {
                        "user-agent": self._api_cfg.get("user_agent", "okhttp/4.11.0"),
                        "accept": "application/json",
                        "content-type": "application/json; charset=utf-8",
                        "mediahubmx-signature": sig,
                    }

                    try:
                        r = self._session.post(catalog_url, json=data, headers=headers, timeout=timeout, verify=False)
                        if r.status_code == 200:
                            res = r.json()
                            items = res.get("items", [])
                            if not items:
                                break

                            for item in items:
                                name = item.get("name", "")
                                url = item.get("url")

                                if url and url not in seen_urls:
                                    clean_name_up = name.upper()
                                    if any(tn.upper() in clean_name_up for tn in target_names):
                                        found.append({
                                            "name": name,
                                            "url": url,
                                            "group": "Switzerland",
                                            "logo": item.get("logo"),
                                            "priority": 100,
                                        })
                                        seen_urls.add(url)

                            cursor = res.get("nextCursor")
                            if cursor is None:
                                break
                        else:
                            break
                    except Exception:
                        break

        return found

    def _build_logos_cache(self, logos_dir: str) -> Dict[str, str]:
        """Pre-build a normalized logo filename cache for O(1) lookups."""
        cache = {}
        if os.path.exists(logos_dir):
            for f in os.listdir(logos_dir):
                if f.lower().endswith((".png", ".svg", ".jpg")):
                    cache[f.lower()] = f
        return cache

    def _normalize_name(self, name: str) -> str:
        """Cleans channel names with improved regex patterns."""
        if not name:
            return ""
        n = name.upper()
        n = re.sub(r"\[.*?\]", "", n)
        n = re.sub(r"\(.*?\)", "", n)
        n = re.sub(r"\s+(HD|FHD|SD|4K|ITA|ITALIA|BACKUP|TIMVISION|PLUS)$", "", n)

        if not n.startswith("HISTORY"):
            n = re.sub(r"\s+\.[A-Z0-9]{1,3}$", "", n)
        n = re.sub(r"\s\+$", "", n)
        n = re.sub(r"[^A-Z0-9 ]", "", n)
        n = re.sub(r"\s+", " ", n)
        return n.strip()

    def _fuzzy_match_epg(self, norm_name: str, epg_map: Dict[str, str], threshold: float = 0.85) -> Optional[str]:
        """Fallback fuzzy matching for EPG IDs when exact match fails."""
        best_match = None
        best_score = threshold

        for key in epg_map:
            score = SequenceMatcher(None, norm_name, key).ratio()
            if score > best_score:
                best_score = score
                best_match = epg_map[key]

        if best_match:
            logging.debug(f"Fuzzy matched '{norm_name}' -> '{best_match}' (score: {best_score:.2f})")
        return best_match

    def _get_categories(self, norm_name: str) -> List[str]:
        """Returns ALL matching categories for a channel."""
        bouquets = self.config.get("bouquets", {})
        categories = []
        for category, keywords in bouquets.items():
            for k in keywords:
                if k in norm_name:
                    categories.append(category)
                    break
        return categories if categories else ["Other"]

    def _get_priority(self, norm_name: str) -> int:
        """Assigns sort priority based on TIVUSAT_ORDER mapping."""
        tivusat = self.config.get("tivusat_order", {})
        priority_fallbacks = self.config.get("priority_fallbacks", {})
        default_priority = self.config.get("default_priority", 9999)

        if norm_name in tivusat:
            return tivusat[norm_name]

        for k, v in tivusat.items():
            if k in norm_name:
                return v

        for keyword, priority in priority_fallbacks.items():
            if keyword in norm_name:
                return priority

        return default_priority

    def _is_blacklisted(self, norm_name: str) -> bool:
        """Check if channel is in the blacklist."""
        blacklist = self.config.get("blacklist", [])
        return any(bl in norm_name for bl in blacklist)

    def _apply_rename(self, norm_name: str) -> Tuple[str, bool]:
        """Apply rename rules from config. Returns (new_name, was_renamed)."""
        renames = self.config.get("renames", {})
        if norm_name in renames:
            return renames[norm_name], True

        for key, value in renames.items():
            if key in norm_name and len(key) > 3:
                return value, True

        return norm_name, False

    def _resolve_logo(self, norm_name: str, epg_id: str, original_logo: str, logo_override: str = "") -> str:
        """Resolve logo with multiple fallback strategies."""
        logo_base_url = self._output_cfg.get("logo_base_url", "https://raw.githubusercontent.com/mich-de/vavoo-player/master/logos/")

        if logo_override:
            return logo_override.replace("logos/", logo_base_url)

        if epg_id:
            if self._logos_cache is None:
                logos_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logos")
                if not os.path.exists(logos_dir):
                    logos_dir = os.path.join(os.path.dirname(__file__), "logos")
                self._logos_cache = self._build_logos_cache(logos_dir)

            target_fname = f"{epg_id}.png".lower()
            matched_file = self._logos_cache.get(target_fname)
            if matched_file:
                self._stats["logo_resolved"] += 1
                return f"{logo_base_url}{matched_file}"

            for ext in [".png", ".svg", ".jpg"]:
                target_fname = f"{epg_id}{ext}".lower()
                matched_file = self._logos_cache.get(target_fname)
                if matched_file:
                    self._stats["logo_resolved"] += 1
                    return f"{logo_base_url}{matched_file}"

        return original_logo

    def _assign_channel_number(self, norm_name: str, priority: int) -> int:
        """Assign channel number based on TIVUSAT_ORDER priority."""
        tivusat = self.config.get("tivusat_order", {})
        if norm_name in tivusat:
            return tivusat[norm_name]
        for k, v in tivusat.items():
            if k in norm_name:
                return v
        return 0

    def process_channels(self, channels: List[Dict[str, Any]]) -> List[ChannelInfo]:
        """Process raw channels into ChannelInfo objects with all metadata."""
        processed: List[ChannelInfo] = []
        epg_map = self.config.get("epg_map", {})
        logo_overrides = self.config.get("logo_overrides", {})
        no_epg_channels = set(self.config.get("no_epg_channels", []))

        logging.info("Loading EPG data for name resolution...")
        self.dm.load_all_epgs()

        for ch in channels:
            norm_name = self._normalize_name(ch["name"])

            if self._is_blacklisted(norm_name):
                self._stats["blacklisted"] += 1
                continue

            original_norm = norm_name
            norm_name, was_renamed = self._apply_rename(norm_name)
            if was_renamed:
                self._stats["renamed"] += 1

            is_no_epg = norm_name in no_epg_channels or original_norm in no_epg_channels

            logo_override = logo_overrides.get(norm_name, "")
            if not logo_override:
                logo_override = logo_overrides.get(original_norm, "")

            categories = self._get_categories(norm_name)
            priority = self._get_priority(norm_name)
            channel_number = self._assign_channel_number(norm_name, priority)

            epg_id = "" if is_no_epg else epg_map.get(norm_name, "")
            if not epg_id and not is_no_epg:
                epg_id = self._fuzzy_match_epg(norm_name, epg_map)
                if epg_id:
                    self._stats["epg_matched"] += 1

            clean_display_name = norm_name
            if epg_id:
                epg_name = self.dm.get_clean_epg_name(epg_id)
                if epg_name:
                    clean_display_name = epg_name

            tvg_id = epg_id if epg_id else norm_name
            if is_no_epg:
                tvg_id = ""

            tvg_name = tvg_id if tvg_id else clean_display_name
            if is_no_epg:
                tvg_name = clean_display_name
                tvg_id = ""

            logo_path = self._resolve_logo(norm_name, epg_id, ch.get("logo", ""), logo_override)

            catchup_source = ""
            catchup_days = 0
            if self._catchup_cfg.get("enabled", False):
                catchup_source = self._catchup_cfg.get("source", "xmltv")
                catchup_days = self._catchup_cfg.get("days", 7)

            for category in categories:
                ch_info = ChannelInfo(
                    name=ch["name"],
                    url=ch["url"],
                    group=category,
                    logo=ch.get("logo", ""),
                    norm_name=norm_name,
                    tvg_id=tvg_id,
                    tvg_name=tvg_name,
                    clean_name=clean_display_name,
                    priority=priority,
                    categories=categories.copy(),
                    channel_number=channel_number,
                    catchup_source=catchup_source,
                    catchup_days=catchup_days,
                    no_epg=is_no_epg,
                    logo_override=logo_override,
                )
                processed.append(ch_info)
                self._stats["categories"][category] = self._stats["categories"].get(category, 0) + 1

        processed.sort(key=lambda x: (x.priority, x.group, x.norm_name))
        return processed

    def generate_m3u8(self, output_path: str, groups: Optional[List[str]] = None, is_xc: bool = False) -> bool:
        """Generates an M3U8 playlist file with sorting, categorization, and local logos."""
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
                logging.info(f"Deleted existing playlist: {output_path}")
            except OSError as e:
                logging.warning(f"Error deleting existing playlist: {e}")

        channels = self.fetch_all_channels(groups)
        logging.info(f"DEBUG: fetch_all_channels returned {len(channels)} items.")

        if not channels:
            logging.warning("No channels found to write.")
            return False

        processed = self.process_channels(channels)

        if not processed:
            logging.warning("No valid channels to write.")
            return False

        try:
            logging.info(f"Writing {len(processed)} channels to {output_path}...")
            with open(output_path, "w", encoding="utf-8") as f:
                epg_url = self._output_cfg.get("epg_url", "https://raw.githubusercontent.com/mich-de/vavoo-player/master/epg.xml")
                user_agent = self._api_cfg.get("user_agent", "okhttp/4.11.0")
                catchup_enabled = self._catchup_cfg.get("enabled", False)
                catchup_source = self._catchup_cfg.get("source", "xmltv")
                catchup_days = self._catchup_cfg.get("days", 7)

                f.write(f'#EXTM3U x-tvg-url="{epg_url}"')
                if catchup_enabled:
                    f.write(f' catchup="{catchup_source}" catchup-days="{catchup_days}"')
                f.write("\n")

                for ch in processed:
                    f.write(f"#EXTVLCOPT:http-user-agent={user_agent}\n")

                    extinf = f'#EXTINF:-1'
                    if ch.channel_number > 0:
                        extinf += f' tvg-chno="{ch.channel_number}"'
                    extinf += f' tvg-id="{ch.tvg_id}"'
                    extinf += f' tvg-name="{ch.clean_name}"'
                    extinf += f' tvg-logo="{ch.logo_override or ch.logo}"'
                    extinf += f' channel="{ch.tvg_id}"'
                    extinf += f' group-title="{ch.group}"'
                    if catchup_enabled:
                        extinf += f' catchup="{catchup_source}" catchup-days="{catchup_days}"'
                    extinf += f',{ch.clean_name}'

                    f.write(f"{extinf}\n")
                    f.write(f"{ch.url}\n")
                    self._stats["channels_written"] += 1

            logging.info("Playlist generated successfully.")
            self._print_stats()
            return True
        except Exception as e:
            logging.error(f"Error writing playlist: {e}")
            return False

    def _print_stats(self):
        """Print playlist generation statistics."""
        logging.info("=" * 50)
        logging.info("Playlist Generation Statistics:")
        logging.info(f"  Channels fetched:     {self._stats['fetched']}")
        logging.info(f"  Channels blacklisted: {self._stats['blacklisted']}")
        logging.info(f"  Channels renamed:     {self._stats['renamed']}")
        logging.info(f"  EPG matches:          {self._stats['epg_matched']}")
        logging.info(f"  Logos resolved:       {self._stats['logo_resolved']}")
        logging.info(f"  Entries written:      {self._stats['channels_written']}")
        logging.info("  Categories:")
        for cat, count in sorted(self._stats["categories"].items(), key=lambda x: x[1], reverse=True):
            logging.info(f"    {cat}: {count}")
        logging.info("=" * 50)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("vavoo_player.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    gen = PlaylistGenerator()
    gen.generate_m3u8("test_playlist.m3u8", groups=["Italy", "Switzerland", "Vavoo"])
