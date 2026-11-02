#!/usr/bin/env python3
"""
List all active gaming platforms on Batocera with ROM and Media statistics.
"""
import os
import glob
import xml.etree.ElementTree as ET

ES_SYSTEMS_PATH = "/etc/emulationstation/es_systems.cfg"

# Colors
C_RESET  = "\033[0m"
C_BOLD   = "\033[1m"
C_GREEN  = "\033[1;32m"
C_YELLOW = "\033[1;33m"
C_CYAN   = "\033[1;36m"
C_RED    = "\033[1;31m"
C_DIM    = "\033[2m"

def get_active_systems():
    if not os.path.exists(ES_SYSTEMS_PATH):
        print(f"Error: {ES_SYSTEMS_PATH} not found.")
        return []

    try:
        tree = ET.parse(ES_SYSTEMS_PATH)
        root = tree.getroot()
    except Exception as e:
        print(f"Error parsing {ES_SYSTEMS_PATH}: {e}")
        return []

    active = []
    for s in root.findall("system"):
        name_el = s.find("name")
        fullname_el = s.find("fullname")
        path_el = s.find("path")
        ext_el = s.find("extension")

        name = name_el.text.strip() if name_el is not None and name_el.text else ""
        fullname = fullname_el.text.strip() if fullname_el is not None and fullname_el.text else name
        raw_path = path_el.text.strip() if path_el is not None and path_el.text else ""

        if not name or not raw_path:
            continue

        real_path = os.path.realpath(raw_path)
        if not os.path.exists(real_path):
            continue

        gl_path = os.path.join(real_path, "gamelist.xml")
        num_games = 0

        # Try gamelist first
        if os.path.exists(gl_path):
            try:
                gltree = ET.parse(gl_path)
                num_games = len(gltree.getroot().findall("game"))
            except Exception:
                pass

        # Fallback to counting files
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
            covers = len(glob.glob(os.path.join(real_path, "images", "*-image.*")))
            thumbs = len(glob.glob(os.path.join(real_path, "images", "*-thumb.*")))
            marquees = len(glob.glob(os.path.join(real_path, "images", "*-marquee.*")))
            videos = len(glob.glob(os.path.join(real_path, "videos", "*-video.*")))

            req_media = num_games
            vid_pct = min(100, int((videos / req_media) * 100)) if req_media > 0 else 0
            thumb_pct = min(100, int((thumbs / req_media) * 100)) if req_media > 0 else 0
            cover_pct = min(100, int((covers / req_media) * 100)) if req_media > 0 else 0

            avg_pct = int((cover_pct + thumb_pct + vid_pct) / 3)

            active.append({
                "name": name,
                "fullname": fullname,
                "games": num_games,
                "covers": covers,
                "thumbs": thumbs,
                "marquees": marquees,
                "videos": videos,
                "pct": avg_pct,
                "path": real_path
            })

    return sorted(active, key=lambda x: (-x["games"], x["name"]))

def main():
    systems = get_active_systems()
    if not systems:
        print("Nenhuma plataforma com jogos encontrada.")
        return

    total_games = sum(s["games"] for s in systems)
    total_covers = sum(s["covers"] for s in systems)
    total_thumbs = sum(s["thumbs"] for s in systems)
    total_marquees = sum(s["marquees"] for s in systems)
    total_videos = sum(s["videos"] for s in systems)

    header = f"{'PLATAFORMA':<15} | {'JOGOS':>5} | {'CAPAS':>5} | {'THUMBS':>6} | {'LOGOS':>5} | {'VÍDEOS':>6} | {'STATUS':<20} | NOME"
    sep = "=" * 95

    print(f"\n{C_BOLD}{sep}{C_RESET}")
    print(f"{C_CYAN}  PLATAFORMAS DISPONÍVEIS NO BATOCERA ({len(systems)} ativas com {total_games} jogos){C_RESET}")
    print(f"{C_BOLD}{sep}{C_RESET}")
    print(f"{C_BOLD}{header}{C_RESET}")
    print(f"{C_DIM}{'-'*95}{C_RESET}")

    for s in systems:
        pct = s["pct"]
        if pct >= 90:
            status_str = f"{C_GREEN}● {pct:>3}% Completo{C_RESET}"
        elif pct >= 40:
            status_str = f"{C_YELLOW}◐ {pct:>3}% Parcial{C_RESET}"
        else:
            status_str = f"{C_RED}○ {pct:>3}% Pendente{C_RESET}"

        line = f"{s['name']:<15} | {s['games']:>5} | {s['covers']:>5} | {s['thumbs']:>6} | {s['marquees']:>5} | {s['videos']:>6} | {status_str:<30} | {s['fullname']}"
        print(line)

    print(f"{C_DIM}{'-'*95}{C_RESET}")
    print(f"{C_BOLD}{'TOTAL':<15} | {total_games:>5} | {total_covers:>5} | {total_thumbs:>6} | {total_marquees:>5} | {total_videos:>6} | {'':<20} | {len(systems)} plataformas{C_RESET}")
    print(f"{C_BOLD}{sep}{C_RESET}\n")

if __name__ == "__main__":
    main()
