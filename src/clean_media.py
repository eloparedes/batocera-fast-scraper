#!/usr/bin/env python3
"""
Clean/Wipe media assets for Batocera systems safely.
Allows removing images, videos, or both, while updating gamelist.xml and preserving ROMs.
"""
import os
import sys
import glob
import shutil
import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom

ES_SYSTEMS_PATH = "/etc/emulationstation/es_systems.cfg"

C_RESET  = "\033[0m"
C_BOLD   = "\033[1m"
C_GREEN  = "\033[1;32m"
C_YELLOW = "\033[1;33m"
C_CYAN   = "\033[1;36m"
C_RED    = "\033[1;31m"

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

def get_dir_size_and_count(dir_path):
    if not os.path.exists(dir_path):
        return 0, 0
    total_size = 0
    total_files = 0
    for root, _, files in os.walk(dir_path):
        for f in files:
            fp = os.path.join(root, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
                total_files += 1
    return total_files, total_size

def format_size(bytes_size):
    if bytes_size >= 1024 ** 3:
        return f"{bytes_size / (1024 ** 3):.2f} GB"
    elif bytes_size >= 1024 ** 2:
        return f"{bytes_size / (1024 ** 2):.1f} MB"
    elif bytes_size >= 1024:
        return f"{bytes_size / 1024:.1f} KB"
    return f"{bytes_size} B"

def clean_system(system_name, mode="all", force=False, dry_run=False):
    sdir = get_system_dir(system_name)
    if not sdir or not os.path.exists(sdir):
        print(f"{C_RED}Erro: Diretório para o sistema '{system_name}' não foi encontrado.{C_RESET}")
        return False

    clean_images = mode in ("all", "images")
    clean_videos = mode in ("all", "videos")

    img_dir = os.path.join(sdir, "images")
    vid_dir = os.path.join(sdir, "videos")
    gl_path = os.path.join(sdir, "gamelist.xml")

    img_count, img_size = get_dir_size_and_count(img_dir) if clean_images else (0, 0)
    vid_count, vid_size = get_dir_size_and_count(vid_dir) if clean_videos else (0, 0)
    total_count = img_count + vid_count
    total_size = img_size + vid_size

    print(f"\n{C_BOLD}Sistema:{C_RESET} {C_CYAN}{system_name.upper()}{C_RESET} ({sdir})")
    print(f"Modo de limpeza: {C_YELLOW}{mode.upper()}{C_RESET}")
    if clean_images:
        print(f" - Imagens encontradas: {img_count} arquivos ({format_size(img_size)})")
    if clean_videos:
        print(f" - Vídeos encontrados:  {vid_count} arquivos ({format_size(vid_size)})")
    print(f"{C_BOLD}Total a liberar:{C_RESET} {C_GREEN}{format_size(total_size)}{C_RESET} ({total_count} arquivos)")

    if total_count == 0:
        print(f"{C_YELLOW}Nenhuma mídia encontrada para limpar neste modo.{C_RESET}\n")
        return True

    if dry_run:
        print(f"\n{C_CYAN}[DRY-RUN] Nenhuma alteração foi feita no disco.{C_RESET}\n")
        return True

    if not force:
        try:
            confirm = input(f"\n{C_RED}Tem certeza que deseja apagar permanentemente essas mídias? (s/N): {C_RESET}").strip().lower()
            if confirm not in ("s", "sim", "y", "yes"):
                print("Operação cancelada pelo usuário.")
                return False
        except EOFError:
            print("Execução não-interativa detectada sem flag --force / -y. Abortando por segurança.")
            return False

    # 1. Apagar arquivos físicos
    deleted_files = 0
    if clean_images and os.path.exists(img_dir):
        for f in os.listdir(img_dir):
            fp = os.path.join(img_dir, f)
            try:
                if os.path.isfile(fp) or os.path.islink(fp):
                    os.unlink(fp)
                    deleted_files += 1
            except Exception as e:
                print(f"Erro ao apagar {fp}: {e}")

    if clean_videos and os.path.exists(vid_dir):
        for f in os.listdir(vid_dir):
            fp = os.path.join(vid_dir, f)
            try:
                if os.path.isfile(fp) or os.path.islink(fp):
                    os.unlink(fp)
                    deleted_files += 1
            except Exception as e:
                print(f"Erro ao apagar {fp}: {e}")

    # 2. Atualizar gamelist.xml removendo as tags de mídia
    if os.path.exists(gl_path):
        try:
            tree = ET.parse(gl_path)
            root = tree.getroot()
            tags_to_remove = []
            if clean_images:
                tags_to_remove.extend(["image", "thumbnail", "marquee"])
            if clean_videos:
                tags_to_remove.extend(["video"])

            changed = False
            for g in root.findall("game"):
                for tag in tags_to_remove:
                    el = g.find(tag)
                    if el is not None:
                        g.remove(el)
                        changed = True

            if changed:
                rough_string = ET.tostring(root, 'utf-8')
                reparsed = minidom.parseString(rough_string)
                clean_xml = '\n'.join([line for line in reparsed.toprettyxml(indent='\t').split('\n') if line.strip()])
                with open(gl_path, 'w', encoding='utf-8') as f:
                    f.write(clean_xml)
                print(f"{C_GREEN}✓ gamelist.xml atualizado com sucesso (tags de mídia removidas).{C_RESET}")
        except Exception as e:
            print(f"{C_RED}Aviso ao atualizar gamelist.xml: {e}{C_RESET}")

    # 3. Notificar EmulationStation
    try:
        requests.get('http://localhost:1234/reloadgames', timeout=3)
        print(f"{C_GREEN}✓ EmulationStation recarregado.{C_RESET}")
    except Exception:
        pass

    print(f"\n{C_BOLD}{C_GREEN}Limpeza concluída com sucesso!{C_RESET}")
    print(f"Espaço liberado: {C_GREEN}{format_size(total_size)}{C_RESET} ({deleted_files} arquivos removidos)\n")
    return True

def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print("Uso: clean_media.py <sistema> [--all | --videos | --images] [--force | -y] [--dry-run]")
        print("")
        print("Opções:")
        print("  <sistema>     Nome do sistema (ex: snes, mastersystem, gba, mame)")
        print("  --all         (Padrão) Remove imagens e vídeos do sistema")
        print("  --videos      Remove apenas os vídeos (-video.mp4)")
        print("  --images      Remove apenas as imagens (-image.png, -thumb.png, -marquee.png)")
        print("  --force, -y   Não pede confirmação interativa")
        print("  --dry-run     Apenas calcula o espaço e lista os arquivos sem apagar")
        sys.exit(0)

    system_name = args[0]
    mode = "all"
    force = False
    dry_run = False

    for opt in args[1:]:
        if opt in ("--all", "all"):
            mode = "all"
        elif opt in ("--videos", "videos", "-v"):
            mode = "videos"
        elif opt in ("--images", "images", "-i"):
            mode = "images"
        elif opt in ("--force", "-y", "-f"):
            force = True
        elif opt in ("--dry-run", "-d"):
            dry_run = True

    clean_system(system_name, mode=mode, force=force, dry_run=dry_run)

if __name__ == "__main__":
    main()
