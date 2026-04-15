# Vavoo Player per VLC/mpv

Playlist IPTV italiana da Vavoo con supporto per VLC e mpv.

## Perché Serve un Player Speciale?

VLC non può leggere i flussi Vavoo perché richiedono header di autenticazione speciali (`mediahubmx-signature`) che VLC non può aggiungere. **mpv** supporta header HTTP nativamente!

## Installazione Rapida

### Opzione 1: mpv (Consigliato - Più Semplice)

1. **Installa mpv** da <https://mpv.io/installation/>
   - Windows: Scarica da <https://sourceforge.net/projects/mpv-player-windows/files/>
   - macOS: `brew install mpv`
   - Linux: `apt install mpv` o `pacman -S mpv`

2. **Genera la playlist** (opzionale, per avere la lista canali):

   ```bash
   cd scripts
   python generate_streamlink_playlist.py
   ```

3. **Riproduci un canale**:

   ```bash
   cd scripts
   python play_with_mpv.py --channel "RAI 1"
   ```

### Opzione 2: Streamlink + VLC

1. **Installa Streamlink**:

   ```bash
   pip install streamlink
   ```

2. **Genera la playlist**:

   ```bash
   cd scripts
   python generate_streamlink_playlist.py
   ```

3. **Riproduci con VLC**:

   ```bash
   cd scripts
   python play_with_streamlink.py
   ```

## Struttura Progetto

```
vavoo player/
├── src/                    # Codice sorgente
│   ├── playlist_generator.py
│   ├── data_manager.py
│   ├── epg_manager.py
│   └── epg_merger.py
├── scripts/                # Script eseguibili
│   ├── generate_streamlink_playlist.py  # Genera playlist per Streamlink
│   ├── play_with_streamlink.py          # Riproduce con Streamlink
│   ├── generate_playlist.py             # Genera playlist standard (Kodi)
│   ├── generate_proxy_playlist.py       # Genera playlist con proxy
│   └── server.py                        # Server proxy opzionale
├── logos/                  # Loghi canali
├── epg.xml                 # Dati EPG
├── playlist.m3u8           # Playlist generata
└── requirements.txt        # Dipendenze Python
```

## Comandi Disponibili

### Generare la Playlist per Streamlink

```bash
cd scripts
python generate_streamlink_playlist.py
```

### Riprodurre i Canali

```bash
cd scripts

# Riproduci dalla playlist
python play_with_streamlink.py

# Riproduci un canale specifico
python play_with_streamlink.py --channel "RAI 1"

# Lista canali disponibili
python play_with_streamlink.py --list

# Usa mpv invece di VLC
python play_with_streamlink.py --player mpv
```

### Generare Playlist Standard (per Kodi)

```bash
cd scripts
python generate_playlist.py
```

## Usare con Player IPTV Esterni

La playlist generata (`playlist_streamlink.m3u8`) contiene header speciali per Streamlink. Per usarla con altri player IPTV:

### Opzione 1: Streamlink (Consigliato)

```bash
streamlink --player vlc playlist_streamlink.m3u8
```

### Opzione 2: mpv Player

mpv supporta header HTTP nativamente:

```bash
mpv --http-header-fields="mediahubmx-signature: YOUR_SIGNATURE" "STREAM_URL"
```

### Opzione 3: Server Proxy

Esegui il server proxy locale:

```bash
cd scripts
python server.py
```

Poi usa `playlist_proxy.m3u8` con qualsiasi player.

## Deploy Remoto (Opzionale)

Se vuoi accedere alla playlist da altri dispositivi:

1. Fork questo repository su GitHub
2. Vai su [render.com](https://render.com) e crea un Web Service
3. Connetti il repository (deploy automatico grazie a `render.yaml`)
4. Usa l'URL del servizio per accedere da remoto

## Requisiti

- Python 3.8+
- Streamlink
- VLC o mpv

## Note

- La firma di autenticazione scade dopo ~10 minuti
- Streamlink la aggiorna automaticamente
- I canali disponibili dipendono dall'API Vavoo

## Licenza

Uso personale e didattico.
