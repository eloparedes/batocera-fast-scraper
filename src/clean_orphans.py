#!/usr/bin/env python3
"""
Clean Orphaned Media and Gamelist Entries in Batocera.
Identifies and removes media files (images, videos, marquees) that do not belong to any existing game ROM.
Also optionally cleans dead gamelist.xml entries where the ROM file no longer exists.
"""
import os
import sys
import glob
import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom

ES_SYSTEMS_PATH = "/etc/emulationstation/es_systems.cfg"

# Colors
C_RESET  = "\033[0m"
C_BOLD   = "\033[1m"
C_GREEN  = "\033[1;32m"
C_YELLOW = "\033[1;33m"
C_CYAN   = "\033[1;36m"
C_RED    = "\033[1;31m"
C_DIM    = "\033[2m"

KNOWN_MEDIA_SUFFIXES = [
    "-image", "-thumb", "-marquee", "-video", "-fanart", "-wheel",
    "-boxart", "-cartridge", "-map", "-titlescreen", "-snap", "-manual"
]

def format_size(bytes_size):
    if bytes_size >= 1024 ** 3:
        return f"{bytes_size / (1024 ** 3):.2f} GB"
    elif bytes_size >= 1024 ** 2:
        return f"{bytes_size / (1024 ** 2):.1f} MB"
    elif bytes_size >= 1024:
        return f"{bytes_size / 1024:.1f} KB"
    return f"{bytes_size} B"

def get_system_dir(system_name):
    # 1. /media/SHARE_1
    p1 = f"/media/SHARE_1/{system_name}"
    if os.path.exists(p1):
        return os.path.realpath(p1)
    
    # 2. /userdata/roms
    p2 = f"/userdata/roms/{system_name}"
    if os.path.exists(p2):
        return os.path.realpath(p2)

    # 3. es_systems.cfg
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

def get_all_systems():
    if not os.path.exists(ES_SYSTEMS_PATH):
        return []
    try:
        tree = ET.parse(ES_SYSTEMS_PATH)
        systems = []
        for s in tree.getroot().findall("system"):
            n = s.find("name")
            p = s.find("path")
            if n is not None and n.text and p is not None and p.text:
                rp = os.path.realpath(p.text.strip())
                if os.path.exists(rp):
                    systems.append((n.text.strip().lower(), rp))
        return systems
    except Exception:
        return []

def strip_media_suffix(filename):
    base_no_ext, _ = os.path.splitext(filename)
    lower_base = base_no_ext.lower()
    for suff in KNOWN_MEDIA_SUFFIXES:
        if lower_base.endswith(suff):
            return base_no_ext[:-len(suff)]
    return base_no_ext

def scan_system_orphans(sname, sdir):
    if not os.path.exists(sdir):
        return None

    # 1. Find all actual ROMs on disk
    rom_bases = set()
    rom_files = set()
    for root, dirs, files in os.walk(sdir):
        for ignored in ("images", "videos", "manuals", ".git"):
            if ignored in dirs:
                dirs.remove(ignored)
        for f in files:
            if f.startswith(".") or f == "gamelist.xml":
                continue
            rom_files.add(f.lower())
            base = os.path.splitext(f)[0].lower()
            rom_bases.add(base)

    gl_path = os.path.join(sdir, "gamelist.xml")
    dead_game_elems = []
    referenced_media_paths = set()
    root_xml = None

    if os.path.exists(gl_path):
        try:
            tree = ET.parse(gl_path)
            root_xml = tree.getroot()
            for g in root_xml.findall("game"):
                p_el = g.find("path")
                if p_el is not None and p_el.text:
                    raw_rel = p_el.text.strip()
                    clean_rel = raw_rel.lstrip("./")
                    full_p = os.path.join(sdir, clean_rel)
                    if not os.path.exists(full_p):
                        dead_game_elems.append(g)
                    else:
                        for tag in ("image", "thumbnail", "marquee", "video"):
                            m_el = g.find(tag)
                            if m_el is not None and m_el.text:
                                clean_m = m_el.text.strip().lstrip("./")
                                referenced_media_paths.add(clean_m.lower())
                                referenced_media_paths.add(os.path.basename(clean_m).lower())
        except Exception:
            pass

    # 2. Find orphaned media files in images/, videos/, manuals/
    orphan_files = []
    orphan_bytes = 0

    for sub in ("images", "videos", "manuals"):
        mdir = os.path.join(sdir, sub)
        if not os.path.isdir(mdir):
            continue

        for mf in os.listdir(mdir):
            if mf.startswith("."):
                continue
            fp = os.path.join(mdir, mf)
            if not os.path.isfile(fp):
                continue

            mf_lower = mf.lower()
            if mf_lower in referenced_media_paths:
                continue

            clean_base = strip_media_suffix(mf).lower()
            if clean_base in rom_bases:
                continue

            if clean_base in rom_files:
                continue

            sz = os.path.getsize(fp)
            orphan_files.append((fp, sz))
            orphan_bytes += sz

    return {
        "name": sname,
        "dir": sdir,
        "rom_count": len(rom_bases),
        "orphan_files": orphan_files,
        "orphan_bytes": orphan_bytes,
        "dead_games": dead_game_elems,
        "root_xml": root_xml,
        "gl_path": gl_path
    }

def clean_orphans(target_systems, force=False, dry_run=False):
    results = []
    for sname, sdir in target_systems:
        res = scan_system_orphans(sname, sdir)
        if res and (len(res["orphan_files"]) > 0 or len(res["dead_games"]) > 0):
            results.append(res)

    total_orphans = sum(len(r["orphan_files"]) for r in results)
    total_bytes = sum(r["orphan_bytes"] for r in results)
    total_dead_games = sum(len(r["dead_games"]) for r in results)

    sep = "=" * 80
    print(f"\n{C_BOLD}{sep}{C_RESET}")
    print(f"{C_CYAN}  VERIFICAÇÃO DE MÍDIAS E REGISTROS ÓRFÃOS NO BATOCERA{C_RESET}")
    print(f"{C_BOLD}{sep}{C_RESET}")

    if not results:
        print(f"{C_GREEN}✓ Nenhuma mídia órfã encontrada! Sua biblioteca está 100% limpa.{C_RESET}\n")
        return

    print(f"{'PLATAFORMA':<15} | {'ROMS ATIVAS':>11} | {'MÍDIAS ÓRFÃS':>12} | {'ESPAÇO OCUPADO':>14} | {'JOGOS INEXISTENTES NO XML':>25}")
    print(f"{C_DIM}{'-'*85}{C_RESET}")

    for r in results:
        orf_cnt = len(r["orphan_files"])
        dead_cnt = len(r["dead_games"])
        print(f"{r['name']:<15} | {r['rom_count']:>11} | {orf_cnt:>12} | {format_size(r['orphan_bytes']):>14} | {dead_cnt:>25}")

    print(f"{C_DIM}{'-'*85}{C_RESET}")
    print(f"{C_BOLD}{'TOTAL':<15} | {'':<11} | {total_orphans:>12} | {format_size(total_bytes):>14} | {total_dead_games:>25}{C_RESET}")
    print(f"{C_BOLD}{sep}{C_RESET}\n")

    if dry_run:
        print(f"{C_CYAN}[DRY-RUN] Modo de simulação: nenhum arquivo foi excluído.{C_RESET}")
        print(f"Para executar a limpeza real, execute sem a flag --dry-run.\n")
        return

    if not force:
        try:
            confirm = input(f"{C_RED}Deseja apagar definitivamente essas {total_orphans} mídias órfãs ({format_size(total_bytes)})? (s/N): {C_RESET}").strip().lower()
            if confirm not in ("s", "sim", "y", "yes"):
                print("Operação cancelada pelo usuário.\n")
                return
        except EOFError:
            print("Execução não interativa sem flag --force / -y. Abortando por segurança.\n")
            return

    # Deletion process
    deleted_count = 0
    for r in results:
        for fp, _ in r["orphan_files"]:
            try:
                if os.path.isfile(fp) or os.path.islink(fp):
                    os.unlink(fp)
                    deleted_count += 1
            except Exception as e:
                print(f"Erro ao apagar {fp}: {e}")

        if r["dead_games"] and r["root_xml"] is not None and os.path.exists(r["gl_path"]):
            try:
                for dg in r["dead_games"]:
                    r["root_xml"].remove(dg)
                rough_string = ET.tostring(r["root_xml"], 'utf-8')
                reparsed = minidom.parseString(rough_string)
                clean_xml = '\n'.join([line for line in reparsed.toprettyxml(indent='\t').split('\n') if line.strip()])
                with open(r["gl_path"], 'w', encoding='utf-8') as f:
                    f.write(clean_xml)
            except Exception as e:
                print(f"Erro ao salvar gamelist {r['gl_path']}: {e}")

    try:
        requests.get('http://localhost:1234/reloadgames', timeout=3)
    except Exception:
        pass

    print(f"\n{C_BOLD}{C_GREEN}✓ Limpeza concluída com sucesso!{C_RESET}")
    print(f"Arquivos órfãos excluídos: {C_GREEN}{deleted_count}{C_RESET}")
    print(f"Espaço total liberado em disco: {C_GREEN}{format_size(total_bytes)}{C_RESET}\n")

def main():
    args = sys.argv[1:]
    if args and args[0] in ("-h", "--help", "help"):
        print("Uso: clean_orphans.py [sistema | --all] [--force | -y] [--dry-run | -d]")
        print("")
        print("Opções:")
        print("  <sistema>        Limpa órfãos de um sistema específico (ex: mame, snes, fbneo)")
        print("  --all            (Padrão se nenhum sistema for passado) Verifica e limpa todos os sistemas")
        print("  --dry-run, -d    Apenas simula a limpeza e mostra os arquivos/tamanho a liberar")
        print("  --force, -y      Não pede confirmação interativa antes de apagar")
        sys.exit(0)

    dry_run = "--dry-run" in args or "-d" in args
    force = "--force" in args or "-y" in args or "-f" in args
    sys_args = [a for a in args if not a.startswith("-")]

    targets = []
    if sys_args:
        for sname in sys_args:
            sdir = get_system_dir(sname)
            if sdir:
                targets.append((sname, sdir))
            else:
                print(f"{C_RED}Aviso: Sistema '{sname}' não encontrado.{C_RESET}")
    else:
        targets = get_all_systems()

    if not targets:
        print("Nenhum sistema válido selecionado.")
        return

    clean_orphans(targets, force=force, dry_run=dry_run)

if __name__ == "__main__":
    main()
