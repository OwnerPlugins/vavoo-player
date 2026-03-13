import requests
import json
import time
import os
import sys
import logging
import logging
import urllib3
# Add parent dir to sys.path to resolve data_manager if needed
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from src.data_manager import DataManager

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONSTANTS ---
USER_AGENT = "okhttp/4.11.0"
API_BASE = "https://www.vavoo.tv/api"
VAOO_URL = "https://vavoo.to/mediahubmx-catalog.json"

GROUPS = [
    "Italy"
]


TIVUSAT_ORDER = {
    "RAI 1": 1, "RAI 2": 2, "RAI 3": 3, "RETE 4": 4, "CANALE 5": 5, "ITALIA 1": 6, "LA7": 7, "TV8": 8, "NOVE": 9,
    "RAI 4": 10, "IRIS": 11, "LA5": 12, "RAI 5": 13, "RAI MOVIE": 14, "RAI PREMIUM": 15,
    "MEDIASET EXTRA": 17, "TV2000": 18, "CIELO": 19, "20 MEDIASET": 20, "RAI SPORT": 21,
    "RAI STORIA": 23, "RAI NEWS 24": 24, "TGCOM24": 25, "DMAX": 26, "REAL TIME": 31,
    "CINE34": 34, "FOCUS": 35, "RTL 102.5": 36, "WARNER TV": 37, "GIALLO": 38, "TOP CRIME": 39,
    "BOING": 40, "K2": 41, "RAI GULP": 42, "RAI YOYO": 43, "FRISBEE": 44, "CARTOONITO": 46, "SUPER!": 47,
    "SPIKE": 49, "SKY TG24": 50, "ITALIA 2": 66, "RADIO ITALIA TV": 70,
    "RSI LA 1": 71, "RSI LA 2": 72
}

BOUQUETS = {
    "TV Sat": ["RAI 1", "RAI 2", "RAI 3", "RETE 4", "CANALE 5", "ITALIA 1", "LA7", "TV8", "NOVE", "20 MEDIASET", "20 HD",
               "RAI 4", "IRIS", "LA5", "RAI 5", "RAI MOVIE", "RAI PREMIUM", "MEDIASET EXTRA",
               "RAI GULP", "RAI YOYO", "RAI STORIA", "RAI SCUOLA", "RAI NEWS", "RAI SPORT",
               "TV2000", "CIELO", "DMAX", "REAL TIME", "QVC", "RTL 102.5 TV",
               "BOING", "K2", "FRISBEE", "CARTOONITO", "SUPER!", "SPIKE", "PARAMOUNT",
               "CINE34", "FOCUS", "TOP CRIME", "GIALLO", "WARNER TV", "TGCOM24", "SKY TG24",
               "ITALIA 2", "MOTOR TREND", "RAI 4K", "RSI LA 1", "RSI LA 2", "TWENTYSEVEN", "27 TWENTYSEVEN",
               "RAI ITALIA", "FOOD NETWORK", "HGTV", "SENATO TV", "CAMERA DEI DEPUTATI", "ALMA TV", "LA 7D", "LA7D", "CUSANO"],
    "Intrattenimento": ["SKY UNO", "SKY ARTE", "SKY SERIE", "SKY ATLANTIC", "COMEDY CENTRAL", "PREMIUM ACTION", "PREMIUM CRIME", "PREMIUM STORIES", "FOX", "BLAZE", "GIALLO", "LAEFFE", "TV2000", "NOVE", "REAL TIME", "DMAX", "MEDIASET EXTRA", "DONNATV", "FASHION TV", "CANALE 5", "ITALIA 1", "RETE 4", "LA7"],
    "Cinema": ["SKY CINEMA", "PREMIUM CINEMA", "CINE34", "RAI MOVIE", "PARAMOUNT", "IRIS", "LA5", "TWENTYSEVEN", "27 TWENTYSEVEN",
               "RAI PREMIUM", "SKYSHOWTIME", "DISNEY FILM", "STUDIO UNIVERSAL"],
    "Sport": ["SKY SPORT", "DAZN", "EUROSPORT", "TENNIS", "MOTOGP", "F1", "CALCIO", "ACISPORT", "LIVECAMP", "ELEVEN", "DIRT", "GOLF", 
              "INTER TV", "MILAN TV", "JUVE", "SPORTITALIA", "SPORT ITALIA", "SUPER TENNIS", "SUPERTENNIS",
              "ACI SPORT", "BIKE", "MOTOR TREND", "NBA", "NFL", "WWE", "FIGHT", "UFC", "EQUTV", "HORSE TV", "CACCIA", "PESCA"],
    "Kids": ["BOING", "K2", "FRISBEE", "CARTOONITO", "SUPER!", "RAI GULP", "RAI YOYO", "DEAKIDS", "DEA JUNIOR",
             "BOOMERANG", "CARTOON NETWORK", "NICK JR", "NICKELODEON", "NICK", "BABY TV",
             "IUNIOR TV", "DISNEY", "JIMJAM", "TEEN NICK"],
    "Documentary": ["SKY DOCUMENTARIES", "SKY NATURE", "GEO", "DISCOVERY", "HISTORY",
                     "NATIONAL GEOGRAPHIC", "NAT GEO", "CRIME INVESTIGATION", "CRIME+ INV", 
                     "ANIMAL PLANET", "PESCA", "CACCIA", "MARCOPOLO", "FOCUS", "SCIENCE", "EXPLORER HD", "BLAZE"],
    "Music": ["VH1", "MTV", "RADIO ITALIA", "RTL 102.5", "RADIO CAPITAL", "RADIO FRECCIA", "RDS", 
              "RADIONORBA", "DEEJAY", "RADIO 105", "RADIO MONTE CARLO", "R101", "VIRGIN",
              "KISS KISS", "M2O", "CLASSICA", "RMC", "ZETA", "BATTITI"],
    "News": ["SKY TG24", "TGCOM24", "RAI NEWS", "EURONEWS", "BBC NEWS", "BBC WORLD", "CNN", "AL JAZEERA",
             "CNBC", "BLOOMBERG", "FRANCE 24", "I24NEWS", "CLASS-CNBC", "RUSSIA TODAY", "SKY NEWS", "FOX NEWS", "TG NORBA"],
    "Locali": ["ANTENNA SICILIA", "TELELOMBARDIA", "TOP CALCIO", "TELENORBA", "TELECAPRI", "CANALE 21", "VIDEOFUMETTO", "RTTR", "TVA", "VIDEOLINA", "TELEPACE", "TELETUTTO", "RETE 8", "PRIMOCANALE", "ER24", "ITALIA 7 GOLD"],
    "Primafila / PPV": ["PRIMAFILA", "SKY CALCIO", "SKY SPORT HD INFO", "PPV"]
}

# Mapping from Normalized Vavoo Name to EPG ID
# Based on common Italian XMLTV IDs
EPG_MAP = {
    "RAI 1": "Rai1.it",
    "RAI 2": "Rai2.it",
    "RAI 3": "Rai3.it",
    "RAI 4": "Rai4.it",
    "RAI 4K": "Rai4k.it",
    "RAI 5": "Rai5.it",
    "RAI MOVIE": "RaiMovie.it",
    "RAI PREMIUM": "RaiPremium.it",
    "RAI GULP": "RaiGulp.it",
    "RAI YOYO": "RaiYoyo.it",
    "RAI STORIA": "RaiStoria.it",
    "RAI SCUOLA": "RaiScuola.it",
    "RAI NEWS 24": "RaiNews.it",
    "RAI SPORT": "RAISport.it",
    "CANALE 5": "Canale5.it",
    "ITALIA 1": "Italia1.it",
    "ITALIA 2": "Italia2.it",
    "RETE 4": "Rete4.it",
    "LA7": "La7.it",
    "LA 7": "La7.it",
    "LA7D": "La7d.it",
    "TV8": "TV8.it",
    "TV 8": "TV8.it",
    "8": "TV8.it",
    "NOVE": "Nove.it",
    "DISCOVERY NOVE": "Nove.it",
    "20 MEDIASET": "Mediaset20.it",
    "CIELO": "cielo.it",
    "DMAX": "DMAX.it",
    "MOTOR TREND": "MotorTrend.it",
    "EUROSPORT 1": "Eurosport.it",
    "EUROSPORT 2": "Eurosport2.it",
    "BIKE": "BIKE.it",
    "REAL TIME": "Real.Time.it",
    "FOCUS": "Focus.it",
    "DISCOVERY FOCUS": "Focus.it",
    "FOOD NETWORK": "FoodNetwork.it",
    "HGTV": "HGTV.it",
    "LA7D": "La7D.it",
    "GIALLO": "Giallo.TV.it",
    "TOP CRIME": "TOPcrime.it",
    "BOING": "Boing.it",
    "BOING PLUS": "BoingPlus.it",
    "K2": "K2.it",
    "DISCOVERY K2": "K2.it",
    "FRISBEE": "-frisbee-.it",
    "CARTOONITO": "CARTOONITO.it",
    "SUPER!": "Super!.it",
    "IRIS": "Iris.it",
    "LA5": "La5.it",
    "CINE34": "Cine34.it",
    "MEDIASET EXTRA": "MediasetExtra.it",
    "TGCOM24": "TgCom24.it",
    "20": "Mediaset20.it",
    "ACI SPORT TV": "ACISportTv.it",
    "AL JAZEERA": "AlJazeera.it",
    "ALMA TV": "AlmaTV.it",
    "BABY TV": "BabyTV.it",
    "BBC WORLD NEWS": "BBCWorldNews.it",
    "BIKE": "Bike.it",
    "BLAZE": "Blaze.it",
    "BLOOMBERG": "Bloomberg.it",
    "BOOMERANG + 1": "Boomerang+1.it",
    "BOOMERANG": "Boomerang.it",
    "CACCIA E PESCA": "CacciaPesca.it",
    "CARTOON NETWORK": "CartoonNetwork.it",
    "CLASS-CNBC": "ClassCNBC.it",
    "CLASSICA HD": "Classica.it",
    "CN +1": "CN+1.it",
    "CNBC": "CNBC.it",
    "CNN INTL": "CNNIntl.it",
    "COMEDY +1": "Comedy+1.it",
    "COMEDY CENTRAL": "ComedyCentral.it",
    "CRIME+ INV.": "Crime+Inv..it",
    "DAZN": "DAZN.it",
    "DAZN 1": "DAZN.1.it.it",
    "DAZN 2": "DAZN.2.it.it",
    "DEA JUNIOR": "DeAJunior.it",
    "DEAKIDS": "DeAKids.it",
    "DEAKIDS+1": "DeAKids+1.it",
    "DEEJAY TV": "DeejayTV.it",
    "DISCOVERY CH +1": "Discovery+1.it",
    "DISCOVERY CHANNEL HD": "DiscoveryChannelHD.it",
    "DISCOVERY SCIENCE HD": "DiscoverySci.it",
    "DMAX HD": "DMAXHD.it",
    "DONNATV": "DonnaTv.it",
    "EQUTV": "Equtv.it",
    "ER24 - EMILIA ROMAGNA 24": "EmiliaRomagna24.it",
    "EURONEWS": "Euronews.it",
    "INTER TV": "InterTV.it",
    "MILAN TV": "MilanTV.it",
    "EUROSPORT 1": "Eurosport.1.it",
    "EUROSPORT 2HD": "Eurosport.2.it",
    "EUROSPORT HD": "Eurosport.1.it",
    "EUROSPORT 2": "Eurosport.2.it",
    "BLAZE": "Blaze.it",
    "DISNEY CHANNEL": "DisneyChannel.ch",
    "DISNEY JUNIOR": "DisneyJuniorf.ch",
    "FOX": "Fox.it",
    "FOX +1": "Fox+1.it",
    "FOX BUSINESS": "Fox.Business.it",
    "FOX NEWS": "Fox.News.it",
    "FRANCE 24 ENGLISH": "France24English.it",
    "FRANCE 24": "France24.it",
    "GAMBERO ROSSO HD": "GamberoRosso.it",
    "HGTV - HOMEANDGARDEN": "HGTV.it",
    "HISTORY": "History.it",
    "HISTORY 1": "History.it",
    "HISTORY HD": "History.it",
    "HISTORY C": "History.it",
    "HISTORY S": "History.it",
    "HISTORY CHANNEL S": "History.it",
    "HORSE TV HD": "HorseTV.it",
    "I24NEWS": "i24news.it",
    "IL61": "IL61.it",
    "INTER TV HD": "InterTV.it",
    "ITALIA 7 GOLD": "Italia7Gold.it",
    "LA 1": "RSILA1.it",
    "LA 2": "RSILA2.it",
    "LAZIO STYLE CHANNEL": "LazioStyleCh.it",
    "MARCOPOLO TRAVEL TV": "MarcopoloTravelTV.it",
    "MILAN TV": "MilanTV.it",
    "MOTOR TREND": "MotorTrend.it",
    "MTV MUSIC": "MTVMusic.it",
    "MTV": "MTV.it",
    "NAT GEO WILD +1": "NatGeoWild+1.it",
    "NATIONAL GEOGRAPHIC": "NationalGeo.it",
    "NATIONAL GEOGRAPHIC WILD": "NatGeoWild.it",
    "NATIONAL GEOGRAPHIC +1": "NationalGeo+1.it",
    "NHK WORLD TV": "NHKWorldTV.it",
    "NICK JR+1": "NickJr+1.it",
    "NICK JUNIOR": "NickJr.it",
    "NICKELODEON + 1": "Nickelodeon+1.it",
    "NICKELODEON": "Nickelodeon.it",
    "PESCA E CACCIA": "PescaCaccia.it",
    "PREMIUM ACTION": "PremiumAction.it",
    "PREMIUM CINEMA 1": "PremiumCinema1.it",
    "PREMIUM CINEMA 2": "PremiumCinema2.it",
    "PREMIUM CINEMA 3": "PremiumCinema3.it",
    "PREMIUM CRIME": "PremiumCrime.it",
    "PREMIUM STORIES": "PremiumStories.it",
    "PRIMAFILA 1": "Primafila1.it",
    "PRIMAFILA 2": "Primafila2.it",
    "PRIMAFILA 3": "Primafila3.it",
    "PRIMAFILA 4": "Primafila4.it",
    "PRIMAFILA 5": "Primafila5.it",
    "QVC": "QVC.it",
    "R101": "R101.it",
    "RADIO 105": "Radio105.it",
    "RADIO FRECCIA": "RADIOFRECCIA.it",
    "RADIO ITALIA TV": "RadioItaliaTV.it",
    "RADIO MONTE CARLO": "RadioMonteCarlo.it",
    "RADIONORBA TV": "RADIONORBATV.it",
    "RT DOC HD": "RTDoc.it",
    "RTL 102.5 TV": "RTL1025.it",
    "RTL 102.5": "RTL1025.it",
    "RUSSIA TODAY": "RussiaToday.it",
    "SKY ADVENTURE": "SkyAdventure.it",
    "SKY ARTE +1": "SkyArte+1.it",
    "SKY ARTE": "SkyArte.it",
    "SKY ARTE HD-400": "SkyArteHD-400.it",
    "SKY ATLANTIC +1": "SkyAtlantic+1.it",
    "SKY ATLANTIC": "SkyAtlantic.it",
    "SKY CINEMA ACTION": "SkyCinemaAction.it",
    "SKY CINEMA COLLECTION": "SkyCinemaCollection.it",
    "SKY CINEMA COMEDY": "SkyCinemaComedy.it",
    "SKY CINEMA DRAMA": "SkyCinemaDrama.it",
    "SKY CINEMA DUE +24": "SkyCinemaDue+24.it",
    "SKY CINEMA DUE": "SkyCinemaDue.it",
    "SKY CINEMA FAMILY": "SkyCinemaFamily.it",
    "SKY CINEMA ROMANCE": "SkyCinemaRomance.it",
    "SKY CINEMA SUSPENSE": "SkyCinemaSuspense.it",
    "SKY CINEMA UNO +24": "SkyCinemaUno+24.it",
    "SKY CINEMA UNO": "SkyCinemaUno.it",
    "SKY CRIME": "SkyCrime.it",
    "SKY DOCUMENTARIES +1": "SkyDocumentaries+1.it",
    "SKY DOCUMENTARIES": "SkyDocumentaries.it",
    "SKY INVESTIGATION +1": "SkyInvestigation+1.it",
    "SKY INVESTIGATION": "SkyInvestigation.it",
    "SKY METEO24": "SkyMeteo24.it",
    "SKY NATURE": "SkyNature.it",
    "SKY NEWS": "SkyNews.it",
    "SKY SERIE +1": "SkySerie+1.it",
    "SKY SERIE": "SkySerie.it",
    "SKY SPORT 251": "SkySport251.it",
    "SKY SPORT 252": "SkySport252.it",
    "SKY SPORT 253": "SkySport253.it",
    "SKY SPORT 254": "SkySport254.it",
    "SKY SPORT 255": "SkySport255.it",
    "SKY SPORT 256": "SkySport256.it",
    "SKY SPORT 257": "SkySport257.it",
    "SKY SPORT 258": "SkySport258.it",
    "SKY SPORT 259": "SkySport259.it",
    "SKY SPORT 260": "SkySport260.it",
    "SKY SPORT 261": "SkySport261.it",
    "SKY SPORT 4K": "SkySport4K.it",
    "SKY SPORT ACTION": "SkySportAction.it",
    "SKY SPORT ARENA": "SkySportArena.it",
    "SKY SPORT CALCIO": "SkySportCalcio.it",
    "SKY SPORT F1": "SkySportF1.it",
    "SKY SPORT GOLF": "SkySportGolf.it",
    "SKY SPORT MOTOGP": "SkySportMotoGP.it",
    "SKY SPORT MOTO GP": "SkySportMotoGP.it",
    "SKY SPORT NBA": "SkySportNBA.it",
    "SKY SPORT TENNIS": "SkySportTennis.it",
    "SKY SPORT UNO": "SkySportUno.it",
    "SKY SPORT24": "SkySport24.it",
    "SKY SPORT 24": "SkySport24.it",
    "SKY TG24": "SkyTG24.it",
    "SKY UNO +1": "SkyUno+.it",
    "SKY UNO": "SkyUno.it",
    "SMTV SAN MARINO": "SanMarinoRTV.it",
    "SPORTITALIA": "Sportitalia.it",
    "SUPER TENNIS": "SuperTennis.it",
    "SUPERTENNIS HD": "SuperTennisHD.it",
    "SUPERTENNIS": "SuperTennis.it",
    "TWENTYSEVEN": "Mediaset27Twentyseven.it",
    "DISCOVERY CHANNEL": "DiscoveryChannel.it",
    "DISCOVERY SCIENCE": "DiscoveryScience.it",
    "NAT GEO WILD": "NatGeoWild.it",
    "NATIONAL GEOGRAPHIC": "NationalGeographic.it",
    "MTV HITS": "MTVHits.it",
    "MTV MUSIC": "MTVMusic.it",
    "SKY SPORT MAX": "SkySportMax.it",
    "TELECAMPIONE": "Telecampione.it",
    "TG NORBA24": "TGNORBA24.it",
    "TOP CALCIO 24": "TopCalcio24.it",
    "TRM H24": "TRMh24.it",
    "TV2000": "TV2000.it",
    "RSI LA 1": "RSILA1.it",
    "RSI LA 2": "RSILA2.it",
}

class PlaylistGenerator:
    """
    Handles fetching channels from Vavoo API and generating M3U8 playlists.
    """
    def __init__(self):
        self._auth_cache = {
            "sig": None,
            "timestamp": 0
        }
        self.dm = DataManager()

    def _get_auth_signature(self):
        """Performs handshake to get the addon signature."""
        url = f"{API_BASE}/app/ping"
        headers = {
            "user-agent": USER_AGENT,
            "accept": "application/json",
            "content-type": "application/json; charset=utf-8",
            "accept-encoding": "gzip"
        }
        
        data = {
            "token": "tosFwQCJMS8qrW_AjLoHPQ41646J5dRNha6ZWHnijoYQQQoADQoXYSo7ki7O5-CsgN4CH0uRk6EEoJ0728ar9scCRQW3ZkbfrPfeCXW2VgopSW2FWDqPOoVYIuVPAOnXCZ5g",
            "reason": "app-blur",
            "locale": "de",
            "theme": "dark",
            "metadata": {
                "device": {"type": "Handset", "brand": "google", "model": "Nexus", "name": "21081111RG", "uniqueId": "d10e5d99ab665233"},
                "os": {"name": "android", "version": "7.1.2", "abis": ["arm64-v8a", "armeabi-v7a", "armeabi"], "host": "android"},
                "app": {"platform": "android", "version": "3.1.20", "buildId": "289515000", "engine": "hbc85", "signatures": ["6e8a975e3cbf07d5de823a760d4c2547f86c1403105020adee5de67ac510999e"], "installer": "app.revanced.manager.flutter"},
                "version": {"package": "tv.vavoo.app", "binary": "3.1.20", "js": "3.1.20"}
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
            "iap": {"supported": False}
        }

        try:
            logging.info("Requesting authentication signature...")
            # Disable SSL verification
            response = requests.post(url, json=data, headers=headers, timeout=10, verify=False)
            response.raise_for_status()
            sig = response.json().get("addonSig")
            if sig:
                self._auth_cache["sig"] = sig
                self._auth_cache["timestamp"] = time.time()
                logging.info("Signature received successfully.")
            return sig
        except Exception as e:
            logging.error(f"Error getting auth signature: {e}")
            return None

    def get_signature(self, max_age_seconds=600):
        """Returns a valid signature, refreshing if expired."""
        if self._auth_cache["sig"] and (time.time() - self._auth_cache["timestamp"] < max_age_seconds):
            return self._auth_cache["sig"]
        return self._get_auth_signature()

    def fetch_all_channels(self, target_groups=None):
        """
        Fetches channels from the API.
        
        Args:
            target_groups (list): List of groups to fetch. If None, uses default GROUPS.
            
        Returns:
            list: List of channel dictionaries.
        """
        if target_groups is None:
            target_groups = GROUPS

        sig = self.get_signature()
        if not sig:
            logging.error("Could not obtain signature. Aborting fetch.")
            return []

        all_channels = []
        seen_urls = set()
        
        for group in target_groups:
            logging.info(f"Fetching group: {group}...")
            cursor = 0
            group_items = 0
            
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
                    "clientVersion": "3.0.2"
                }
                
                headers = {
                    "user-agent": USER_AGENT,
                    "accept": "application/json",
                    "content-type": "application/json; charset=utf-8",
                    "mediahubmx-signature": sig
                }
                
                try:
                    # Disable SSL verification
                    r = requests.post(VAOO_URL, json=data, headers=headers, timeout=15, verify=False)

                    r.raise_for_status()
                    res = r.json()
                    
                    items = res.get("items", [])
                    if not items:
                        break
                        
                    for item in items:
                        url = item.get("url")
                        name = item.get("name")
                        seen_key = (name, url)
                        if url and seen_key not in seen_urls:
                            clean_item = {
                                "name": name,
                                "url": url,
                                "group": group,
                                "logo": item.get("logo")
                            }
                            all_channels.append(clean_item)
                            seen_urls.add(seen_key)
                            group_items += 1
                    
                    cursor = res.get("nextCursor")
                    if cursor is None:
                        break
                        
                except Exception as e:
                    logging.error(f"Error fetching {group}: {e}")
                    break
            
            logging.info(f" > Found {group_items} channels in {group}")

        # Always search for RSI specifically to ensure we catch all variants and groups
        rsi_channels = self.brute_force_search_rsi(sig)
        for rsi_ch in rsi_channels:
            seen_key = (rsi_ch['name'], rsi_ch['url'])
            if seen_key not in seen_urls:
                all_channels.append(rsi_ch)
                seen_urls.add(seen_key)

        return all_channels

    def brute_force_search_rsi(self, sig):
        """Searches specifically for RSI channels in likely groups."""
        target_names = ["RSI LA 1", "RSI LA 2", "RSI LA1", "RSI LA2"]
        found = []
        # Germany and Vavoo are most likely candidates for Swiss content
        search_groups = ["Italy", "Germany", "Vavoo", "Switzerland", "Swiss", "Other"] 
        search_queries = ["RSI LA", "RSI LA 1", "RSI LA 2", "RSI", "LA 1", "LA 2"]
        
        logging.info("Attempting targeted search for RSI channels...")
        
        seen_urls_rsi = set()
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
                        "clientVersion": "3.0.2"
                    }
                    
                    headers = {
                        "user-agent": USER_AGENT,
                        "accept": "application/json",
                        "content-type": "application/json; charset=utf-8",
                        "mediahubmx-signature": sig
                    }
                    
                    try:
                        r = requests.post(VAOO_URL, json=data, headers=headers, timeout=12, verify=False)
                        if r.status_code == 200:
                            res = r.json()
                            items = res.get("items", [])
                            if not items:
                                break
                            
                            for item in items:
                                name = item.get("name", "")
                                url = item.get("url")
                                
                                if url and url not in seen_urls_rsi:
                                    clean_name_up = name.upper()
                                    if any(tn.upper() in clean_name_up for tn in target_names):
                                        found.append({
                                            "name": name,
                                            "url": url,
                                            "group": "Switzerland", 
                                            "logo": item.get("logo"),
                                            "priority": 100 
                                        })
                                        seen_urls_rsi.add(url) # We still deduplicate URLs locally within this search
                            
                            cursor = res.get("nextCursor")
                            if cursor is None:
                                break
                        else:
                            break
                    except Exception:
                        break
                
        return found



    def _normalize_name(self, name):
        import re
        if not name: return ""
        n = name.upper()
        n = re.sub(r'\[.*\]', '', n)
        n = re.sub(r'\(.*\)', '', n)
        n = re.sub(r'\s+(HD|FHD|SD|4K|ITA|ITALIA|BACKUP|TIMVISION|PLUS)$', '', n)
        
        # Handle Vavoo specific suffixes
        if not n.startswith("HISTORY"):
            n = re.sub(r'\s+\.[A-Z0-9]{1,3}$', '', n) # Remove " .c", " .s" (Upper because n is upper)
        n = re.sub(r'\s+\+$', '', n)
        n = re.sub(r'[^A-Z0-9 ]', '', n)
        n = re.sub(r'\s+', ' ', n)
        return n.strip()

    def _get_categories(self, norm_name):
        """Returns ALL matching categories for a channel (supports multi-group)."""
        categories = []
        for category, keywords in BOUQUETS.items():
            for k in keywords:
                if k in norm_name:
                    categories.append(category)
                    break  # Don't match same category twice
        return categories if categories else ["Other"]

    def _get_priority(self, norm_name):
        # Exact match logic for short names to avoid partial overlap issues
        if norm_name in TIVUSAT_ORDER:
            return TIVUSAT_ORDER[norm_name]
        
        # Substring match if not exact
        for k, v in TIVUSAT_ORDER.items():
            if k in norm_name:
                return v
        return 9999

    def generate_m3u8(self, output_path, groups=None, is_xc=False):
        """
        Generates an M3U8 playlist file with sorting, categorization, and local logos.
        
        Args:
            output_path (str): Path to save the playlist.
            groups (list): Groups to include.
            is_xc (bool): If True, generates XCIPTV/Ottrun compatible format.
        """
        # 1. Delete existing playlist if it exists
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

        # Process channels
        processed_channels = []
        logos_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logos") # Assuming script is in python_iptv/src
        
        # Verify logos dir path, fallback to current dir/logos if not found
        if not os.path.exists(logos_dir):
             logos_dir = os.path.join(os.path.dirname(__file__), "logos")

        # Load EPGs to populate names
        logging.info("Loading EPG data for name resolution...")
        self.dm.load_all_epgs()

        for ch in channels:
            norm_name = self._normalize_name(ch['name'])
            
            # BLACKLIST
            if "RAI ITALIA" in norm_name:
                continue
            if "STAR CRIME" in norm_name:
                continue
            if "SKYSHOWTIME 1" in norm_name:
                continue
            if "SKY SPORT FOOTBALL" in norm_name:
                continue
            
            # RENAME
            if norm_name == "RAI":
                # Special case for generic "RAI" which is actually RAI 4K on Vavoo
                norm_name = "RAI 4K"
                ch['final_logo_override'] = "logos/Rai4k.it.png"
                ch['no_epg'] = True
            elif norm_name == "RAI 4K":
                ch['final_logo_override'] = "logos/Rai4k.it.png"
                ch['no_epg'] = True
            elif norm_name == "LA 7":
                norm_name = "LA7"
            elif norm_name == "LA 5":
                norm_name = "LA5"
            elif norm_name in ("8 TV", "8TV", "8", "TV 8"):
                norm_name = "TV8"
            elif norm_name == "CINE 34":
                norm_name = "CINE34"
            elif norm_name == "TV 2000":
                norm_name = "TV2000"
            elif norm_name in ("TG COM 24", "TGCOM 24"):
                norm_name = "TGCOM24"
            elif norm_name == "SKY TG 24":
                norm_name = "SKY TG24"
            elif norm_name in ("SPORT ITALIA", "SPORTITALIA PLUS", "SPORTITALIA SOLOCALCIO"):
                norm_name = "SPORTITALIA"
            elif norm_name == "SUPER":
                norm_name = "SUPER!"
            elif norm_name in ("RTL 1025", "RTL1025"):
                norm_name = "RTL 102.5"
            elif norm_name == "DISCOVERY NOVE":
                norm_name = "NOVE"
            elif norm_name == "DISCOVERY K2":
                norm_name = "K2"
            elif norm_name == "DISCOVERY FOCUS":
                norm_name = "FOCUS"
            elif norm_name == "MEDIASET IRIS":
                norm_name = "IRIS"
            elif norm_name == "MEDIASET ITALIA 2":
                norm_name = "ITALIA 2"
            elif norm_name == "SKY CINEMA UNO 24":
                norm_name = "SKY CINEMA UNO"
            elif norm_name == "SKY CRIME":
                norm_name = "TOP CRIME"
            elif norm_name == "PREMIUM CRIME":
                norm_name = "TOP CRIME"
            elif norm_name == "SKY SPORT MOTOGP":
                norm_name = "SKY SPORT MOTO GP"
            elif norm_name == "SKY SPORTS F1":
                norm_name = "SKY SPORT F1"
            elif norm_name == "SKY SUPER TENNIS":
                norm_name = "SUPER TENNIS"
            elif norm_name in ("CANALE 27", "27", "TWENTYSEVEN", "TWENTY SEVEN", "27 TWENTY SEVEN", "27 TWENTYSEVEN"):
                norm_name = "TWENTYSEVEN"
            elif norm_name in ("CINE 34 MEDIASET",):
                norm_name = "CINE34"
            elif norm_name in ("MEDIASET 20", "MEDIASET 1"):
                norm_name = "20 MEDIASET"
            elif norm_name == "MOTORTREND":
                norm_name = "MOTOR TREND"
            elif norm_name == "LA 7 D":
                norm_name = "LA7D"
            elif norm_name == "RAI SPORT":
                ch['final_logo_override'] = "logos/rai-sport-hd-it.svg"
            elif norm_name.startswith("HISTORY") and "CHANNEL" not in norm_name and norm_name != "HISTORY":
                norm_name = "HISTORY"
            elif norm_name == "HISTORY CHANNEL S" or norm_name == "HISTORY  CHANNEL S":
                norm_name = "HISTORY"
            
            categories = self._get_categories(norm_name)
            priority = self._get_priority(norm_name)
            
            if priority == 9999:
                 if "SKY" in norm_name: priority = 200
                 elif "DAZN" in norm_name: priority = 210
                 elif "PRIMA" in norm_name: priority = 300
            
            # Resolve EPG ID and Logo
            epg_id = "" if ch.get('no_epg') else EPG_MAP.get(norm_name, "")
            
            # Resolve Clean Name from EPG
            clean_display_name = norm_name
            if norm_name == "HISTORY":
                clean_display_name = "HISTORY"
            elif epg_id:
                epg_name = self.dm.get_clean_epg_name(epg_id)
                if epg_name:
                    clean_display_name = epg_name

            tvg_id = epg_id if epg_id else norm_name
            if ch.get('no_epg'): tvg_id = ""
            
            tvg_name = tvg_id if tvg_id else clean_display_name
            if ch.get('no_epg'):
                tvg_name = clean_display_name
                tvg_id = ""
            
            # Check local logo
            logo_path = ch['logo'] # Default to remote
            if ch.get('final_logo_override'):
                logo_path = ch['final_logo_override'].replace("logos/", "https://raw.githubusercontent.com/mich-de/vavoo-player/master/logos/")
            elif epg_id:
                target_fname = f"{epg_id}.png".lower()
                matched_file = None
                
                try:
                    if os.path.exists(logos_dir):
                        for f in os.listdir(logos_dir):
                            if f.lower() == target_fname:
                                matched_file = f
                                break
                except Exception as e:
                    logging.error(f"Error scanning logos directory: {e}")

                if matched_file:
                    logo_path = f"https://raw.githubusercontent.com/mich-de/vavoo-player/master/logos/{matched_file}"
            
            # Duplicate channel into each matching group
            for category in categories:
                ch_copy = ch.copy()
                ch_copy['norm_name'] = norm_name
                ch_copy['group'] = category
                ch_copy['priority'] = priority
                ch_copy['tvg_id'] = tvg_id
                ch_copy['tvg_name'] = tvg_name
                ch_copy['final_logo'] = logo_path
                ch_copy['clean_name'] = clean_display_name
                processed_channels.append(ch_copy)

        # Sort
        processed_channels.sort(key=lambda x: (x['priority'], x['group'], x['norm_name']))

        if not processed_channels:
            logging.warning("No valid channels to write.")
            return False

        try:
            logging.info(f"Writing {len(processed_channels)} channels to {output_path}...")
            with open(output_path, "w", encoding="utf-8") as f:
                epg_url = "https://raw.githubusercontent.com/mich-de/vavoo-player/master/epg.xml"
                f.write(f'#EXTM3U x-tvg-url="{epg_url}"\n')
                
                for ch in processed_channels:
                    f.write(f'#EXTVLCOPT:http-user-agent={USER_AGENT}\n')
                    header = f'#EXTINF:-1 tvg-id="{ch["tvg_id"]}" tvg-name="{ch["clean_name"]}" tvg-logo="{ch["final_logo"]}" channel="{ch["tvg_id"]}" group-title="{ch["group"]}",{ch["clean_name"]}'
                    f.write(f"{header}\n")
                    f.write(f"{ch['url']}\n")
                    
            logging.info("Playlist generated successfully.")
            return True
        except Exception as e:
            logging.error(f"Error writing playlist: {e}")
            return False

if __name__ == "__main__":
    # Test run
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler("vavoo_player.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    gen = PlaylistGenerator()
    gen.generate_m3u8("test_playlist.m3u8", groups=["Italy", "Switzerland", "Vavoo"])
