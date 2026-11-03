#!/usr/bin/env python3
"""
Modern Multi-Threaded Scraper for Batocera (5 Parallel Workers)
Multi-Provider Edition: ScreenScraper + ArcadeDB (Arcade Italia) Fallback!
Features:
- Smart Resume: Scans existing media first; NEVER restarts from 0%!
- Multi-Source: ScreenScraper (Primary) + ArcadeDB (Auto-fallback for MAME, FBNeo, NeoGeo, CPS, etc.).
- Real-time visual progress counter [current/total | percent%].
- Auto-detects all active platforms with games when run without arguments.
- Downloads Boxart 2D / Flyers, In-game Screenshots (-thumb.png), Wheel/Marquee (-marquee.png), and Video Snaps (-video.mp4).
- Safe multi-threaded gamelist.xml synchronization.
- Storage guard: halts downloads if free space drops below threshold.
- Auto-reloads EmulationStation after each system.
"""
import os
import sys
import time
import json
import glob
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import xml.etree.ElementTree as ET
from xml.dom import minidom

LOG_FILE = "/userdata/system/logs/fast_scraper.log"
PID_FILE = "/userdata/system/logs/fast_scraper.pid"
STATUS_JSON = "/userdata/system/logs/fast_scraper_status.json"
ES_SYSTEMS_PATH = "/etc/emulationstation/es_systems.cfg"
CONFIG_PATH = "/userdata/system/configs/fast_scraper/config.json"
ES_SETTINGS_XML = "/userdata/system/configs/emulationstation/es_settings.cfg"
BATOCERA_CONF = "/userdata/system/batocera.conf"

MIN_FREE_GB = 22.0
MAX_WORKERS = 5

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

log_lock = threading.Lock()
xml_lock = threading.Lock()
status_lock = threading.Lock()

def log(msg):
    ts = time.strftime("[%Y-%m-%d %H:%M:%S]")
    line = f"{ts} {msg}"
    with log_lock:
        print(line, flush=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")

class SystemProgress:
    def __init__(self, system_name, total_games, start_count=0):
        self.system_name = system_name
        self.total = total_games
        self.processed = start_count
        self.success = 0
        self.lock = threading.Lock()
        pct = (self.processed / self.total * 100) if self.total > 0 else 0.0
        self._write_status(pct, "Iniciando...")

    def _write_status(self, pct, game_name):
        try:
            data = {
                "pid": os.getpid(),
                "system": self.system_name,
                "processed": self.processed,
                "total": self.total,
                "percent": round(pct, 1),
                "remaining": max(0, self.total - self.processed),
                "last_game": game_name,
                "status": "running",
                "updated_at": time.strftime("%H:%M:%S")
            }
            with status_lock:
                with open(STATUS_JSON, "w", encoding="utf-8") as sf:
                    json.dump(data, sf)
        except Exception:
            pass

    def advance(self, game_name, success=False):
        with self.lock:
            self.processed += 1
            if success:
                self.success += 1
            pct = (self.processed / self.total * 100) if self.total > 0 else 0.0
            self._write_status(pct, game_name)
            return self.processed, pct

def load_credentials():
    ss_user = ""
    ss_pass = ""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                ss_user = cfg.get("ssid", "") or cfg.get("user", "")
                ss_pass = cfg.get("sspassword", "") or cfg.get("password", "")
        except Exception:
            pass

    if not ss_user and os.path.exists(ES_SETTINGS_XML):
        try:
            tree = ET.parse(ES_SETTINGS_XML)
            for s in tree.getroot().findall("string"):
                if s.get("name") == "ScreenScraperUser":
                    ss_user = s.get("value", "")
                elif s.get("name") == "ScreenScraperPass":
                    ss_pass = s.get("value", "")
        except Exception:
            pass

    if not ss_user and os.path.exists(BATOCERA_CONF):
        try:
            with open(BATOCERA_CONF, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("scrapper.user="):
                        ss_user = line.split("=", 1)[1].strip()
                    elif line.startswith("scrapper.password="):
                        ss_pass = line.split("=", 1)[1].strip()
        except Exception:
            pass

    return ss_user, ss_pass

try:
    creds = requests.get('https://retrogamesets.fr/rgsx/manager/rgsx_screenscraper_credentials_api.php', timeout=8).json()
    DEVID = creds['devid']
    DEVPASS = creds['devpassword']
except Exception as e:
    DEVID = ""
    DEVPASS = ""
    log(f"ScreenScraper credentials error: {e}")

SS_USER, SS_PASS = load_credentials()
SS_API_URL = "https://api.screenscraper.fr/api2/jeuInfos.php"
ARCADEDB_API_URL = "http://adb.arcadeitalia.net/service_scraper.php"

ARCADE_SYSTEMS = {
    'mame', 'fbneo', 'neogeo', 'arcadeclassics',
    'cps1', 'cps2', 'cps3', 'atomiswave', 'naomi',
    'model2', 'model3'
}

SYSTEM_IDS = {
    # Arcade
    'mame': '75',
    'fbneo': '75',
    'arcadeclassics': '75',
    'cps1': '75',
    'cps2': '75',
    'cps3': '75',
    'neogeo': '142',
    'atomiswave': '53',
    'naomi': '56',
    'naomi2': '56',
    'model2': '118',
    'model3': '119',
    'daphne': '30',
    # Nintendo
    'nes': '3',
    'fds': '106',
    'snes': '4',
    'n64': '14',
    'gamecube': '13',
    'wii': '16',
    'wiiu': '18',
    'gb': '9',
    'gbc': '10',
    'gba': '12',
    'nds': '15',
    '3ds': '17',
    'virtualboy': '11',
    # Sega
    'sg1000': '109',
    'mastersystem': '2',
    'gamegear': '21',
    'megadrive': '1',
    'megacd': '20',
    'segacd': '20',
    'sega32x': '19',
    'saturn': '22',
    'dreamcast': '23',
    # Sony
    'psx': '57',
    'ps2': '58',
    'psp': '61',
    'psvita': '62',
    # Atari
    'atari2600': '40',
    'atari5200': '41',
    'atari7800': '42',
    'atari800': '43',
    'atarist': '44',
    'lynx': '28',
    'jaguar': '27',
    # Other consoles / microcomputers
    'pcengine': '31',
    'pcenginecd': '116',
    'amiga500': '64',
    'amiga1200': '111',
    'amstradcpc': '65',
    'c64': '66',
    '3do': '111',
    'cdi': '113',
    'msx1': '114',
    'msx2': '115',
    'intellivision': '117',
    'ngp': '25',
    'ngpc': '82',
    'tic80': '221',
    'openbor': '214',
    'solarus': '222',
    'xbox': '32',
}

def get_free_gb(path="/media/SHARE_1"):
    try:
        st = os.statvfs(path)
        return (st.f_bavail * st.f_frsize) / (1024 ** 3)
    except Exception:
        return 999.0

def download_media(url, target_path, min_size=500):
    try:
        r = requests.get(url, timeout=25)
        if r.status_code == 200 and len(r.content) >= min_size:
            with open(target_path, 'wb') as f:
                f.write(r.content)
            os.chmod(target_path, 0o644)
            return True
    except Exception:
        pass
    return False

def save_gamelist(root, gl_path):
    with xml_lock:
        try:
            rough_string = ET.tostring(root, 'utf-8')
            reparsed = minidom.parseString(rough_string)
            clean_xml = '\n'.join([line for line in reparsed.toprettyxml(indent='\t').split('\n') if line.strip()])
            with open(gl_path, 'w', encoding='utf-8') as f:
                f.write(clean_xml)
        except Exception as e:
            log(f"Error saving gamelist {gl_path}: {e}")

def get_system_dir(system_name):
    share_path = f"/media/SHARE_1/{system_name}"
    if os.path.exists(share_path):
        return share_path
    
    ud_path = f"/userdata/roms/{system_name}"
    if os.path.exists(ud_path):
        return os.path.realpath(ud_path)

    if os.path.exists(ES_SYSTEMS_PATH):
        try:
            tree = ET.parse(ES_SYSTEMS_PATH)
            for s in tree.getroot().findall("system"):
                n = s.find("name")
                if n is not None and n.text.strip().lower() == system_name.lower():
                    p = s.find("path")
                    if p is not None and p.text:
                        rp = os.path.realpath(p.text.strip())
                        if os.path.exists(rp):
                            return rp
        except Exception:
            pass
    return None

def auto_detect_systems():
    if not os.path.exists(ES_SYSTEMS_PATH):
        return []

    try:
        tree = ET.parse(ES_SYSTEMS_PATH)
        root = tree.getroot()
    except Exception:
        return []

    detected = []
    for s in root.findall("system"):
        name_el = s.find("name")
        path_el = s.find("path")
        ext_el = s.find("extension")
        if name_el is None or not name_el.text:
            continue
        sname = name_el.text.strip().lower()
        if sname not in SYSTEM_IDS:
            continue

        raw_path = path_el.text.strip() if path_el is not None and path_el.text else f"/userdata/roms/{sname}"
        real_path = os.path.realpath(raw_path)
        if not os.path.exists(real_path):
            continue

        gl_path = os.path.join(real_path, "gamelist.xml")
        num_games = 0
        if os.path.exists(gl_path):
            try:
                gltree = ET.parse(gl_path)
                num_games = len(gltree.getroot().findall("game"))
            except Exception:
                pass

        if num_games == 0:
            exts = ext_el.text.split() if ext_el is not None and ext_el.text else []
            try:
                files = [
                    f for f in os.listdir(real_path)
                    if not f.startswith(".") and f != "gamelist.xml" and not os.path.isdir(os.path.join(real_path, f))
                    and (not exts or any(f.lower().endswith(e.lower()) for e in exts))
                ]
                num_games = len(files)
            except Exception:
                pass

        if num_games > 0:
            thumbs = len(glob.glob(os.path.join(real_path, "images", "*-thumb.*")))
            vids = len(glob.glob(os.path.join(real_path, "videos", "*-video.*")))
            covers = len(glob.glob(os.path.join(real_path, "images", "*-image.*")))

            if sname in ARCADE_SYSTEMS:
                if vids < (num_games * 0.95) or covers < (num_games * 0.95) or thumbs < (num_games * 0.95):
                    detected.append((sname, num_games, covers, vids))
            else:
                if thumbs < (num_games * 0.90) or covers < (num_games * 0.90):
                    detected.append((sname, num_games, covers, thumbs))

    detected.sort(key=lambda x: (x[1] - x[3]), reverse=True)
    return [d[0] for d in detected]

def query_arcadedb(rom_short_name):
    params = {
        "ajax": "query_mame",
        "lang": "en",
        "game_name": rom_short_name
    }
    try:
        r = requests.get(ARCADEDB_API_URL, params=params, timeout=10)
        if r.status_code == 200:
            res = r.json().get("result", [])
            if res:
                return res[0]
    except Exception:
        pass
    return None

def process_single_game(system_name, sys_id, base_dir, img_dir, vid_dir, game_elem, progress_tracker):
    path_elem = game_elem.find('path')
    if path_elem is None or not path_elem.text:
        progress_tracker.advance("unknown", success=False)
        return False
    
    fn = os.path.basename(path_elem.text.strip())
    base_no_ext = os.path.splitext(fn)[0]

    box_file = os.path.join(img_dir, f"{base_no_ext}-image.png")
    ss_file = os.path.join(img_dir, f"{base_no_ext}-thumb.png")
    wheel_file = os.path.join(img_dir, f"{base_no_ext}-marquee.png")
    vid_file = os.path.join(vid_dir, f"{base_no_ext}-video.mp4")

    has_video = os.path.exists(vid_file) and os.path.getsize(vid_file) > 1024
    has_box = os.path.exists(box_file) and os.path.getsize(box_file) > 1024
    has_ss = os.path.exists(ss_file) and os.path.getsize(ss_file) > 1024
    has_wheel = os.path.exists(wheel_file) and os.path.getsize(wheel_file) > 1024

    need_video = not has_video
    need_ss = not has_ss
    need_wheel = not has_wheel
    need_box = not has_box

    if not (need_video or need_ss or need_wheel or need_box):
        progress_tracker.advance(base_no_ext, success=False)
        return False

    if need_video and get_free_gb("/media/SHARE_1") < MIN_FREE_GB:
        need_video = False

    downloaded_any = False
    source_used = "ScreenScraper"

    # --- 1. TENTATIVA PRINCIPAL: ScreenScraper API ---
    ss_params = {
        "devid": DEVID,
        "devpassword": DEVPASS,
        "softname": "RGSX",
        "output": "json",
        "ssid": SS_USER,
        "sspassword": SS_PASS,
        "systemeid": sys_id,
        "romnom": fn
    }

    medias = []
    jeu_data = {}
    ss_failed = False

    try:
        r = requests.get(SS_API_URL, params=ss_params, timeout=12)
        if r.status_code == 200:
            jeu_data = r.json().get('response', {}).get('jeu', {})
            medias = jeu_data.get('medias', [])
        elif r.status_code in (430, 431):
            ss_failed = True
        else:
            ss_failed = True
    except Exception:
        ss_failed = True

    if medias or jeu_data:
        # 1. Capa ScreenScraper
        if need_box:
            box_url = None
            for reg in ('br', 'us', 'wor', 'eu', 'ss', 'jp'):
                for m in medias:
                    if m.get('type') == 'box-2D' and m.get('region') == reg:
                        box_url = m.get('url')
                        break
                if box_url:
                    break
            if not box_url:
                for m in medias:
                    if m.get('type') in ('box-2D', 'box-3D', 'flyer'):
                        box_url = m.get('url')
                        break

            if box_url and download_media(box_url, box_file):
                downloaded_any = True
                need_box = False
                with xml_lock:
                    ie = game_elem.find('image')
                    if ie is None: ie = ET.SubElement(game_elem, 'image')
                    ie.text = f"./images/{base_no_ext}-image.png"

        # 2. Screenshot ScreenScraper
        if need_ss:
            ss_url = None
            for m in medias:
                if m.get('type') == 'ss':
                    ss_url = m.get('url')
                    break
            if not ss_url:
                for m in medias:
                    if m.get('type') == 'sstitle':
                        ss_url = m.get('url')
                        break

            if ss_url and download_media(ss_url, ss_file):
                downloaded_any = True
                need_ss = False
                with xml_lock:
                    te = game_elem.find('thumbnail')
                    if te is None: te = ET.SubElement(game_elem, 'thumbnail')
                    te.text = f"./images/{base_no_ext}-thumb.png"

        # 3. Marquee ScreenScraper
        if need_wheel:
            wheel_url = None
            for reg in ('br', 'us', 'wor', 'eu', 'ss', 'jp', None):
                for m in medias:
                    if m.get('type') == 'wheel' and (m.get('region') == reg or reg is None):
                        wheel_url = m.get('url')
                        break
                if wheel_url:
                    break
            if not wheel_url:
                for m in medias:
                    if m.get('type') in ('wheel', 'wheel-steel', 'wheel-carbon', 'marquee'):
                        wheel_url = m.get('url')
                        break

            if wheel_url and download_media(wheel_url, wheel_file):
                downloaded_any = True
                need_wheel = False
                with xml_lock:
                    me = game_elem.find('marquee')
                    if me is None: me = ET.SubElement(game_elem, 'marquee')
                    me.text = f"./images/{base_no_ext}-marquee.png"

        # 4. Video ScreenScraper
        if need_video:
            vid_url = None
            for m in medias:
                if m.get('type') == 'video-normalized':
                    vid_url = m.get('url')
                    break
            if not vid_url:
                for m in medias:
                    if m.get('type') == 'video':
                        vid_url = m.get('url')
                        break

            if vid_url and download_media(vid_url, vid_file, min_size=1024):
                downloaded_any = True
                need_video = False
                with xml_lock:
                    ve = game_elem.find('video')
                    if ve is None: ve = ET.SubElement(game_elem, 'video')
                    ve.text = f"./videos/{base_no_ext}-video.mp4"

        # 5. Metadados
        synopsis = jeu_data.get('synopsis', [])
        desc_text = None
        for s in synopsis:
            if s.get('langue') in ('pt', 'br'):
                desc_text = s.get('text')
                break
        if not desc_text:
            for s in synopsis:
                if s.get('langue') in ('en', 'us'):
                    desc_text = s.get('text')
                    break

        with xml_lock:
            if desc_text and game_elem.find('desc') is None:
                d = ET.SubElement(game_elem, 'desc')
                d.text = desc_text
            dev = jeu_data.get('developpeur', {}).get('text')
            if dev and game_elem.find('developer') is None:
                d = ET.SubElement(game_elem, 'developer')
                d.text = dev
            pub = jeu_data.get('editeur', {}).get('text')
            if pub and game_elem.find('publisher') is None:
                p = ET.SubElement(game_elem, 'publisher')
                p.text = pub

    # --- 2. FALLBACK INTELIGENTE: ArcadeDB (Arcade Italia) ---
    # Ativado se o sistema for Arcade (MAME, FBNeo, etc.) e ainda faltar vídeo, capa ou screenshot!
    if system_name in ARCADE_SYSTEMS and (need_video or need_box or need_ss or need_wheel):
        adb_data = query_arcadedb(base_no_ext)
        if adb_data:
            # Video snap do ArcadeDB
            adb_vid = adb_data.get("url_video_shortplay")
            if need_video and adb_vid:
                if download_media(adb_vid, vid_file, min_size=1024):
                    downloaded_any = True
                    source_used = "ArcadeDB"
                    with xml_lock:
                        ve = game_elem.find('video')
                        if ve is None: ve = ET.SubElement(game_elem, 'video')
                        ve.text = f"./videos/{base_no_ext}-video.mp4"

            # Flyer do ArcadeDB
            adb_flyer = adb_data.get("url_image_flyer")
            if need_box and adb_flyer and download_media(adb_flyer, box_file, min_size=500):
                downloaded_any = True
                source_used = "ArcadeDB"
                with xml_lock:
                    ie = game_elem.find('image')
                    if ie is None: ie = ET.SubElement(game_elem, 'image')
                    ie.text = f"./images/{base_no_ext}-image.png"

            # Screenshot Ingame do ArcadeDB
            adb_ss = adb_data.get("url_image_ingame") or adb_data.get("url_image_title")
            if need_ss and adb_ss and download_media(adb_ss, ss_file, min_size=500):
                downloaded_any = True
                source_used = "ArcadeDB"
                with xml_lock:
                    te = game_elem.find('thumbnail')
                    if te is None: te = ET.SubElement(game_elem, 'thumbnail')
                    te.text = f"./images/{base_no_ext}-thumb.png"

            # Marquee do ArcadeDB
            adb_mq = adb_data.get("url_image_marquee")
            if need_wheel and adb_mq and download_media(adb_mq, wheel_file, min_size=500):
                downloaded_any = True
                source_used = "ArcadeDB"
                with xml_lock:
                    me = game_elem.find('marquee')
                    if me is None: me = ET.SubElement(game_elem, 'marquee')
                    me.text = f"./images/{base_no_ext}-marquee.png"

            # Metadados complementares do ArcadeDB se estiverem vazios
            with xml_lock:
                mfg = adb_data.get("manufacturer")
                if mfg and game_elem.find('developer') is None:
                    d = ET.SubElement(game_elem, 'developer')
                    d.text = mfg

    curr_p, curr_pct = progress_tracker.advance(base_no_ext, success=downloaded_any)

    if downloaded_any:
        log(f"  [{system_name}] [{curr_p:>4}/{progress_tracker.total} | {curr_pct:4.1f}%] [{source_used} OK] {base_no_ext}")
        return True
    return False

def scrape_system(system_name):
    sname = system_name.lower().strip()
    sid = SYSTEM_IDS.get(sname)
    if not sid:
        log(f"[{sname}] Unsupported or unknown ScreenScraper system ID. Skipping.")
        return

    bdir = get_system_dir(sname)
    if not bdir or not os.path.exists(bdir):
        log(f"[{sname}] Directory not found for system. Skipping.")
        return

    gl_path = os.path.join(bdir, "gamelist.xml")
    img_dir = os.path.join(bdir, "images")
    vid_dir = os.path.join(bdir, "videos")
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(vid_dir, exist_ok=True)

    if not os.path.exists(gl_path):
        log(f"[{sname}] Gamelist not found: {gl_path}")
        return

    try:
        tree = ET.parse(gl_path)
        root = tree.getroot()
    except Exception as e:
        log(f"[{sname}] Failed to parse XML: {e}")
        return

    games = root.findall('game')
    total_games = len(games)
    free_now = get_free_gb("/media/SHARE_1")

    # Smart resume: Pre-scan games that already have media
    pending_games = []
    already_done = 0

    for g in games:
        p_el = g.find('path')
        if p_el is None or not p_el.text:
            already_done += 1
            continue
        fn = os.path.basename(p_el.text.strip())
        base_no_ext = os.path.splitext(fn)[0]

        box_file = os.path.join(img_dir, f"{base_no_ext}-image.png")
        ss_file = os.path.join(img_dir, f"{base_no_ext}-thumb.png")
        vid_file = os.path.join(vid_dir, f"{base_no_ext}-video.mp4")

        has_box = os.path.exists(box_file) and os.path.getsize(box_file) > 1024
        has_ss = os.path.exists(ss_file) and os.path.getsize(ss_file) > 1024
        has_vid = os.path.exists(vid_file) and os.path.getsize(vid_file) > 1024

        # For arcade systems, we actively check for videos too!
        if sname in ARCADE_SYSTEMS:
            if has_box and has_ss and has_vid:
                already_done += 1
            else:
                pending_games.append(g)
        else:
            if has_box and has_ss:
                already_done += 1
            else:
                pending_games.append(g)

    initial_pct = (already_done / total_games * 100) if total_games > 0 else 0.0

    log(f"\n=======================================================")
    log(f"=== FULL SCRAPE: {sname.upper()} | Total: {total_games} | Já completos: {already_done} ({initial_pct:4.1f}%) | Pendentes: {len(pending_games)} | Free: {free_now:.1f} GB ===")
    if sname in ARCADE_SYSTEMS:
        log(f"[{sname}] Multi-Source Ativo: ScreenScraper + ArcadeDB (Arcade Italia)")
    log(f"=======================================================")

    if not pending_games:
        log(f"[{sname}] Todos os {total_games} jogos já possuem as mídias completas! Nada a baixar.")
        return

    progress_tracker = SystemProgress(sname, total_games, start_count=already_done)
    success_count = 0
    saved_batch = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_single_game, sname, sid, bdir, img_dir, vid_dir, g, progress_tracker): g for g in pending_games}
        for future in as_completed(futures):
            res = future.result()
            if res:
                success_count += 1
                saved_batch += 1
                if saved_batch >= 15:
                    save_gamelist(root, gl_path)
                    saved_batch = 0

    save_gamelist(root, gl_path)
    log(f"[{sname}] Finished! Updated {success_count}/{len(pending_games)} pending games ({already_done + success_count}/{total_games} total).")

    try:
        requests.get('http://localhost:1234/reloadgames', timeout=3)
    except Exception:
        pass

def main():
    with open(PID_FILE, "w") as pf:
        pf.write(str(os.getpid()))

    target_systems = sys.argv[1:]
    if not target_systems or target_systems == ['all'] or target_systems == ['--all']:
        log("No specific systems provided. Auto-detecting all active platforms with games...")
        target_systems = auto_detect_systems()
        log(f"Auto-detected {len(target_systems)} platforms needing scrape: {target_systems}")
    else:
        log(f"Starting Multi-Threaded Scraper ({MAX_WORKERS} workers) for specified systems: {target_systems}")

    for s in target_systems:
        free_space = get_free_gb("/media/SHARE_1")
        if free_space < MIN_FREE_GB:
            log(f"CRITICAL: Free space {free_space:.1f} GB is below safety floor ({MIN_FREE_GB} GB). Aborting remaining queue.")
            break
        scrape_system(s)

    log("\n=== All Scraper Tasks Finished! ===")
    if os.path.exists(PID_FILE):
        try: os.remove(PID_FILE)
        except Exception: pass
    if os.path.exists(STATUS_JSON):
        try: os.remove(STATUS_JSON)
        except Exception: pass

if __name__ == "__main__":
    main()
