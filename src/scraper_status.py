#!/usr/bin/env python3
"""
Scraper Status & Progress Visualizer for Batocera.
Displays current scraper process, visual ASCII progress bar, and recent activity.
"""
import os
import sys
import json
import glob
import subprocess
import xml.etree.ElementTree as ET

LOG_FILE = "/userdata/system/logs/fast_scraper.log"
STATUS_JSON = "/userdata/system/logs/fast_scraper_status.json"
ES_SYSTEMS_PATH = "/etc/emulationstation/es_systems.cfg"

# Colors
C_RESET  = "\033[0m"
C_BOLD   = "\033[1m"
C_GREEN  = "\033[1;32m"
C_YELLOW = "\033[1;33m"
C_CYAN   = "\033[1;36m"
C_RED    = "\033[1;31m"
C_DIM    = "\033[2m"

def get_running_process():
    try:
        out = subprocess.check_output(["pgrep", "-f", "fast_scraper.py"], universal_newlines=True).strip()
        lines = out.split("\n")
        if lines and lines[0]:
            pid = lines[0].strip()
            cmd = subprocess.check_output(["ps", "-o", "args=", "-p", pid], universal_newlines=True).strip()
            return pid, cmd
    except Exception:
        pass
    return None, None

def get_system_total_games(system_name):
    for base in [f"/media/SHARE_1/{system_name}", f"/userdata/roms/{system_name}"]:
        gl = os.path.join(base, "gamelist.xml")
        if os.path.exists(gl):
            try:
                tree = ET.parse(gl)
                return len(tree.getroot().findall("game"))
            except Exception:
                pass
    return 0

def render_bar(percent, width=32):
    filled = int(width * (percent / 100.0))
    filled = max(0, min(width, filled))
    bar = "█" * filled + "░" * (width - filled)
    return bar

def show_status():
    pid, cmd = get_running_process()
    if not pid:
        print(f"{C_YELLOW}○ Scraper está PARADO{C_RESET}")
        if os.path.exists(LOG_FILE):
            print(f"\n{C_DIM}Últimas linhas do log:{C_RESET}")
            try:
                lines = subprocess.check_output(["tail", "-n", "5", LOG_FILE], universal_newlines=True).strip().split("\n")
                for l in lines:
                    print(f"  {l}")
            except Exception:
                pass
        print(f"\nPara iniciar o scraper: {C_GREEN}fast-scraper start{C_RESET}\n")
        return

    print(f"{C_BOLD}{C_GREEN}● Scraper está RODANDO{C_RESET} {C_DIM}(PID: {pid}){C_RESET}")

    system_name = None
    processed = 0
    total = 0
    pct = 0.0
    last_game = None

    # 1. Try reading status.json
    if os.path.exists(STATUS_JSON):
        try:
            with open(STATUS_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("pid") == int(pid) or str(data.get("pid")) == pid:
                    system_name = data.get("system")
                    processed = data.get("processed", 0)
                    total = data.get("total", 0)
                    pct = data.get("percent", 0.0)
                    last_game = data.get("last_game")
        except Exception:
            pass

    # 2. Fallback: Parse from cmd and log file
    if not system_name or total == 0:
        parts = cmd.split()
        for p in parts[2:]:
            if not p.startswith("-"):
                system_name = p
                break
        if not system_name and os.path.exists(LOG_FILE):
            try:
                last_line = subprocess.check_output(["tail", "-n", "1", LOG_FILE], universal_newlines=True).strip()
                import re
                m = re.search(r"\[([a-zA-Z0-9_\-]+)\]", last_line)
                if m:
                    system_name = m.group(1)
            except Exception:
                pass

        if system_name:
            total = get_system_total_games(system_name)
            try:
                out = subprocess.check_output(f"grep -c '\\[{system_name}\\]' {LOG_FILE}", shell=True, universal_newlines=True).strip()
                processed = int(out)
                pct = (processed / total * 100) if total > 0 else 0
            except Exception:
                processed = 0

    if system_name:
        remaining = max(0, total - processed) if total > 0 else 0
        bar = render_bar(pct, width=32)
        print(f"  {C_BOLD}Plataforma atual:{C_RESET} {C_CYAN}{system_name.upper()}{C_RESET}")
        print(f"  {C_BOLD}Progresso:{C_RESET}        [{C_GREEN}{bar}{C_RESET}] {C_BOLD}{pct:4.1f}%{C_RESET} ({processed}/{total} jogos)")
        print(f"  {C_BOLD}Faltam:{C_RESET}           {C_YELLOW}{remaining} mídias{C_RESET} para concluir este sistema")
        if last_game:
            print(f"  {C_BOLD}Último jogo:{C_RESET}     {last_game}")
    else:
        print(f"  Comando: {cmd}")

    print(f"\n{C_BOLD}Últimas atividades do log:{C_RESET}")
    if os.path.exists(LOG_FILE):
        try:
            lines = subprocess.check_output(["tail", "-n", "6", LOG_FILE], universal_newlines=True).strip().split("\n")
            for l in lines:
                print(f"  {l}")
        except Exception:
            pass

    print(f"\n{C_DIM}Acompanhe ao vivo com: {C_GREEN}fast-scraper log{C_RESET}\n")

if __name__ == "__main__":
    show_status()
