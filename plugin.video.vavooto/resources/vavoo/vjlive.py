# -*- coding: utf-8 -*-
from vavoo.utils import *

chanicons = ['13thstreet.png', '3sat.png', 'animalplanet.png', 'anixe.png', 'ard.png', 'ardalpha.png', 'arte.png', 'atv.png', 'atv2.png', 'automotorsport.png', 'axnblack.png', 'axnwhite.png', 'br.png', 'cartoonito.png', 'cartoonnetwork.png', 'comedycentral.png', 'curiositychannel.png', 'fix&foxi.png', 'dazn1.png', 'dazn2.png', 'deluxemusic.png', 'nationalgeographic.png', 'dmax.png', 'eurosport1.png', 'eurosport2.png', 'nickjunior.png', 'superrtl.png', 'heimatkanal.png', 'history.png', 'hr.png', 'jukebox.png', 'kabel1doku.png', 'pro7.png', 'pro7maxx.png', 'pro7fun.png', 'rtl2.png', 'kika.png', 'kinowelt.png', 'mdr.png', 'universaltv.png', 'discovery.png', 'mtv.png', 'n24doku.png', 'natgeowild.png', 'sky1.png', 'ndr.png', 'nickelodeon.png', 'nitro.png', 'romancetv.png', 'ntv.png', 'one.png', 'orf1.png', 'orf2.png', 'orf3.png', 'orfsportplus.png', 'phoenix.png', 'geotv.png', 'puls24.png', 'puls4.png', 'rbb.png', 'ric.png', 'motorvision.png', 'rtl.png', 'rtlcrime.png', 'rtlliving.png', 'kabel1.png', 'rtlpassion.png', 'rtlup.png', 'sat1.png', 'sat1emotions.png', 'sat1gold.png', 'servustv.png', 'silverline.png', 'sixx.png', 'skyatlantic.png', 'skycinemaaction.png', 'skycinemaclassics.png', 'skycinemafamily.png', 'skycinemahighlights.png', 'skycinemapremieren.png', 'skycrime.png', 'skydocumentaries.png', 'skykrimi.png', 'skynature.png', 'skyreplay.png', 'skyshowcase.png', 'spiegelgeschichte.png', 'kabel1classics.png', 'sport1.png', 'sportdigital.png', 'swr.png', 'syfy.png', 'tagesschau24.png', 'tele5.png', 'tlc.png', 'toggoplus.png', 'crime+investigation.png', 'vox.png', 'voxup.png', 'warnertvcomedy.png', 'warnertvfilm.png', 'warnertvserie.png', 'wdr.png', 'welt.png', 'weltderwunder.png', 'zdf.png', 'zdfinfo.png', 'zdfneo.png', 'zeeone.png', 'skycinemathriller.png']

def resolve_link(link):
	if not "vavoo" in link:
		from vavoo.stalker import StalkerPortal
		try:
			link, headers = StalkerPortal(get_cache_or_setting("stalkerurl"), get_cache_or_setting("mac")).get_tv_stream_url(link)
			status = int(request("GET", link, headers=headers, timeout=10, stream=True, retries=0).status_code)
			log(f"function resolve_link Staus :{status}")
			if status < 400: 
				return link, "&".join([f"{k}={v}" for k, v in headers.items()])
		except Exception:
			log(format_exc())
		else:
			return None, None
	else:
		_headers = {"user-agent": "MediaHubMX/2", "accept": "application/json", "content-type": "application/json; charset=utf-8", "content-length": "115", "accept-encoding": "gzip", "mediahubmx-signature": getAuthSignature()}
		_data = {"language": "de", "region": "AT", "url": link, "clientVersion": "3.0.2"}
		url = "https://vavoo.to/mediahubmx-resolve.json"
		streamurl = request_json("POST", url, json=_data, headers=_headers, timeout=10, retries=1)[0]["url"]
		status = int(request("GET", streamurl, timeout=10, stream=True, retries=0).status_code)
		log(f"function resolve_link Staus :{status}")
		if status < 400: return streamurl, None
		return None, None

def get_stalker_channels(genres=False):
	if genres == False: cacheOk, genres = get_cache("stalker_groups")
	from vavoo.stalker import StalkerPortal, get_genres, new_mac
	if not genres: genres = get_genres()
	cacheOk, chan = get_cache("sta_channels")
	if not cacheOk:
		url, mac = get_cache_or_setting("stalkerurl"), get_cache_or_setting("mac")
		if not url or not mac:
			dialog.notification('VAVOO.TO', 'Kein Stalkerportal gewählt, deaktiviere Stalker', xbmcgui.NOTIFICATION_ERROR, 2000)
			setSetting("stalker", "false")
			return {}
		portal = StalkerPortal(url, mac)
		check = portal.check()
		if check == True: cacheOk, chan = get_cache("sta_channels")
		elif check == "IP BLOCKED":
			dialog.notification('VAVOO.TO', 'IP BLOCKED anderes Portal auswählen, deaktiviere Stalker', xbmcgui.NOTIFICATION_ERROR, 2000)
			setSetting("stalker", "false")
			return {}
		else:
			m = new_mac(True)
			if m == False:
				dialog.notification('VAVOO.TO', 'Keine funktionierende Mac gefunden, anderes Portal auswählen, deaktiviere Stalker', xbmcgui.NOTIFICATION_ERROR, 2000)
				setSetting("stalker", "false")
				return {}
		cacheOk, chan = get_cache("sta_channels")
		if not cacheOk: return {}
	sta_channels = {}
	for item in chan:
		if item["tv_genre_id"] not in genres: continue
		name = item["name"].upper()
		if any(ele in name for ele in ["***", "###", "---"]): continue
		name = filterout(name)
		if not name: continue
		if name not in sta_channels: sta_channels[name] = []
		if item["cmd"] not in sta_channels[name]:
			sta_channels[name].append(item["cmd"])
	return sta_channels

def getchannels(type=None, group=None):
	if getSetting("stalker") == "true" and not type == "vavoo":
		allchannels = get_stalker_channels() if type == None else get_stalker_channels([group])
	else: allchannels = {}
	if getSetting("vavoo") == "true" and not type == "stalker":
		from vavoo.vavoo_tv import get_vav_channels
		vav_channels = get_vav_channels() if type == None else get_vav_channels([group])
	else: vav_channels = {}
	for k, v in vav_channels.items():
		if k not in allchannels: allchannels[k] = []
		for n in v: allchannels[k].append(n)
	return allchannels

def get_channel_logo(name):
	img = "%s.png" % name.replace(" ", "").lower()
	if img in chanicons:
		return "https://michaz1988.github.io/logos/%s" % img
	return ""

def getchannels_meta(type=None, group=None):
	channels = {}
	if getSetting("vavoo") == "true" and not type == "stalker":
		cacheOk, vav_data = get_cache("vav_channels")
		if not cacheOk or not isinstance(vav_data, dict):
			from vavoo.vavoo_tv import get_vav_channels
			get_vav_channels()
			cacheOk, vav_data = get_cache("vav_channels")
		if cacheOk and isinstance(vav_data, dict):
			for item in vav_data.get("channels", []):
				name = filterout(item["name"])
				if group and item["group"] != group:
					continue
				if name not in channels:
					channels[name] = {"name": name, "group": item["group"], "urls": [], "logo": get_channel_logo(name)}
				if item["url"] not in channels[name]["urls"]:
					channels[name]["urls"].append(item["url"])
	if getSetting("stalker") == "true" and not type == "vavoo":
		cacheOk2, sta_chans = get_cache("sta_channels")
		if cacheOk2:
			for item in sta_chans:
				name = filterout(item["name"].upper())
				if not name or any(ele in name for ele in ["***", "###", "---"]):
					continue
				if name not in channels:
					channels[name] = {"name": name, "group": "Stalker", "urls": [], "logo": get_channel_logo(name)}
				if item["cmd"] not in channels[name]["urls"]:
					channels[name]["urls"].append(item["cmd"])
	return list(channels.values())

def handle_wait(kanal):
	create = progress.create("Abbrechen zur manuellen Auswahl", "STARTE  : %s" % kanal)
	time_to_wait = int(getSetting("count")) + 1
	for secs in range(1, time_to_wait):
		secs_left = time_to_wait - secs
		progress.update(int(secs / time_to_wait * 100), "STARTE  : %s\nStarte Stream in  : %s" % (kanal, secs_left))
		monitor.waitForAbort(1)
		if (progress.iscanceled()):
			progress.close()
			return False
	progress.close()
	return True

def livePlay(name, type=None, group=None):
	m = getchannels(type, group).get(name)
	if not m:
		showFailedNotification()
		return
	i, title = 0, None
	if len(m) > 1:
		if getSetting("auto") == "0":
			cacheOk, last = get_cache("last")
			if cacheOk and last.get("idn") == name: i = last.get("num") + 1
			if i >= len(m): i = 0
			title = "%s (%s/%s)" % (name, i + 1, len(m))  # wird verwendet für infoLabels
		elif getSetting("auto") == "1":
			if not handle_wait(name):  # Dialog aufrufen
				cap = []
				for i, n in enumerate(m, 1): cap.append("STREAM %s" % i)
				i = selectDialog(cap)
				if i < 0: return
			title = "%s (%s/%s)" % (name, i + 1, len(m))  # wird verwendet für infoLabels
		else:
			cap = []
			for i, n in enumerate(m, 1): cap.append("STREAM %s" % i)
			i = selectDialog(cap)
			if i < 0: return
			title = "%s (%s/%s)" % (name, i + 1, len(m))  # wird verwendet für infoLabels
	k = 0
	while True:
		k += 1
		if k > len(m): return
		url, headers = resolve_link(m[i])
		if url: break
		else:
			i += 1
			if i >= len(m): i = 0
	set_cache("last", {"idn": name, "num": i}, 2)
	title = title if title else name
	infoLabels = {"title": title, "plot": "[B]%s[/B] - Stream %s von %s" % (name, i + 1, len(m))}
	o = ListItem(name)
	log("Spiele %s" % url)
	if "hls" in url or "m3u8" in url: inputstream = "inputstream.ffmpegdirect" if getSetting("hlsinputstream") == "0" else "inputstream.adaptive"
	else: inputstream = "inputstream.ffmpegdirect"
	o.setProperty("inputstream", inputstream)
	if inputstream == "inputstream.ffmpegdirect":
		o.setProperty("inputstream.ffmpegdirect.is_realtime_stream", "true")
		o.setProperty("inputstream.ffmpegdirect.stream_mode", "timeshift")
		if getSetting("openmode") != "0": o.setProperty("inputstream.ffmpegdirect.open_mode", "ffmpeg" if getSetting("openmode") == "1" else "curl")
		if "hls" in url or "m3u8" in url: o.setProperty("inputstream.ffmpegdirect.manifest_type", "hls")
	if headers:
		if inputstream == "inputstream.adaptive":
			o.setProperty(f'{inputstream}.common_headers', headers)
			o.setProperty(f'{inputstream}.stream_headers', headers)
		else: url += f"|{headers}"
	o.setPath(url)
	o.setProperty("IsPlayable", "true")
	info_tag = ListItemInfoTag(o, 'video')
	info_tag.set_info(infoLabels)
	set_resolved(o)
	end()

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

def fetch_vavoo_direct_urls(sig, groups=None):
	if not sig: return []
	if not groups:
		cacheOk, g = get_cache("groups")
		groups = g if cacheOk else ["Germany", "Italy"]
	channels = []
	_headers = {"user-agent": "okhttp/4.11.0", "accept": "application/json", "content-type": "application/json; charset=utf-8", "accept-encoding": "gzip", "mediahubmx-signature": sig}
	for group in groups:
		cursor = 0
		while cursor is not None:
			try:
				_data = {"language": "de", "region": "AT", "catalogId": "iptv", "id": "iptv", "adult": False, "search": "", "sort": "name", "filter": {"group": group}, "cursor": cursor, "clientVersion": "3.0.2"}
				req = request_json("POST", "https://vavoo.to/mediahubmx-catalog.json", json=_data, headers=_headers, timeout=10, retries=1)
				for item in req.get("items", []):
					channels.append({"name": item["name"], "url": item["url"], "group": item.get("group", group), "logo": item.get("logo", "")})
				cursor = req.get("nextCursor")
			except Exception:
				log(format_exc())
				break
	return channels

def makem3u():
	progress.create("VAVOO.TO", "Generazione playlist M3U per mpv/VLC...")
	progress.update(5, "Ottenimento auth signature...")
	sig = getAuthSignature()
	if not sig:
		progress.close()
		dialog.ok('VAVOO.TO', 'Errore: impossibile ottenere auth signature')
		return
	progress.update(15, "Recupero canali da VAVOO...")
	direct_channels = fetch_vavoo_direct_urls(sig)
	progress.update(70, "Elaborazione canali...")
	user_agent = "okhttp/4.11.0"
	seen = set()
	processed = []
	for ch in direct_channels:
		name = normalize_italian_name(ch["name"])
		if not name: continue
		if any(bl in name for bl in ITALIAN_BLACKLIST): continue
		key = (name, ch["url"])
		if key in seen: continue
		seen.add(key)
		priority = get_channel_priority(name)
		logo = ch.get("logo", "") or get_channel_logo(name)
		group = ch.get("group", "VAVOO")
		chno = priority if priority < 9999 else 0
		processed.append({
			"name": name, "url": ch["url"], "group": group,
			"logo": logo, "priority": priority, "chno": chno
		})
	processed.sort(key=lambda x: (x["priority"], x["name"]))
	m3u_lines = ['#EXTM3U x-tvg-url="https://raw.githubusercontent.com/mich-de/vavoo-player/master/epg.xml"\n']
	for idx, ch in enumerate(processed, 1):
		url_encoded = quote(ch["name"].encode("utf-8"))
		chno = ch["chno"] if ch["chno"] > 0 else idx
		m3u_lines.append("#EXTVLCOPT:http-user-agent=%s\n" % user_agent)
		extinf = '#EXTINF:-1 tvg-id="%s" tvg-name="%s" tvg-chno="%s" tvg-logo="%s" group-title="%s",%s\n' % (
			url_encoded, url_encoded, chno, ch["logo"], ch["group"], ch["name"]
		)
		m3u_lines.append(extinf)
		m3u_lines.append(ch["url"] + "\n")
	progress.update(90, "Scrittura file M3U...")
	m3uPath = os.path.join(addonprofile, "vavoo.m3u")
	with open(m3uPath, "w", encoding="utf-8") as a:
		a.writelines(m3u_lines)
	progress.update(100, "Playlist pronta: %d canali" % len(processed))
	time.sleep(1)
	progress.close()
	yes = dialog.yesno('VAVOO.TO', 'm3u erstellt in %s\n%d canali\n\nAprire con mpv?' % (m3uPath, len(processed)))
	if yes:
		import subprocess
		try:
			subprocess.Popen(["mpv", "--playlist", m3uPath])
		except FileNotFoundError:
			dialog.ok('VAVOO.TO', 'mpv non trovato.\nInstallalo da https://mpv.io/installation/')
		except Exception as e:
			dialog.ok('VAVOO.TO', 'Errore: %s' % str(e))

# edit kasi
def channels(items=None, type=None, group=None):
	try: lines = json.loads(getSetting("favs"))
	except (TypeError, ValueError):
		lines = []
	results = json.loads(items) if items else getchannels(type, group)
	for name in results:
		index = len(results[name])
		title = name if getSetting("stream_count") == "false" or index == 1 else "%s  (%s)" % (name, index)
		o = ListItem(name)
		img = "%s.png" % name.replace(" ", "").lower()
		iconimage = "DefaultTVShows.png"
		if img in chanicons: iconimage = "https://michaz1988.github.io/logos/%s" % img
		o.setArt({"icon": iconimage, "thumb": iconimage, "poster": iconimage})
		cm = []
		if not name in lines:
			cm.append(("zu TV Favoriten hinzufügen", "RunPlugin(%s?action=addTvFavorit&name=%s)" % (sys.argv[0], name.replace("&", "%26").replace("+", "%2b"))))
			plot = ""
		else:
			plot = "[COLOR gold]TV Favorit[/COLOR]"
			cm.append(("von TV Favoriten entfernen", "RunPlugin(%s?action=delTvFavorit&name=%s)" % (sys.argv[0], name.replace("&", "%26").replace("+", "%2b"))))
		cm.append(("Einstellungen", "RunPlugin(%s?action=settings)" % sys.argv[0]))
		cm.append(("m3u erstellen", "RunPlugin(%s?action=makem3u)" % sys.argv[0]))
		o.addContextMenuItems(cm)
		infoLabels = {"title": title, "plot": plot}
		info_tag = ListItemInfoTag(o, 'video')
		info_tag.set_info(infoLabels)
		o.setProperty("IsPlayable", "true")
		param = {"name": name, "type": type, "group": group} if type else {"name": name}
		add(param, o)
	sort_method()
	end()

def favchannels():
	try: lines = json.loads(getSetting("favs"))
	except (TypeError, ValueError):
		return
	for name in getchannels():
		if not name in lines: continue
		o = ListItem(name)
		img = "%s.png" % name.replace(" ", "").lower()
		iconimage = "DefaultTVShows.png"
		if img in chanicons: iconimage = "https://michaz1988.github.io/logos/%s" % img
		o.setArt({"icon": iconimage, "thumb": iconimage, "poster": iconimage})
		cm = []
		cm.append(("von TV Favoriten entfernen", "RunPlugin(%s?action=delTvFavorit&name=%s)" % (sys.argv[0], name.replace("&", "%26").replace("+", "%2b"))))
		cm.append(("Einstellungen", "RunPlugin(%s?action=settings)" % sys.argv[0]))
		o.addContextMenuItems(cm)
		infoLabels = {"title": name, "plot": "[COLOR gold]Liste der eigene Live Favoriten[/COLOR]"}
		info_tag = ListItemInfoTag(o, 'video')
		info_tag.set_info(infoLabels)
		o.setProperty("IsPlayable", "true")
		add({"name": name}, o)
	sort_method()
	end()

def change_favorit(name, delete=False):
	try:lines = json.loads(getSetting("favs"))
	except (TypeError, ValueError):
		lines = []
	if delete:
		if name in lines:
			lines.remove(name)
	else:
		if name not in lines:
			lines.append(name)
	setSetting("favs", json.dumps(lines))
	if len(lines) == 0: execute("Action(ParentDir)")
	else: execute("Container.Refresh")
