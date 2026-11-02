#!/usr/bin/env python3
"""
ScreenScraper Configuration Manager for Batocera Fast Scraper.
Allows viewing, updating, and verifying ScreenScraper account credentials.
"""
import os
import sys
import json
import getpass
import requests
import xml.etree.ElementTree as ET

CONFIG_DIR = "/userdata/system/configs/fast_scraper"
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
ES_SETTINGS_XML = "/userdata/system/configs/emulationstation/es_settings.cfg"
BATOCERA_CONF = "/userdata/system/batocera.conf"

# Colors
C_RESET  = "\033[0m"
C_BOLD   = "\033[1m"
C_GREEN  = "\033[1;32m"
C_YELLOW = "\033[1;33m"
C_CYAN   = "\033[1;36m"
C_RED    = "\033[1;31m"
C_DIM    = "\033[2m"

def get_dev_credentials():
    try:
        r = requests.get('https://retrogamesets.fr/rgsx/manager/rgsx_screenscraper_credentials_api.php', timeout=8)
        data = r.json()
        return data.get('devid', ''), data.get('devpassword', '')
    except Exception:
        return "", ""

def load_credentials():
    ss_user = ""
    ss_pass = ""
    source = "Nenhum"

    # 1. Config file
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                ss_user = d.get("ssid", "") or d.get("user", "")
                ss_pass = d.get("sspassword", "") or d.get("password", "")
                if ss_user:
                    source = "Arquivo de configuração (fast_scraper/config.json)"
        except Exception:
            pass

    # 2. EmulationStation settings.cfg
    if not ss_user and os.path.exists(ES_SETTINGS_XML):
        try:
            tree = ET.parse(ES_SETTINGS_XML)
            for s in tree.getroot().findall("string"):
                if s.get("name") == "ScreenScraperUser":
                    ss_user = s.get("value", "")
                elif s.get("name") == "ScreenScraperPass":
                    ss_pass = s.get("value", "")
            if ss_user:
                source = "Configurações nativas do Batocera (es_settings.cfg)"
        except Exception:
            pass

    # 3. batocera.conf
    if not ss_user and os.path.exists(BATOCERA_CONF):
        try:
            with open(BATOCERA_CONF, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("scrapper.user="):
                        ss_user = line.split("=", 1)[1].strip()
                    elif line.startswith("scrapper.password="):
                        ss_pass = line.split("=", 1)[1].strip()
            if ss_user:
                source = "batocera.conf"
        except Exception:
            pass

    return ss_user, ss_pass, source

def save_credentials(user, password):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    data = {
        "ssid": user.strip(),
        "sspassword": password.strip()
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    os.chmod(CONFIG_FILE, 0o600)

def test_credentials(user, password):
    devid, devpass = get_dev_credentials()
    if not devid:
        print(f"{C_YELLOW}Não foi possível conectar ao serviço de validação. Ignorando teste.{C_RESET}")
        return True

    params = {
        "devid": devid,
        "devpassword": devpass,
        "softname": "RGSX",
        "output": "json",
        "ssid": user,
        "sspassword": password
    }
    try:
        r = requests.get("https://api.screenscraper.fr/api2/ssuserInfos.php", params=params, timeout=10)
        if r.status_code == 200:
            data = r.json().get("response", {}).get("ssuser", {})
            max_threads = data.get("maxthreads", "1")
            quota_dia = data.get("requeststoday", "0")
            limite = data.get("maxrequestsperday", "Desconhecido")
            print(f"{C_GREEN}✓ Credenciais validadas com sucesso no ScreenScraper!{C_RESET}")
            print(f"  Usuário: {C_BOLD}{data.get('id', user)}{C_RESET}")
            print(f"  Nível da conta: {C_CYAN}{data.get('niveau', 'Normal')}{C_RESET}")
            print(f"  Threads permitidas: {C_BOLD}{max_threads}{C_RESET}")
            print(f"  Requisições hoje: {quota_dia} / {limite}")
            return True
        elif r.status_code == 401 or "identification" in r.text.lower():
            print(f"{C_RED}✗ Usuário ou senha incorretos no ScreenScraper.{C_RESET}")
            return False
        else:
            print(f"{C_YELLOW}Aviso: Resposta da API ({r.status_code}). Credenciais salvas mesmo assim.{C_RESET}")
            return True
    except Exception as e:
        print(f"{C_YELLOW}Aviso: Falha ao testar conexão ({e}). Credenciais salvas.{C_RESET}")
        return True

def main():
    args = sys.argv[1:]
    current_user, current_pass, source = load_credentials()

    if "--set" in args:
        # Scripted format: --set <user> <pass>
        idx = args.index("--set")
        if len(args) > idx + 2:
            new_u = args[idx + 1]
            new_p = args[idx + 2]
            save_credentials(new_u, new_p)
            print(f"{C_GREEN}Credenciais salvas com sucesso.{C_RESET}")
            return
        else:
            print("Uso: manage_config.py --set <usuario> <senha>")
            return

    sep = "=" * 80
    print(f"\n{C_BOLD}{sep}{C_RESET}")
    print(f"{C_CYAN}         CONFIGURAÇÃO DE CONTA DO SCREENSCRAPER         {C_RESET}")
    print(f"{C_BOLD}{sep}{C_RESET}\n")

    if current_user:
        masked = current_pass[:2] + ("*" * (max(0, len(current_pass) - 3))) + current_pass[-1:] if len(current_pass) >= 4 else "****"
        print(f"Usuário atual: {C_BOLD}{C_GREEN}{current_user}{C_RESET}")
        print(f"Senha atual:   {C_DIM}{masked}{C_RESET}")
        print(f"Origem:        {C_CYAN}{source}{C_RESET}\n")
    else:
        print(f"{C_YELLOW}Nenhuma conta do ScreenScraper configurada atualmente.{C_RESET}")
        print(f"{C_DIM}(O scraper pode operar em modo anônimo, mas ter uma conta gratuita garante downloads mais rápidos e maior cota diária).{C_RESET}\n")

    try:
        prompt = "Deseja alterar ou cadastrar novas credenciais? (s/N): " if current_user else "Deseja cadastrar uma conta agora? (S/n): "
        resp = input(prompt).strip().lower()
        if current_user and resp not in ("s", "sim", "y", "yes"):
            print("Nenhuma alteração foi feita.\n")
            return
        elif not current_user and resp in ("n", "nao", "não", "no"):
            print("Operação cancelada.\n")
            return

        new_user = input("\nDigite seu usuário do ScreenScraper: ").strip()
        if not new_user:
            print(f"{C_RED}Usuário não pode ser vazio. Cancelado.{C_RESET}\n")
            return

        new_pass = getpass.getpass("Digite sua senha do ScreenScraper: ").strip()
        if not new_pass:
            print(f"{C_RED}Senha não pode ser vazia. Cancelado.{C_RESET}\n")
            return

        print("\nTestando credenciais com o servidor do ScreenScraper...")
        if test_credentials(new_user, new_pass):
            save_credentials(new_user, new_pass)
            print(f"{C_BOLD}{C_GREEN}Configuração salva permanentemente em {CONFIG_FILE}!{C_RESET}\n")
        else:
            save_anyway = input("Deseja salvar mesmo assim? (s/N): ").strip().lower()
            if save_anyway in ("s", "sim", "y", "yes"):
                save_credentials(new_user, new_pass)
                print(f"{C_GREEN}Credenciais salvas.{C_RESET}\n")
            else:
                print("Operação descartada.\n")

    except (KeyboardInterrupt, EOFError):
        print("\nOperação cancelada.\n")

if __name__ == "__main__":
    main()
