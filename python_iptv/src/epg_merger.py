"""
EPG Merger - Merges multiple XMLTV EPG sources into a single file.

Downloads 4 EPG sources (IT primary/backup + CH primary/backup),
filters to only channels used in the playlist (from EPG_MAP),
filters CH to only RSI LA 1/LA 2, deduplicates programmes,
and outputs a single merged epg.xml.
"""

import gzip
import io
import logging
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Set, Tuple

from src.epg_manager import EPGSource, EPGDownloader, EPGCache
from src.playlist_generator import EPG_MAP


# All 4 sources as separate entries for maximum coverage
EPG_SOURCES = [
    EPGSource(name="IT_primary", url="https://iptv-epg.org/files/epg-it.xml.gz", priority=0),
    EPGSource(name="IT_backup", url="https://epgshare01.online/epgshare01/epg_ripper_IT1.xml.gz", priority=1),
    EPGSource(name="CH_primary", url="https://iptv-epg.org/files/epg-ch.xml.gz", priority=2),
    EPGSource(name="CH_backup", url="https://epgshare01.online/epgshare01/epg_ripper_CH1.xml.gz", priority=3),
]

# Channel IDs actually used in the playlist
PLAYLIST_CHANNEL_IDS = set(EPG_MAP.values())
# Also include RSI IDs as they appear in CH EPG sources (different from .it suffixes)
PLAYLIST_CHANNEL_IDS.update({"RSI.La.1.ch", "RSI.LA.2.ch", "RSI La 1.ch", "RSI La 2.ch"})


def _is_ch_source(name: str) -> bool:
    return name.startswith("CH_")


def _download_source(source: EPGSource, downloader: EPGDownloader, cache: EPGCache) -> Optional[bytes]:
    """Download and decompress a single EPG source with caching."""
    cached = cache.get_cached(source.name)
    if cached:
        logging.info(f"Using cached EPG for {source.name}")
        return cached

    gz_content = downloader.download(source)
    if gz_content is None:
        return None

    xml_content = downloader.decompress(gz_content, source.url)
    if xml_content:
        cache.save(source.name, xml_content)
    return xml_content


def merge_epg(output_path: str) -> bool:
    """Merge all EPG sources into a single XMLTV file.
    
    Only includes channels whose IDs appear in the playlist's EPG_MAP.
    
    Returns True if at least one source was merged successfully.
    """
    downloader = EPGDownloader()
    cache = EPGCache()

    merged_channels: Dict[str, ET.Element] = {}
    merged_programmes: Dict[Tuple[str, str], ET.Element] = {}

    sources_loaded = 0

    logging.info(f"Filtering EPG to {len(PLAYLIST_CHANNEL_IDS)} channel IDs from playlist")

    for source in EPG_SOURCES:
        logging.info(f"Processing EPG source: {source.name}...")
        xml_content = _download_source(source, downloader, cache)
        if xml_content is None:
            logging.warning(f"Skipping {source.name} — download failed")
            continue

        try:
            tree = ET.parse(io.BytesIO(xml_content))
            root = tree.getroot()
        except ET.ParseError as e:
            logging.error(f"Failed to parse {source.name}: {e}")
            continue

        source_channels = 0
        source_programmes = 0

        # Process channels — only keep those in our playlist
        for ch_elem in root.findall("channel"):
            ch_id = ch_elem.get("id")
            if not ch_id:
                continue

            # Only keep channels that are in our playlist's EPG_MAP
            if ch_id not in PLAYLIST_CHANNEL_IDS:
                continue

            if ch_id not in merged_channels:
                merged_channels[ch_id] = ch_elem
                source_channels += 1

        # Process programmes — only keep those for our playlist channels
        for prog_elem in root.findall("programme"):
            ch_id = prog_elem.get("channel", "")
            start = prog_elem.get("start", "")

            if not ch_id or not start:
                continue

            if ch_id not in PLAYLIST_CHANNEL_IDS:
                continue

            # Deduplicate by (channel_id, start)
            key = (ch_id, start)
            if key not in merged_programmes:
                merged_programmes[key] = prog_elem
                source_programmes += 1

        sources_loaded += 1
        logging.info(f"  {source.name}: +{source_channels} channels, +{source_programmes} programmes")

    if sources_loaded == 0:
        logging.error("No EPG sources loaded!")
        return False

    # Build output XMLTV
    logging.info(f"Building merged EPG: {len(merged_channels)} channels, {len(merged_programmes)} programmes...")
    
    out_root = ET.Element("tv")
    out_root.set("generator-info-name", "vavoo-epg-merger")

    for ch_id in sorted(merged_channels.keys()):
        out_root.append(merged_channels[ch_id])

    for key in sorted(merged_programmes.keys()):
        out_root.append(merged_programmes[key])

    tree = ET.ElementTree(out_root)
    ET.indent(tree, space="  ")
    
    with open(output_path, "wb") as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(b'<!DOCTYPE tv SYSTEM "xmltv.dtd">\n')
        tree.write(f, encoding="utf-8", xml_declaration=False)

    import os
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    logging.info(f"Merged EPG written to {output_path} ({size_mb:.1f} MB)")
    return True


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    merge_epg("epg.xml")
