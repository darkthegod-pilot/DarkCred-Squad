#!/usr/bin/env bash
# ============================================================
#  DarkCred — Deploy / Manage Script
#  Uso: ./deploy.sh [opção]
# ============================================================
set -euo pipefail

# ── Cores ───────────────────────────────────────────────────
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
AMBER='\033[38;5;214m'

ok()   { echo -e "${GREEN}✓${RESET} $*"; }
info() { echo -e "${CYAN}→${RESET} $*"; }
warn() { echo -e "${YELLOW}⚠${RESET}  $*"; }
err()  { echo -e "${RED}✗${RESET} $*" >&2; }
sep()  { echo -e "${AMBER}$(printf '─%.0s' {1..60})${RESET}"; }
die()  { err "$*"; exit 1; }

# ── Configurações ────────────────────────────────────────────
REPO_URL="https://github.com/darkthegod-pilot/DarkCred-Squad.git"
BRANCH="${DEPLOY_BRANCH:-claude/darkcred-instagram-merchants-xHC03}"
INSTALL_DIR="${DEPLOY_DIR:-$HOME/DarkCred-Squad}"
PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"
VENV_DIR="$INSTALL_DIR/.venv"
SERVICE_NAME="darkcred"
LOG_FILE="/tmp/darkcred_deploy.log"
PID_FILE="/tmp/darkcred.pid"
ENV_FILE="$INSTALL_DIR/.env"

# ── Detecta IP público ───────────────────────────────────────
get_public_ip() {
  local ip=""
  for svc in "https://api.ipify.org" "https://ipecho.net/plain" "https://icanhazip.com"; do
    ip=$(curl -sf --max-time 3 "$svc" 2>/dev/null || true)
    [[ -n "$ip" ]] && { echo "$ip"; return; }
  done
  # fallback: IP local
  hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost"
}

# ── Banner ───────────────────────────────────────────────────
print_banner() {
  echo ""
  echo -e "${AMBER}${BOLD}"
  echo "  ██████╗  █████╗ ██████╗ ██╗  ██╗ ██████╗██████╗ ███████╗██████╗ "
  echo "  ██╔══██╗██╔══██╗██╔══██╗██║ ██╔╝██╔════╝██╔══██╗██╔════╝██╔══██╗"
  echo "  ██║  ██║███████║██████╔╝█████╔╝ ██║     ██████╔╝█████╗  ██║  ██║"
  echo "  ██║  ██║██╔══██║██╔══██╗██╔═██╗ ██║     ██╔══██╗██╔══╝  ██║  ██║"
  echo "  ██████╔╝██║  ██║██║  ██║██║  ██╗╚██████╗██║  ██║███████╗██████╔╝"
  echo "  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═════╝ "
  echo -e "${RESET}"
  echo -e "  ${BOLD}Painel de Deploy — DarkCred Agency${RESET}"
  sep
}

# ════════════════════════════════════════════════════════════
#  MENU PRINCIPAL
# ════════════════════════════════════════════════════════════
show_menu() {
  print_banner
  echo ""
  echo -e "  ${BOLD}Escolha uma opção:${RESET}"
  echo ""
  echo -e "  ${GREEN}1${RESET}) ${BOLD}Instalar${RESET}         — Clone repo + venv + deps + .env + iniciar"
  echo -e "  ${CYAN}2${RESET}) ${BOLD}Atualizar${RESET}         — git pull + reinstalar deps + reiniciar"
  echo -e "  ${CYAN}3${RESET}) ${BOLD}Forçar atualização${RESET} — reset hard + pull + reinstalar tudo"
  echo -e "  ${CYAN}4${RESET}) ${BOLD}Reiniciar servidor${RESET} — para e sobe o uvicorn"
  echo -e "  ${CYAN}5${RESET}) ${BOLD}Parar servidor${RESET}     — encerra o processo"
  echo -e "  ${CYAN}6${RESET}) ${BOLD}Ver status${RESET}         — PID, porta, URL de acesso"
  echo -e "  ${CYAN}7${RESET}) ${BOLD}Ver logs${RESET}           — tail -f do log do servidor"
  echo -e "  ${CYAN}8${RESET}) ${BOLD}Editar .env${RESET}        — abre o .env no nano"
  echo -e "  ${CYAN}9${RESET}) ${BOLD}Verificar dependências${RESET} — checa sistema e Python"
  echo -e "  ${RED}0${RESET}) ${BOLD}Sair${RESET}"
  echo ""
  sep
}

# ════════════════════════════════════════════════════════════
#  UTILS
# ════════════════════════════════════════════════════════════
check_command() {
  command -v "$1" &>/dev/null || die "Comando '$1' não encontrado. Instale com: $2"
}

need_python() {
  local py=""
  for cmd in python3.12 python3.11 python3.10 python3.9 python3; do
    command -v "$cmd" &>/dev/null && { py=$(command -v "$cmd"); break; }
  done
  [[ -z "$py" ]] && die "Python 3.9+ não encontrado. Instale: sudo apt install python3"
  echo "$py"
}

is_running() {
  [[ -f "$PID_FILE" ]] || return 1
  local pid
  pid=$(cat "$PID_FILE")
  kill -0 "$pid" 2>/dev/null
}

stop_server() {
  if is_running; then
    local pid
    pid=$(cat "$PID_FILE")
    info "Parando servidor (PID $pid)..."
    kill "$pid" 2>/dev/null || true
    sleep 1
    kill -9 "$pid" 2>/dev/null || true
    rm -f "$PID_FILE"
    ok "Servidor parado."
  else
    # tenta matar por porta mesmo sem PID file
    local pid_by_port
    pid_by_port=$(lsof -ti :"$PORT" 2>/dev/null || true)
    if [[ -n "$pid_by_port" ]]; then
      warn "PID file ausente mas porta $PORT em uso. Encerrando PID $pid_by_port..."
      kill "$pid_by_port" 2>/dev/null || kill -9 "$pid_by_port" 2>/dev/null || true
      sleep 1
      ok "Porta liberada."
    else
      warn "Servidor não estava rodando."
    fi
  fi
}

start_server() {
  local py="$VENV_DIR/bin/python"
  [[ -f "$py" ]] || die "venv não encontrada em $VENV_DIR. Rode a opção de instalação primeiro."

  stop_server 2>/dev/null || true

  info "Iniciando servidor na porta $PORT..."
  cd "$INSTALL_DIR"

  nohup "$VENV_DIR/bin/uvicorn" web.app:app \
    --host "$HOST" \
    --port "$PORT" \
    --log-level info \
    >> "$LOG_FILE" 2>&1 &

  local pid=$!
  echo "$pid" > "$PID_FILE"
  sleep 2

  if kill -0 "$pid" 2>/dev/null; then
    ok "Servidor iniciado! PID $pid"
    print_url
  else
    err "Falha ao iniciar o servidor. Veja os logs:"
    tail -20 "$LOG_FILE"
    die "Abortando."
  fi
}

print_url() {
  local ip
  ip=$(get_public_ip)
  echo ""
  sep
  echo -e "  ${AMBER}${BOLD}✦ DarkCred está no ar!${RESET}"
  echo ""
  echo -e "  ${BOLD}URL local:${RESET}   http://localhost:$PORT"
  echo -e "  ${BOLD}URL pública:${RESET} http://$ip:$PORT"
  echo ""
  echo -e "  ${BOLD}PIN de acesso:${RESET} ${AMBER}42445${RESET}"
  sep
  echo ""
}

create_env() {
  if [[ -f "$ENV_FILE" ]]; then
    warn ".env já existe em $ENV_FILE"
    read -rp "  Recriar .env do zero? [s/N] " ans
    [[ "${ans,,}" == "s" ]] || { ok "Mantendo .env existente."; return; }
  fi

  echo ""
  info "Configurando variáveis de ambiente..."
  echo ""

  read -rp "  ANTHROPIC_API_KEY (obrigatório): " anthro_key
  [[ -z "$anthro_key" ]] && die "ANTHROPIC_API_KEY é obrigatório."

  read -rp "  OPENAI_API_KEY (opcional, Enter para pular): " openai_key

  read -rp "  Porta do servidor [$PORT]: " input_port
  [[ -n "$input_port" ]] && PORT="$input_port"

  read -rp "  SESSION_SECRET (Enter para gerar automaticamente): " sess_secret
  if [[ -z "$sess_secret" ]]; then
    sess_secret=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || date | md5sum | cut -c1-32)
  fi

  cat > "$ENV_FILE" << EOF
# DarkCred — Ambiente
# Gerado em: $(date '+%Y-%m-%d %H:%M:%S')

ANTHROPIC_API_KEY=$anthro_key
OPENAI_API_KEY=${openai_key:-}

PORT=$PORT
HOST=$HOST

SESSION_SECRET=$sess_secret
EOF

  chmod 600 "$ENV_FILE"
  ok ".env criado em $ENV_FILE"
}

install_deps() {
  local py
  py=$(need_python)
  info "Usando Python: $py"

  # Cria venv se não existir
  if [[ ! -d "$VENV_DIR" ]]; then
    info "Criando virtualenv em $VENV_DIR..."
    "$py" -m venv "$VENV_DIR" || die "Falha ao criar venv. Tente: $py -m pip install virtualenv"
    ok "Virtualenv criada."
  fi

  info "Instalando dependências..."
  "$VENV_DIR/bin/pip" install --upgrade pip --quiet

  local req="$INSTALL_DIR/requirements.txt"
  [[ -f "$req" ]] || die "requirements.txt não encontrado em $INSTALL_DIR"

  "$VENV_DIR/bin/pip" install -r "$req" --quiet \
    || { warn "Falha silenciosa — tentando sem --quiet..."; "$VENV_DIR/bin/pip" install -r "$req"; }

  ok "Dependências instaladas."
}

check_port_available() {
  if lsof -ti :"$PORT" &>/dev/null 2>&1; then
    warn "Porta $PORT em uso."
    read -rp "  Tentar porta $(( PORT + 1 ))? [S/n] " ans
    [[ "${ans,,}" == "n" ]] || { PORT=$(( PORT + 1 )); info "Usando porta $PORT"; }
  fi
}

# ════════════════════════════════════════════════════════════
#  OPÇÃO 1 — INSTALAÇÃO COMPLETA
# ════════════════════════════════════════════════════════════
action_install() {
  sep
  echo -e "  ${BOLD}INSTALAÇÃO COMPLETA${RESET}"
  sep
  echo ""

  # Pré-requisitos
  check_command git  "sudo apt install git"
  check_command curl "sudo apt install curl"
  need_python > /dev/null

  # Clone ou atualiza
  if [[ -d "$INSTALL_DIR/.git" ]]; then
    warn "Diretório $INSTALL_DIR já existe com git."
    read -rp "  Usar existente (sem novo clone)? [S/n] " ans
    if [[ "${ans,,}" == "n" ]]; then
      info "Removendo diretório antigo..."
      rm -rf "$INSTALL_DIR"
      clone_repo
    else
      info "Mantendo diretório existente. Fazendo pull..."
      git -C "$INSTALL_DIR" fetch origin "$BRANCH" 2>&1 | tail -3
      git -C "$INSTALL_DIR" checkout "$BRANCH" 2>/dev/null || true
      git -C "$INSTALL_DIR" pull origin "$BRANCH" || warn "Pull falhou — continuando com versão local."
    fi
  elif [[ -d "$INSTALL_DIR" ]]; then
    warn "Diretório $INSTALL_DIR existe mas sem git."
    read -rp "  Remover e clonar do zero? [s/N] " ans
    [[ "${ans,,}" == "s" ]] || die "Abortado. Remova $INSTALL_DIR manualmente."
    rm -rf "$INSTALL_DIR"
    clone_repo
  else
    clone_repo
  fi

  install_deps
  create_env
  check_port_available

  # Carrega PORT do .env se redefinido
  [[ -f "$ENV_FILE" ]] && source "$ENV_FILE" 2>/dev/null || true

  start_server
}

clone_repo() {
  info "Clonando $REPO_URL (branch: $BRANCH)..."
  local attempts=0
  while (( attempts < 3 )); do
    git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$INSTALL_DIR" \
      && { ok "Repositório clonado."; return; }
    attempts=$(( attempts + 1 ))
    warn "Tentativa $attempts/3 falhou. Aguardando $((attempts * 3))s..."
    sleep $(( attempts * 3 ))
  done
  die "Não foi possível clonar o repositório após 3 tentativas."
}

# ════════════════════════════════════════════════════════════
#  OPÇÃO 2 — ATUALIZAÇÃO NORMAL
# ════════════════════════════════════════════════════════════
action_update() {
  sep
  echo -e "  ${BOLD}ATUALIZAÇÃO (git pull)${RESET}"
  sep
  echo ""

  [[ -d "$INSTALL_DIR/.git" ]] || die "Projeto não encontrado em $INSTALL_DIR. Use a opção Instalar."

  info "Buscando atualizações (branch: $BRANCH)..."
  cd "$INSTALL_DIR"

  git fetch origin "$BRANCH" 2>&1 | tail -5

  local local_sha remote_sha
  local_sha=$(git rev-parse HEAD)
  remote_sha=$(git rev-parse "origin/$BRANCH" 2>/dev/null || echo "?")

  if [[ "$local_sha" == "$remote_sha" ]]; then
    ok "Já na versão mais recente ($local_sha)."
  else
    info "Aplicando mudanças..."
    git pull origin "$BRANCH" || {
      warn "Pull com conflito. Tentando stash + pull..."
      git stash push -m "deploy-auto-stash-$(date +%s)"
      git pull origin "$BRANCH" || die "Pull falhou mesmo após stash. Use 'Forçar atualização'."
    }
    ok "Atualizado para $(git rev-parse --short HEAD)."
  fi

  info "Verificando dependências novas..."
  install_deps

  start_server
}

# ════════════════════════════════════════════════════════════
#  OPÇÃO 3 — FORÇAR ATUALIZAÇÃO (reset hard)
# ════════════════════════════════════════════════════════════
action_force_update() {
  sep
  echo -e "  ${BOLD}${RED}FORÇAR ATUALIZAÇÃO${RESET}"
  sep
  echo ""
  warn "Isso fará git reset --hard e DESCARTARÁ alterações locais não commitadas."
  read -rp "  Confirmar? [s/N] " ans
  [[ "${ans,,}" == "s" ]] || { info "Cancelado."; return; }

  [[ -d "$INSTALL_DIR/.git" ]] || die "Projeto não encontrado em $INSTALL_DIR."

  cd "$INSTALL_DIR"
  info "Fazendo reset e pull forçado..."

  git fetch origin "$BRANCH" 2>&1 | tail -5
  git checkout "$BRANCH" 2>/dev/null || true
  git reset --hard "origin/$BRANCH"
  git clean -fd --quiet

  ok "Reset para origin/$BRANCH completo: $(git rev-parse --short HEAD)"

  info "Reinstalando todas as dependências..."
  rm -rf "$VENV_DIR"
  install_deps

  start_server
}

# ════════════════════════════════════════════════════════════
#  OPÇÃO 4 — REINICIAR
# ════════════════════════════════════════════════════════════
action_restart() {
  sep
  echo -e "  ${BOLD}REINICIAR SERVIDOR${RESET}"
  sep
  echo ""
  [[ -f "$ENV_FILE" ]] && source "$ENV_FILE" 2>/dev/null || true
  start_server
}

# ════════════════════════════════════════════════════════════
#  OPÇÃO 5 — PARAR
# ════════════════════════════════════════════════════════════
action_stop() {
  sep
  echo -e "  ${BOLD}PARAR SERVIDOR${RESET}"
  sep
  echo ""
  stop_server
}

# ════════════════════════════════════════════════════════════
#  OPÇÃO 6 — STATUS
# ════════════════════════════════════════════════════════════
action_status() {
  sep
  echo -e "  ${BOLD}STATUS DO SERVIDOR${RESET}"
  sep
  echo ""

  if is_running; then
    local pid
    pid=$(cat "$PID_FILE")
    ok "Servidor RODANDO (PID $pid)"
    local mem
    mem=$(ps -o rss= -p "$pid" 2>/dev/null | awk '{printf "%.1f MB", $1/1024}' || echo "?")
    echo -e "  Memória: $mem"
    print_url
  else
    err "Servidor NÃO está rodando."
    if [[ -f "$LOG_FILE" ]]; then
      echo ""
      warn "Últimas linhas do log:"
      tail -10 "$LOG_FILE"
    fi
  fi

  # Info do git
  if [[ -d "$INSTALL_DIR/.git" ]]; then
    echo ""
    info "Git:"
    echo -e "  Branch:  $(git -C "$INSTALL_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null)"
    echo -e "  Commit:  $(git -C "$INSTALL_DIR" rev-parse --short HEAD 2>/dev/null)"
    echo -e "  Data:    $(git -C "$INSTALL_DIR" log -1 --format='%ci' 2>/dev/null)"
  fi

  # Info do processo na porta
  echo ""
  info "Porta $PORT:"
  lsof -i :"$PORT" 2>/dev/null | head -5 || echo "  (nenhum processo)"
  echo ""
}

# ════════════════════════════════════════════════════════════
#  OPÇÃO 7 — LOGS
# ════════════════════════════════════════════════════════════
action_logs() {
  sep
  echo -e "  ${BOLD}LOGS DO SERVIDOR${RESET} — Ctrl+C para sair"
  sep
  echo ""
  [[ -f "$LOG_FILE" ]] || die "Log não encontrado em $LOG_FILE"
  tail -f "$LOG_FILE"
}

# ════════════════════════════════════════════════════════════
#  OPÇÃO 8 — EDITAR .ENV
# ════════════════════════════════════════════════════════════
action_edit_env() {
  sep
  echo -e "  ${BOLD}EDITAR .ENV${RESET}"
  sep
  echo ""
  [[ -f "$ENV_FILE" ]] || {
    warn ".env não encontrado. Criando agora..."
    create_env
    return
  }
  local editor="${EDITOR:-nano}"
  command -v "$editor" &>/dev/null || editor=vi
  "$editor" "$ENV_FILE"
  ok ".env salvo."
  read -rp "  Reiniciar servidor para aplicar mudanças? [S/n] " ans
  [[ "${ans,,}" == "n" ]] || action_restart
}

# ════════════════════════════════════════════════════════════
#  OPÇÃO 9 — VERIFICAR DEPENDÊNCIAS
# ════════════════════════════════════════════════════════════
action_check_deps() {
  sep
  echo -e "  ${BOLD}VERIFICAÇÃO DE DEPENDÊNCIAS${RESET}"
  sep
  echo ""

  local all_ok=true

  # Sistema
  for cmd in git curl lsof; do
    if command -v "$cmd" &>/dev/null; then
      ok "$cmd: $(command -v "$cmd")"
    else
      err "$cmd: NÃO ENCONTRADO"
      all_ok=false
    fi
  done

  echo ""

  # Python
  local py
  py=$(need_python 2>/dev/null || echo "")
  if [[ -n "$py" ]]; then
    ok "Python: $py ($("$py" --version 2>&1))"
  else
    err "Python 3.9+: NÃO ENCONTRADO"
    all_ok=false
  fi

  # Venv
  if [[ -d "$VENV_DIR" ]]; then
    ok "Virtualenv: $VENV_DIR"
    local uvi
    uvi=$("$VENV_DIR/bin/uvicorn" --version 2>/dev/null || echo "NÃO INSTALADO")
    ok "uvicorn: $uvi"
  else
    warn "Virtualenv: ainda não criada"
  fi

  echo ""

  # .env
  if [[ -f "$ENV_FILE" ]]; then
    ok ".env encontrado"
    source "$ENV_FILE" 2>/dev/null || true
    if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
      ok "ANTHROPIC_API_KEY: configurada (${#ANTHROPIC_API_KEY} chars)"
    else
      err "ANTHROPIC_API_KEY: NÃO configurada"
      all_ok=false
    fi
    if [[ -n "${OPENAI_API_KEY:-}" ]]; then
      ok "OPENAI_API_KEY: configurada"
    else
      warn "OPENAI_API_KEY: não configurada (opcional)"
    fi
  else
    warn ".env: não encontrado (necessário para rodar)"
  fi

  echo ""
  # Conectividade
  info "Testando conectividade..."
  if curl -sf --max-time 5 "https://api.anthropic.com" &>/dev/null; then
    ok "api.anthropic.com: acessível"
  else
    warn "api.anthropic.com: sem resposta (pode ser normal — HTTPS sem rota)"
  fi

  echo ""
  if $all_ok; then
    ok "${BOLD}Tudo OK! Pronto para rodar.${RESET}"
  else
    warn "Alguns problemas encontrados. Corrija antes de instalar."
  fi
  echo ""
}

# ════════════════════════════════════════════════════════════
#  ARGUMENTOS DIRETOS (sem menu)
#  Uso: ./deploy.sh install | update | force | restart | stop | status | logs
# ════════════════════════════════════════════════════════════
handle_arg() {
  case "${1,,}" in
    install|i)       action_install      ;;
    update|u)        action_update       ;;
    force|f)         action_force_update ;;
    restart|r)       action_restart      ;;
    stop|s)          action_stop         ;;
    status|st)       action_status       ;;
    logs|l)          action_logs         ;;
    env|e)           action_edit_env     ;;
    check|c)         action_check_deps   ;;
    help|h|--help)   show_usage          ;;
    *)               err "Argumento inválido: $1"; show_usage; exit 1 ;;
  esac
}

show_usage() {
  echo ""
  echo -e "  ${BOLD}Uso:${RESET} ./deploy.sh [comando]"
  echo ""
  echo "  Comandos:"
  echo "    install   — Instalação completa"
  echo "    update    — git pull + reiniciar"
  echo "    force     — reset hard + reinstalar tudo"
  echo "    restart   — reiniciar servidor"
  echo "    stop      — parar servidor"
  echo "    status    — ver status e URL"
  echo "    logs      — tail -f do log"
  echo "    env       — editar .env"
  echo "    check     — checar dependências"
  echo ""
  echo "  Variáveis de ambiente:"
  echo "    DEPLOY_DIR=<path>     — diretório de instalação (padrão: ~/DarkCred-Squad)"
  echo "    DEPLOY_BRANCH=<name>  — branch do git"
  echo "    PORT=<num>            — porta do servidor (padrão: 8000)"
  echo ""
  echo "  Exemplos:"
  echo "    ./deploy.sh install"
  echo "    PORT=9000 ./deploy.sh install"
  echo "    ./deploy.sh force"
  echo ""
}

# ════════════════════════════════════════════════════════════
#  PONTO DE ENTRADA
# ════════════════════════════════════════════════════════════
main() {
  # Se recebeu argumento, executa direto
  if [[ $# -gt 0 ]]; then
    print_banner
    handle_arg "$1"
    exit 0
  fi

  # Modo interativo
  while true; do
    show_menu
    read -rp "  Opção: " choice
    echo ""
    case "$choice" in
      1) action_install      ;;
      2) action_update       ;;
      3) action_force_update ;;
      4) action_restart      ;;
      5) action_stop         ;;
      6) action_status       ;;
      7) action_logs         ;;
      8) action_edit_env     ;;
      9) action_check_deps   ;;
      0) echo -e "${AMBER}Saindo...${RESET}"; exit 0 ;;
      *) warn "Opção inválida: '$choice'" ;;
    esac

    echo ""
    read -rp "  Pressione Enter para voltar ao menu..." _
  done
}

main "$@"
