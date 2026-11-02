#!/bin/bash
# ==============================================================================
#  Batocera Fast Scraper - One-Line Installer
# ==============================================================================
set -e

REPO_USER="eloparedes" # Default repository owner
REPO_NAME="batocera-fast-scraper"
GITHUB_USER="${GITHUB_USER:-$REPO_USER}"
TARBALL_URL="https://github.com/${GITHUB_USER}/${REPO_NAME}/archive/refs/heads/main.tar.gz"

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
C_DIM="\033[2m"

echo -e "\n${C_BOLD}${C_CYAN}================================================================================${C_RESET}"
echo -e "${C_BOLD}${C_CYAN}         Instalador do Batocera Fast Scraper (Versão Inteligente)             ${C_RESET}"
echo -e "${C_BOLD}${C_CYAN}================================================================================${C_RESET}\n"

# 1. Verificar ambiente Batocera
if [ ! -d "/userdata" ]; then
    echo -e "${C_RED}[ERRO] Este instalador foi desenvolvido para o Batocera Linux (/userdata não encontrado).${C_RESET}"
    exit 1
fi

# 2. Criar diretório de instalação
echo -e "${C_CYAN}[1/4]${C_RESET} Preparando diretório de instalação..."
mkdir -p "/userdata/system/tools"
mkdir -p "/userdata/system/logs"

# 3. Baixar ou copiar arquivos
SCRIPT_DIR=""
if [ -f "$0" ] && [ -d "$(dirname "$0")/src" ]; then
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
fi

if [ -n "$SCRIPT_DIR" ] && [ "$SCRIPT_DIR" != "$INSTALL_DIR" ]; then
    echo -e "${C_CYAN}[2/4]${C_RESET} Instalando a partir dos arquivos locais..."
    mkdir -p "$INSTALL_DIR"
    cp -r "$SCRIPT_DIR/bin" "$INSTALL_DIR/"
    cp -r "$SCRIPT_DIR/src" "$INSTALL_DIR/"
    [ -f "$SCRIPT_DIR/README.md" ] && cp "$SCRIPT_DIR/README.md" "$INSTALL_DIR/"
    [ -f "$SCRIPT_DIR/LICENSE" ] && cp "$SCRIPT_DIR/LICENSE" "$INSTALL_DIR/"
else
    echo -e "${C_CYAN}[2/4]${C_RESET} Baixando versão mais recente do GitHub (${GITHUB_USER}/${REPO_NAME})..."
    TEMP_DIR="/tmp/fast_scraper_install_$$"
    mkdir -p "$TEMP_DIR"
    if curl -sSL "$TARBALL_URL" | tar -xz -C "$TEMP_DIR" 2>/dev/null; then
        EXTRACTED_DIR=$(find "$TEMP_DIR" -maxdepth 1 -type d -name "${REPO_NAME}*" | head -n 1)
        if [ -d "$EXTRACTED_DIR" ]; then
            mkdir -p "$INSTALL_DIR"
            cp -r "$EXTRACTED_DIR/bin" "$INSTALL_DIR/"
            cp -r "$EXTRACTED_DIR/src" "$INSTALL_DIR/"
            [ -f "$EXTRACTED_DIR/README.md" ] && cp "$EXTRACTED_DIR/README.md" "$INSTALL_DIR/"
            [ -f "$EXTRACTED_DIR/LICENSE" ] && cp "$EXTRACTED_DIR/LICENSE" "$INSTALL_DIR/"
            rm -rf "$TEMP_DIR"
        else
            echo -e "${C_RED}[ERRO] Não foi possível extrair o pacote de instalação.${C_RESET}"
            rm -rf "$TEMP_DIR"
            exit 1
        fi
    else
        echo -e "${C_RED}[ERRO] Falha ao baixar pacote do GitHub: $TARBALL_URL${C_RESET}"
        rm -rf "$TEMP_DIR"
        exit 1
    fi
fi

# 4. Configurar permissões de execução
echo -e "${C_CYAN}[3/4]${C_RESET} Configurando permissões..."
chmod +x "$INSTALL_DIR/bin/fast-scraper"
chmod +x "$INSTALL_DIR/src/"*.py

# 5. Criar links simbólicos no PATH (/usr/bin)
ln -sf "$INSTALL_DIR/bin/fast-scraper" /usr/bin/fast-scraper
ln -sf "$INSTALL_DIR/src/list_systems.py" /usr/bin/list-systems
ln -sf "$INSTALL_DIR/src/clean_media.py" /usr/bin/clean-media
ln -sf "$INSTALL_DIR/src/clean_orphans.py" /usr/bin/clean-orphans

# 6. Garantir persistência após reboots do Batocera (/userdata/system/custom.sh e .profile)
echo -e "${C_CYAN}[4/5]${C_RESET} Configurando persistência permanente de boot..."

# Configurar custom.sh (executado a cada boot do Batocera)
HOOK_MARKER="# --- Batocera Fast Scraper Hooks ---"
if ! grep -q "$HOOK_MARKER" "$CUSTOM_SH" 2>/dev/null; then
    mkdir -p "$(dirname "$CUSTOM_SH")"
    cat << 'EOF' >> "$CUSTOM_SH"

# --- Batocera Fast Scraper Hooks ---
ln -sf /userdata/system/tools/batocera-fast-scraper/bin/fast-scraper /usr/bin/fast-scraper 2>/dev/null
ln -sf /userdata/system/tools/batocera-fast-scraper/src/list_systems.py /usr/bin/list-systems 2>/dev/null
ln -sf /userdata/system/tools/batocera-fast-scraper/src/clean_media.py /usr/bin/clean-media 2>/dev/null
ln -sf /userdata/system/tools/batocera-fast-scraper/src/clean_orphans.py /usr/bin/clean-orphans 2>/dev/null
EOF
    chmod +x "$CUSTOM_SH"
fi

# Configurar .profile (para sessões de terminal interativas)
if ! grep -q "batocera-fast-scraper/bin" "$PROFILE_SH" 2>/dev/null; then
    echo 'export PATH="/userdata/system/tools/batocera-fast-scraper/bin:$PATH"' >> "$PROFILE_SH"
fi

# 7. Verificar/Configurar credenciais do ScreenScraper
echo -e "${C_CYAN}[5/5]${C_RESET} Verificando credenciais do ScreenScraper..."
ES_SETTINGS="/userdata/system/configs/emulationstation/es_settings.cfg"
FAST_CONFIG_DIR="/userdata/system/configs/fast_scraper"
FAST_CONFIG_FILE="$FAST_CONFIG_DIR/config.json"
mkdir -p "$FAST_CONFIG_DIR"

if [ ! -f "$FAST_CONFIG_FILE" ]; then
    DETECTED_USER=""
    DETECTED_PASS=""
    if [ -f "$ES_SETTINGS" ]; then
        DETECTED_USER=$(grep 'name="ScreenScraperUser"' "$ES_SETTINGS" | sed -n 's/.*value="\([^"]*\)".*/\1/p')
        DETECTED_PASS=$(grep 'name="ScreenScraperPass"' "$ES_SETTINGS" | sed -n 's/.*value="\([^"]*\)".*/\1/p')
    fi

    if [ -n "$DETECTED_USER" ] && [ -n "$DETECTED_PASS" ]; then
        echo -e "${C_GREEN}✓ Credenciais do ScreenScraper detectadas automaticamente do Batocera (Usuário: ${C_BOLD}$DETECTED_USER${C_GREEN})!${C_RESET}"
        cat << EOF > "$FAST_CONFIG_FILE"
{
    "ssid": "$DETECTED_USER",
    "sspassword": "$DETECTED_PASS"
}
EOF
        chmod 600 "$FAST_CONFIG_FILE"
    else
        echo -e "${C_YELLOW}Dica: Você pode cadastrar ou alterar sua conta do ScreenScraper com: ${C_BOLD}fast-scraper config${C_RESET}"
    fi
else
    echo -e "${C_GREEN}✓ Arquivo de configuração de credenciais já existente.${C_RESET}"
fi

echo -e "\n${C_BOLD}${C_GREEN}================================================================================${C_RESET}"
echo -e "${C_BOLD}${C_GREEN}     ✓ FAST-SCRAPER INSTALADO COM SUCESSO NO SEU BATOCERA!                    ${C_RESET}"
echo -e "${C_BOLD}${C_GREEN}================================================================================${C_RESET}\n"

echo -e "Você já pode usar os seguintes comandos de qualquer lugar do terminal:"
echo -e "  ${C_CYAN}fast-scraper list${C_RESET}          -> Ver raio-x das plataformas e status de mídias"
echo -e "  ${C_CYAN}fast-scraper status${C_RESET}        -> Ver progresso com barra visual e contador regressivo"
echo -e "  ${C_CYAN}fast-scraper start${C_RESET}         -> Iniciar o download automático com Smart Resume"
echo -e "  ${C_CYAN}fast-scraper clean-orphans${C_RESET} -> Encontrar e apagar mídias órfãs (sem jogos)"
echo -e "  ${C_CYAN}fast-scraper --help${C_RESET}        -> Ver manual completo com exemplos práticos\n"
