#!/bin/bash
# ==============================================================================
#  Batocera Fast Scraper - Uninstaller
# ==============================================================================
set -e

INSTALL_DIR="/userdata/system/tools/batocera-fast-scraper"
CUSTOM_SH="/userdata/system/custom.sh"
PROFILE_SH="/userdata/system/.profile"

# ANSI Colors
C_RESET="\033[0m"
C_BOLD="\033[1m"
C_GREEN="\033[1;32m"
C_YELLOW="\033[1;33m"
C_CYAN="\033[1;36m"
C_RED="\033[1;31m"

echo -e "\n${C_BOLD}${C_YELLOW}Desinstalador do Batocera Fast Scraper${C_RESET}\n"

# 1. Parar qualquer processo rodando
if pgrep -f "fast_scraper.py" >/dev/null 2>&1; then
    echo "Parando processos ativos do scraper..."
    pkill -9 -f "fast_scraper.py" || true
fi

# 2. Remover links simbólicos
echo "Removendo atalhos do sistema..."
rm -f /usr/bin/fast-scraper /usr/bin/list-systems /usr/bin/clean-media /usr/bin/clean-orphans

# 3. Remover persistência no custom.sh
if [ -f "$CUSTOM_SH" ]; then
    sed -i '/# --- Batocera Fast Scraper Hooks ---/,+4d' "$CUSTOM_SH" 2>/dev/null || true
fi

# 4. Remover do .profile
if [ -f "$PROFILE_SH" ]; then
    sed -i '/batocera-fast-scraper/d' "$PROFILE_SH" 2>/dev/null || true
fi

# 5. Remover pasta de instalação
if [ -d "$INSTALL_DIR" ]; then
    echo "Removendo arquivos do programa ($INSTALL_DIR)..."
    rm -rf "$INSTALL_DIR"
fi

echo -e "\n${C_GREEN}✓ Batocera Fast Scraper foi completamente desinstalado.${C_RESET}\n"
