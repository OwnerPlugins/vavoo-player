#!/usr/bin/env python3
import gzip
import requests
import xml.etree.ElementTree as ET
from io import BytesIO


def download_and_parse(url):
    """Download gzipped XML, decompress and parse."""
    print(f"Downloading {url}")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    with gzip.open(BytesIO(resp.content), 'rt', encoding='utf-8') as f:
        return ET.parse(f)


def merge_xml_files(urls, output):
    """Merge multiple XMLTV files into one."""
    tv = ET.Element('tv')
    channels = []
    programmes = []

    for url in urls:
        tree = download_and_parse(url)
        root = tree.getroot()
        channels.extend(root.findall('channel'))
        programmes.extend(root.findall('programme'))

    for ch in channels:
        tv.append(ch)
    for prog in programmes:
        tv.append(prog)

    tree_out = ET.ElementTree(tv)
    tree_out.write(output, encoding='utf-8', xml_declaration=True)
    print(f"Saved merged EPG to {output}")


if __name__ == '__main__':
    urls = [
        "https://epgshare01.online/epgshare01/epg_ripper_BA1.xml.gz",
        "https://epgshare01.online/epgshare01/epg_ripper_HR1.xml.gz",
        "https://epgshare01.online/epgshare01/epg_ripper_RS1.xml.gz"
    ]
    merge_xml_files(urls, 'epg_bk.xml')
