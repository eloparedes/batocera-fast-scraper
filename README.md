# 🚀 Batocera Fast Scraper

[![Batocera Linux](https://img.shields.io/badge/Batocera-v38--v41+-blue.svg)](https://batocera.org)
[![Python](https://img.shields.io/badge/Python-3.x-yellow.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![ScreenScraper API](https://img.shields.io/badge/Powered%20By-ScreenScraper-orange.svg)](https://www.screenscraper.fr)
[![ArcadeDB](https://img.shields.io/badge/Fallback-ArcadeDB%20(Arcade%20Italia)-red.svg)](http://adb.arcadeitalia.net)

> **Gerenciador completo, acelerado e inteligente de mídias para Batocera Linux.**  
> Scraping com 5 threads simultâneas, motor multi-fonte (ScreenScraper + ArcadeDB), barra de progresso visual, retomada inteligente (Smart Resume), detecção automática de plataformas e limpeza de mídias órfãs.

---

## ⚡ Instalação em 1 Comando

No terminal do seu Batocera (via SSH ou terminal F4):

```bash
curl -sSL https://raw.githubusercontent.com/eloparedes/batocera-fast-scraper/main/install.sh | bash
```

> **Nota:** Não precisa compilar nada nem instalar pacotes externos. O script configura automaticamente a persistência em `/userdata/system/custom.sh` para que os comandos continuem funcionando mesmo após reiniciar ou atualizar o Batocera!

Para desinstalar a qualquer momento:
```bash
curl -sSL https://raw.githubusercontent.com/eloparedes/batocera-fast-scraper/main/uninstall.sh | bash
```

---

## 🌟 Principais Recursos

- ⚡ **Alta Velocidade (5 Threads Paralelas):** Faz o download das mídias em paralelo com fila assíncrona ultra rápida.
- 🌐 **Motor Multi-Fonte Inteligente (ScreenScraper + ArcadeDB):**
  - Utiliza o **ScreenScraper** como provedor primário para todos os consoles e computadores.
  - Ativa automaticamente o **ArcadeDB (Arcade Italia)** como fallback para sistemas Arcade (**MAME, Final Burn Neo, Neo-Geo, CPS-1/2/3, Naomi, Atomiswave, Model 2/3**).
  - Garante **100% de vídeos e flyers** mesmo se a sua cota diária do ScreenScraper estourar ou se a ROM não tiver vídeo cadastrado na base principal!
- 🧠 **Smart Resume (Retomada Inteligente):** Antes de iniciar, analisa sua biblioteca e detecta o que já está baixado. **Nunca mais recomeça do zero!** Se você pausar aos 60%, ele reinicia exatamente em 60%.
- 📊 **Barra de Progresso Visual:** O comando `fast-scraper status` renderiza uma barra colorida `[████████░░░░]`, indicando porcentagem, jogos restantes e último download.
- 🖼️ **Kit Completo de Mídias:**
  - **Capas 2D em Alta Resolução:** Prioriza versões brasileiras (Tectoy / Playtronic) e americanas.
  - **Screenshots In-Game:** Salva em `-thumb.png` para visualização dentro do jogo no tema.
  - **Logos & Marquees:** Salva em `-marquee.png` para rodas e cabeçalhos.
  - **Vídeos Snaps:** Salva em `-video.mp4` para prévias animadas.
  - **Sinopse e Metadados:** Sinopse em português, desenvolvedor, distribuidora e nota.
- 🔍 **Detecção Automática:** Ao rodar `fast-scraper start` sem parâmetros, ele varre todas as plataformas instaladas e baixa apenas para aquelas que possuem mídias pendentes.
- 🧹 **Limpeza de Mídias Órfãs (`clean-orphans`):** Identifica arquivos em `images/` e `videos/` que não pertencem a nenhuma ROM existente na pasta, liberando gigabytes de espaço em disco.
- 🛡️ **Proteção de Armazenamento:** Suspende o download de vídeos caso o espaço livre em disco atinja o piso de segurança (22 GB), garantindo estabilidade do sistema.
- 🔄 **Recarregamento Automático:** Dispara a atualização imediata da interface da EmulationStation ao concluir cada plataforma.

---

## 💻 Manual de Uso

### 1. Diagnóstico e Configuração

**Configurar ou testar sua conta do ScreenScraper:**
```bash
fast-scraper config
```
*(O instalador detecta automaticamente se você já logou no ScreenScraper no Batocera, mas você pode usar esse comando para testar conexão, ver seu limite de requisições ou trocar de conta).*

**Ver panorama da biblioteca e cobertura de mídias:**
```bash
fast-scraper list
# ou:
list-systems
```

### 2. Acompanhamento em Tempo Real

Exibe se o scraper está ativo, qual plataforma está sendo processada, barra de progresso e contador regressivo de mídias restantes:
```bash
fast-scraper status
```

Exemplo de visualização:
```text
● Scraper está RODANDO (PID: 26835)
  Plataforma atual: ATARI800
  Progresso:        [██████████████████░░░░░░░░░░░░░░] 57.7% (1665/2887 jogos)
  Faltam:           1222 mídias para concluir este sistema
  Último jogo:      Wizard of Id's Wiztype (1984)(Sierra On-Line)
```

Para acompanhar o download das artes e vídeos ao vivo:
```bash
fast-scraper log
```

---

### 3. Iniciar o Scraper

#### Opção A: Detecção Automática (Recomendado)
Identifica todas as plataformas com jogos que possuem mídias pendentes e processa tudo em fila:
```bash
fast-scraper start
```

#### Opção B: Plataformas Específicas
Para baixar apenas plataformas escolhidas:
```bash
fast-scraper start gba nes snes
```

#### Opção C: Selecionar o Provedor (`--provider`)
Você pode definir de onde as mídias devem ser baixadas:

```bash
# 1. Provedor Auto (Padrão): ScreenScraper primário + ArcadeDB fallback inteligente
fast-scraper start --provider auto

# 2. Provedor ArcadeDB Exclusivo (Ideal para MAME, FBNeo e Neo-Geo):
# Não gasta cota diária do ScreenScraper e garante 100% de vídeos e flyers!
fast-scraper start mame fbneo --provider arcadedb

# 3. Provedor ScreenScraper Exclusivo (modo tradicional):
fast-scraper start snes megadrive --provider screenscraper
```

---

### 4. Limpeza de Mídias Órfãs (Ganha Gigabytes)

Se você removeu ROMs no passado, os vídeos e capas antigos podem ter ficado para trás.

**Simular a limpeza (sem apagar nada):**
```bash
fast-scraper clean-orphans --dry-run
```

**Limpar órfãos de todo o Batocera:**
```bash
fast-scraper clean-orphans
```

**Limpar órfãos apenas de um sistema (ex: MAME):**
```bash
fast-scraper clean-orphans mame
```

---

### 5. Limpeza de Mídias de uma Plataforma

Se quiser limpar as mídias de uma plataforma inteira (as ROMs **nunca** são tocadas):

```bash
# Limpar imagens e vídeos:
fast-scraper clean <sistema>

# Limpar apenas os vídeos (ótimo para recuperar espaço):
fast-scraper clean <sistema> --videos

# Limpar apenas as imagens:
fast-scraper clean <sistema> --images

# Simular antes de apagar:
fast-scraper clean <sistema> --dry-run
```

---

### 6. Controle do Processo

```bash
# Parar o scraper:
fast-scraper stop

# Reiniciar o scraper:
fast-scraper restart

# Ver ajuda completa:
fast-scraper --help
```

---

## 🗂️ Estrutura do Projeto

```text
batocera-fast-scraper/
├── install.sh             # Instalador em 1 linha para Batocera
├── uninstall.sh           # Desinstalador limpo
├── bin/
│   └── fast-scraper       # CLI principal unificado
├── src/
│   ├── fast_scraper.py    # Motor de scraping multi-threaded com Smart Resume
│   ├── list_systems.py    # Inspetor de plataformas e cobertura de mídias
│   ├── clean_media.py     # Limpeza de mídias de plataforma
│   ├── clean_orphans.py   # Detector e limpador de mídias órfãs
│   └── scraper_status.py  # Renderizador da barra de progresso visual
├── README.md              # Documentação oficial
└── LICENSE                # Licença MIT
```

---

## 📄 Licença

Distribuído sob a licença [MIT](LICENSE). Desenvolvido para a comunidade Batocera Linux.
