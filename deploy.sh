#!/usr/bin/env bash
# ============================================================
#  DarkCred — Deploy / Manage Script
#  Uso: ./deploy.sh [comando]
#
#  Comandos:
#    install   — clone + venv + deps + .env + watchdog start
#    update    — git pull + reiniciar
#    force     — reset hard + reinstalar tudo
#    restart   — reiniciar servidor
#    stop      — parar servidor
#    status    — ver status, PID, URL
#    logs      — tail -f do log
#    env       — editar .env
#    check     — checar deps e API keys
#    cron      — instalar atualização automática via cron (polling)
#    uncron    — remover cron de auto-update
#
#  Variáveis de ambiente:
#    DEPLOY_DIR=<path>      diretório de instalação (padrão: ~/DarkCred-Squad)
#    DEPLOY_BRANCH=<name>   branch do git
#    PORT=<num>             porta do servidor (padrão: 8000)
# ============================================================
set -euo pipefail

# ── Cores ────────────────────────────────────────────────────
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'; AMBER='\033[38;5;214m'
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
LOG_FILE="/tmp/darkcred.log"
PID_FILE="/tmp/darkcred.pid"
SENTINEL="$INSTALL_DIR/.restart_needed"
ENV_FILE="$INSTALL_DIR/.env"

# ── IP público ───────────────────────────────────────────────
get_public_ip() {
  local ip=""
  for svc in "https://api.ipify.org" "https://ipecho.net/plain" "https://icanhazip.com"; do
    ip=$(curl -sf --max-time 3 "$svc" 2>/dev/null || true)
    [[ -n "$ip" ]] && { echo "$ip"; return; }
  done
  hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost"
}

# ── Banner ───────────────────────────────────────────────────
print_banner() {
  echo -e "\n${AMBER}${BOLD}"
  echo "  ██████╗  █████╗ ██████╗ ██╗  ██╗ ██████╗██████╗ ███████╗██████╗ "
  echo "  ██╔══██╗██╔══██╗██╔══██╗██║ ██╔╝██╔════╝██╔══██╗██╔════╝██╔══██╗"
  echo "  ██║  ██║███████║██████╔╝█████╔╝ ██║     ██████╔╝█████╗  ██║  ██║"
  echo "  ██║  ██║██╔══██║██╔══██╗██╔═██╗ ██║     ██╔══██╗██╔══╝  ██║  ██║"
  echo "  ██████╔╝██║  ██║██║  ██║██║  ██╗╚██████╗██║  ██║███████╗██████╔╝"
  echo "  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═════╝ "
  echo -e "${RESET}  ${BOLD}Painel de Deploy — DarkCred Agency${RESET}"
  sep
}

# ════════════════════════════════════════════════════════════
#  UTILS
# ════════════════════════════════════════════════════════════
need_python() {
  for cmd in python3.12 python3.11 python3.10 python3.9 python3; do
    command -v "$cmd" &>/dev/null && { command -v "$cmd"; return; }
  done
  die "Python 3.9+ não encontrado. Instale: sudo apt install python3"
}

is_running() {
  [[ -f "$PID_FILE" ]] || return 1
  kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

kill_on_port() {
  local pid
  pid=$(lsof -ti :"$PORT" 2>/dev/null || true)
  [[ -z "$pid" ]] && return
  warn "Porta $PORT ocupada pelo PID $pid — encerrando..."
  kill "$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null || true
  sleep 1
}

stop_server() {
  if is_running; then
    local pid; pid=$(cat "$PID_FILE")
    info "Parando servidor (PID $pid)..."
    kill "$pid" 2>/dev/null || true
    sleep 1
    kill -9 "$pid" 2>/dev/null || true
    rm -f "$PID_FILE"
    ok "Servidor parado."
  else
    kill_on_port
  fi
}

print_url() {
  local ip; ip=$(get_public_ip)
  echo ""; sep
  echo -e "  ${AMBER}${BOLD}✦ DarkCred está no ar!${RESET}"
  echo ""
  echo -e "  ${BOLD}Local:${RESET}   http://localhost:$PORT"
  echo -e "  ${BOLD}Público:${RESET} http://$ip:$PORT"
  echo ""
  echo -e "  ${BOLD}PIN de acesso:${RESET}  ${AMBER}42445${RESET}"
  echo ""

  # Mostra URL do webhook se configurado
  local whsec; whsec=$(grep -s "^WEBHOOK_SECRET=" "$ENV_FILE" | cut -d= -f2- || true)
  if [[ -n "$whsec" ]]; then
    echo -e "  ${BOLD}Webhook URL:${RESET} http://$ip:$PORT/webhook/push"
    echo -e "  ${BOLD}Webhook Secret:${RESET} ${CYAN}$whsec${RESET}"
  fi
  sep; echo ""
}

# ════════════════════════════════════════════════════════════
#  WATCHDOG LOOP — reinicia o servidor automaticamente
#  Detecta .restart_needed (gerado pelo webhook) e reinicia
# ════════════════════════════════════════════════════════════
run_watchdog() {
  info "Iniciando watchdog loop (reinício automático ativado)..."

  # Carrega .env
  [[ -f "$ENV_FILE" ]] && set -a && source "$ENV_FILE" && set +a

  cd "$INSTALL_DIR"

  while true; do
    rm -f "$SENTINEL"

    # Inicia uvicorn em foreground dentro do loop
    "$VENV_DIR/bin/uvicorn" web.app:app \
      --host "$HOST" \
      --port "$PORT" \
      --log-level info \
      >> "$LOG_FILE" 2>&1 &

    local pid=$!
    echo "$pid" > "$PID_FILE"
    info "Servidor iniciado (PID $pid)"

    # Aguarda o processo terminar
    wait "$pid" || true
    local exit_code=$?
    rm -f "$PID_FILE"

    # Verifica se é reinício intencional (sentinel do webhook)
    if [[ -f "$SENTINEL" ]]; then
      info "Sentinel detectado — reiniciando para aplicar atualização..."
      rm -f "$SENTINEL"
      sleep 1
      continue   # reinicia o loop
    fi

    # Saída com código != 0 → aguarda e reinicia
    if (( exit_code != 0 )); then
      warn "Servidor encerrou com código $exit_code. Reiniciando em 3s..."
      sleep 3
      continue
    fi

    # Saída limpa (código 0) sem sentinel → encerramento intencional
    info "Servidor encerrado normalmente. Watchdog saindo."
    break
  done
}

# ════════════════════════════════════════════════════════════
#  START / RESTART usando watchdog em background
# ════════════════════════════════════════════════════════════
start_server() {
  [[ -f "$VENV_DIR/bin/uvicorn" ]] || die "venv não encontrada. Execute 'install' primeiro."

  stop_server 2>/dev/null || true
  kill_on_port

  # Garante que a porta está livre
  sleep 0.5

  info "Iniciando watchdog em background..."
  nohup bash "$0" _watchdog >> "$LOG_FILE" 2>&1 &
  local wpid=$!
  sleep 2

  # Verifica se uvicorn subiu
  local attempts=0
  while (( attempts < 10 )); do
    if lsof -ti :"$PORT" &>/dev/null 2>&1; then
      ok "Servidor no ar!"
      print_url
      return
    fi
    sleep 1
    (( attempts++ ))
  done

  err "Servidor não respondeu na porta $PORT após 10s."
  warn "Últimas linhas do log:"
  tail -20 "$LOG_FILE"
  die "Verifique .env e tente novamente."
}

# ════════════════════════════════════════════════════════════
#  INSTALAÇÃO
# ════════════════════════════════════════════════════════════
install_deps() {
  local py; py=$(need_python)
  info "Python: $py"

  if [[ ! -d "$VENV_DIR" ]]; then
    info "Criando virtualenv..."
    "$py" -m venv "$VENV_DIR" || die "Falha ao criar venv."
    ok "Virtualenv criada."
  fi

  info "Instalando/atualizando dependências..."
  "$VENV_DIR/bin/pip" install --upgrade pip -q

  "$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q \
    || "$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

  ok "Dependências instaladas."
}

create_env() {
  if [[ -f "$ENV_FILE" ]]; then
    warn ".env já existe."
    read -rp "  Recriar? [s/N] " ans
    [[ "${ans,,}" == "s" ]] || { ok "Mantendo .env existente."; return; }
  fi

  echo ""
  echo -e "  ${BOLD}Configuração de API Keys${RESET}"
  echo -e "  ${CYAN}As chaves NÃO estão no repositório por segurança.${RESET}"
  echo -e "  Você precisa fornecer as suas abaixo."
  echo ""

  # ANTHROPIC_API_KEY
  while true; do
    read -rp "  ANTHROPIC_API_KEY (obrigatório, começa com sk-ant-...): " anthro_key
    [[ -n "$anthro_key" ]] && break
    warn "  Chave obrigatória — não pode ficar vazia."
  done

  # OPENAI_API_KEY
  read -rp "  OPENAI_API_KEY (opcional, Enter para pular):              " openai_key

  # WEBHOOK_SECRET
  read -rp "  WEBHOOK_SECRET (auto-deploy pós-commit, Enter p/ gerar): " whook_secret
  if [[ -z "$whook_secret" ]]; then
    whook_secret=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))" 2>/dev/null \
                   || date | sha256sum | head -c 32)
    ok "Webhook secret gerado automaticamente."
  fi

  # PORT
  read -rp "  Porta do servidor [$PORT]: " input_port
  [[ -n "$input_port" ]] && PORT="$input_port"

  # SESSION_SECRET
  local sess_secret
  sess_secret=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null \
                || date | sha256sum | head -c 64)

  cat > "$ENV_FILE" << EOF
# DarkCred — Ambiente
# Gerado em: $(date '+%Y-%m-%d %H:%M:%S')
# NÃO commite este arquivo!

# ── APIs ─────────────────────────────────────────
ANTHROPIC_API_KEY=$anthro_key
OPENAI_API_KEY=${openai_key:-}

# ── Servidor ─────────────────────────────────────
PORT=$PORT
HOST=$HOST
SESSION_SECRET=$sess_secret

# ── Auto-deploy webhook ──────────────────────────
# Configure no GitHub: Settings → Webhooks
# URL:    http://SEU_IP:$PORT/webhook/push
# Secret: $whook_secret
# Content-Type: application/json
WEBHOOK_SECRET=$whook_secret
EOF

  chmod 600 "$ENV_FILE"
  ok ".env criado em $ENV_FILE"

  echo ""
  echo -e "  ${BOLD}Para configurar o webhook no GitHub:${RESET}"
  echo -e "  1. Vá em: Settings → Webhooks → Add webhook"
  echo -e "  2. Payload URL: ${CYAN}http://$(get_public_ip):$PORT/webhook/push${RESET}"
  echo -e "  3. Content-Type: ${CYAN}application/json${RESET}"
  echo -e "  4. Secret: ${AMBER}$whook_secret${RESET}"
  echo -e "  5. Evento: ${CYAN}Just the push event${RESET}"
  echo ""
}

clone_repo() {
  info "Clonando $REPO_URL (branch: $BRANCH)..."
  local attempt=0
  while (( attempt < 3 )); do
    git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$INSTALL_DIR" \
      && { ok "Repositório clonado."; return; }
    (( attempt++ ))
    warn "Tentativa $attempt/3 falhou. Aguardando $((attempt * 4))s..."
    sleep $(( attempt * 4 ))
  done
  die "Clone falhou após 3 tentativas."
}

action_install() {
  sep; echo -e "  ${BOLD}INSTALAÇÃO COMPLETA${RESET}"; sep; echo ""

  command -v git  &>/dev/null || die "git não encontrado. Instale: sudo apt install git"
  command -v curl &>/dev/null || die "curl não encontrado. Instale: sudo apt install curl"
  need_python > /dev/null

  # Clone ou usa existente
  if [[ -d "$INSTALL_DIR/.git" ]]; then
    warn "Diretório $INSTALL_DIR já existe."
    read -rp "  Atualizar via git pull? [S/n] " ans
    if [[ "${ans,,}" != "n" ]]; then
      git -C "$INSTALL_DIR" fetch origin "$BRANCH" 2>&1 | tail -3
      git -C "$INSTALL_DIR" pull origin "$BRANCH" \
        || warn "Pull falhou — continuando com versão local."
    fi
  elif [[ -d "$INSTALL_DIR" ]]; then
    warn "$INSTALL_DIR existe sem git."
    read -rp "  Remover e clonar do zero? [s/N] " ans
    [[ "${ans,,}" == "s" ]] || die "Remova $INSTALL_DIR manualmente e tente de novo."
    rm -rf "$INSTALL_DIR"; clone_repo
  else
    clone_repo
  fi

  install_deps
  create_env

  # Recarrega PORT do .env
  [[ -f "$ENV_FILE" ]] && source "$ENV_FILE" 2>/dev/null || true

  start_server
}

# ════════════════════════════════════════════════════════════
#  UPDATE
# ════════════════════════════════════════════════════════════
action_update() {
  sep; echo -e "  ${BOLD}ATUALIZAÇÃO (git pull)${RESET}"; sep; echo ""
  [[ -d "$INSTALL_DIR/.git" ]] || die "Projeto não encontrado. Execute 'install'."

  cd "$INSTALL_DIR"
  git fetch origin "$BRANCH" 2>&1 | tail -5

  local local_sha; local_sha=$(git rev-parse HEAD)
  local remote_sha; remote_sha=$(git rev-parse "origin/$BRANCH" 2>/dev/null || echo "")

  if [[ -n "$remote_sha" && "$local_sha" == "$remote_sha" ]]; then
    ok "Já na versão mais recente ($(git rev-parse --short HEAD))."
  else
    info "Aplicando mudanças..."
    git pull origin "$BRANCH" || {
      warn "Pull com conflito — tentando stash + pull..."
      git stash push -m "auto-stash-$(date +%s)"
      git pull origin "$BRANCH" || die "Pull falhou. Use 'force' para resetar."
    }
    ok "Atualizado para $(git rev-parse --short HEAD)."
    install_deps
  fi

  start_server
}

# ════════════════════════════════════════════════════════════
#  FORCE UPDATE
# ════════════════════════════════════════════════════════════
action_force_update() {
  sep; echo -e "  ${BOLD}${RED}FORÇAR ATUALIZAÇÃO (reset hard)${RESET}"; sep; echo ""
  warn "Isso descarta TODAS as alterações locais não commitadas."
  read -rp "  Confirmar? [s/N] " ans
  [[ "${ans,,}" == "s" ]] || { info "Cancelado."; return; }

  [[ -d "$INSTALL_DIR/.git" ]] || die "Projeto não encontrado. Execute 'install'."

  cd "$INSTALL_DIR"
  git fetch origin "$BRANCH" 2>&1 | tail -5
  git checkout "$BRANCH" 2>/dev/null || true
  git reset --hard "origin/$BRANCH"
  git clean -fd --quiet
  ok "Reset para origin/$BRANCH: $(git rev-parse --short HEAD)"

  info "Reinstalando deps..."
  rm -rf "$VENV_DIR"
  install_deps

  start_server
}

# ════════════════════════════════════════════════════════════
#  CRON — polling automático (fallback para webhook)
# ════════════════════════════════════════════════════════════
action_cron_install() {
  sep; echo -e "  ${BOLD}INSTALAR AUTO-UPDATE VIA CRON${RESET}"; sep; echo ""
  warn "Isso adiciona uma tarefa cron que verifica atualizações a cada 5 minutos."
  warn "Recomendado apenas se o webhook não estiver funcionando."
  read -rp "  Confirmar? [s/N] " ans
  [[ "${ans,,}" == "s" ]] || { info "Cancelado."; return; }

  local script_path; script_path=$(realpath "$0")
  local cron_line="*/5 * * * * DEPLOY_DIR=$INSTALL_DIR PORT=$PORT bash $script_path _poll >> /tmp/darkcred_cron.log 2>&1"

  # Remove entradas anteriores do DarkCred
  (crontab -l 2>/dev/null | grep -v "darkcred" | grep -v "$script_path") | crontab - 2>/dev/null || true

  # Adiciona nova entrada
  (crontab -l 2>/dev/null; echo "$cron_line") | crontab -

  ok "Cron instalado: verifica atualizações a cada 5 minutos."
  info "Log do cron: /tmp/darkcred_cron.log"
  info "Para remover: ./deploy.sh uncron"
  echo ""
}

action_cron_remove() {
  sep; echo -e "  ${BOLD}REMOVER CRON DE AUTO-UPDATE${RESET}"; sep; echo ""
  local script_path; script_path=$(realpath "$0")
  (crontab -l 2>/dev/null | grep -v "$script_path") | crontab - 2>/dev/null || true
  ok "Cron removido."
}

# Chamado pelo cron — faz poll silencioso
action_poll() {
  [[ -d "$INSTALL_DIR/.git" ]] || exit 0
  cd "$INSTALL_DIR"

  git fetch origin "$BRANCH" -q 2>/dev/null || exit 0

  local local_sha; local_sha=$(git rev-parse HEAD)
  local remote_sha; remote_sha=$(git rev-parse "origin/$BRANCH" 2>/dev/null || echo "")

  [[ -z "$remote_sha" || "$local_sha" == "$remote_sha" ]] && exit 0

  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Nova versão detectada: $remote_sha — atualizando..."

  git pull origin "$BRANCH" -q || exit 1

  [[ -f "$ENV_FILE" ]] && source "$ENV_FILE" 2>/dev/null || true

  # Sinaliza ao watchdog para reiniciar
  touch "$SENTINEL"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Sentinel criado — servidor será reiniciado pelo watchdog."
}

# ════════════════════════════════════════════════════════════
#  STATUS, LOGS, ENV, CHECK
# ════════════════════════════════════════════════════════════
action_restart() {
  sep; echo -e "  ${BOLD}REINICIAR SERVIDOR${RESET}"; sep; echo ""
  [[ -f "$ENV_FILE" ]] && source "$ENV_FILE" 2>/dev/null || true
  start_server
}

action_stop() {
  sep; echo -e "  ${BOLD}PARAR SERVIDOR${RESET}"; sep; echo ""
  stop_server
}

action_status() {
  sep; echo -e "  ${BOLD}STATUS${RESET}"; sep; echo ""

  if is_running; then
    local pid; pid=$(cat "$PID_FILE")
    ok "Servidor ${GREEN}RODANDO${RESET} (PID $pid)"
    local mem; mem=$(ps -o rss= -p "$pid" 2>/dev/null | awk '{printf "%.1f MB", $1/1024}' || echo "?")
    echo -e "  Memória: $mem"
    print_url
  else
    err "Servidor ${RED}NÃO está rodando${RESET}"
    [[ -f "$LOG_FILE" ]] && { echo ""; warn "Últimas linhas do log:"; tail -10 "$LOG_FILE"; }
  fi

  if [[ -d "$INSTALL_DIR/.git" ]]; then
    echo ""
    info "Git:"
    echo -e "  Branch:  $(git -C "$INSTALL_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null)"
    echo -e "  Commit:  $(git -C "$INSTALL_DIR" rev-parse --short HEAD 2>/dev/null)"
    echo -e "  Última:  $(git -C "$INSTALL_DIR" log -1 --format='%s (%ci)' 2>/dev/null)"
  fi

  echo ""
  info "Porta $PORT:"
  lsof -i :"$PORT" 2>/dev/null | head -5 || echo "  (nenhum processo)"

  # Mostra config do webhook
  echo ""
  local whsec; whsec=$(grep -s "^WEBHOOK_SECRET=" "$ENV_FILE" | cut -d= -f2- || true)
  if [[ -n "$whsec" ]]; then
    local ip; ip=$(get_public_ip)
    info "Webhook de auto-deploy:"
    echo -e "  URL:    http://$ip:$PORT/webhook/push"
    echo -e "  Secret: $whsec"
  else
    warn "Webhook não configurado (WEBHOOK_SECRET ausente no .env)"
  fi
  echo ""
}

action_logs() {
  sep; echo -e "  ${BOLD}LOGS${RESET} — Ctrl+C para sair"; sep; echo ""
  [[ -f "$LOG_FILE" ]] || die "Log não encontrado: $LOG_FILE"
  tail -f "$LOG_FILE"
}

action_edit_env() {
  sep; echo -e "  ${BOLD}EDITAR .ENV${RESET}"; sep; echo ""
  if [[ ! -f "$ENV_FILE" ]]; then
    warn ".env não encontrado — criando..."
    create_env; return
  fi
  local editor="${EDITOR:-nano}"
  command -v "$editor" &>/dev/null || editor=vi
  "$editor" "$ENV_FILE"
  ok ".env salvo."
  read -rp "  Reiniciar para aplicar? [S/n] " ans
  [[ "${ans,,}" == "n" ]] || action_restart
}

action_check() {
  sep; echo -e "  ${BOLD}VERIFICAÇÃO DE DEPENDÊNCIAS E CHAVES${RESET}"; sep; echo ""

  local all_ok=true

  for cmd in git curl lsof; do
    command -v "$cmd" &>/dev/null \
      && ok "$cmd: $(command -v "$cmd")" \
      || { err "$cmd: NÃO ENCONTRADO"; all_ok=false; }
  done

  echo ""
  local py; py=$(need_python 2>/dev/null || echo "")
  [[ -n "$py" ]] \
    && ok "Python: $py ($("$py" --version 2>&1))" \
    || { err "Python 3.9+ não encontrado"; all_ok=false; }

  [[ -d "$VENV_DIR" ]] \
    && ok "Virtualenv: $VENV_DIR" \
    || warn "Virtualenv não criada ainda"

  echo ""
  echo -e "  ${BOLD}API Keys (.env)${RESET}"

  if [[ -f "$ENV_FILE" ]]; then
    source "$ENV_FILE" 2>/dev/null || true

    if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
      ok "ANTHROPIC_API_KEY: configurada (${#ANTHROPIC_API_KEY} chars)"
    else
      err "ANTHROPIC_API_KEY: ${RED}NÃO configurada${RESET} — sem ela o sistema não funciona"
      all_ok=false
    fi

    if [[ -n "${OPENAI_API_KEY:-}" ]]; then
      ok "OPENAI_API_KEY: configurada (fallback ativo)"
    else
      warn "OPENAI_API_KEY: não configurada (opcional — usado como fallback)"
    fi

    if [[ -n "${WEBHOOK_SECRET:-}" ]]; then
      ok "WEBHOOK_SECRET: configurado (auto-deploy ativo)"
    else
      warn "WEBHOOK_SECRET: não configurado — auto-deploy via webhook desativado"
    fi
  else
    err ".env não encontrado em $ENV_FILE"
    all_ok=false
  fi

  echo ""
  $all_ok && ok "${BOLD}Tudo OK!${RESET}" || warn "Corrija os itens acima antes de iniciar."
  echo ""
}

# ════════════════════════════════════════════════════════════
#  MENU INTERATIVO
# ════════════════════════════════════════════════════════════
show_menu() {
  print_banner
  echo ""
  echo -e "  ${BOLD}Servidor${RESET}"
  echo -e "  ${GREEN}1${RESET}) Instalar          — clone + deps + .env + start"
  echo -e "  ${CYAN}2${RESET}) Atualizar          — git pull + reiniciar"
  echo -e "  ${CYAN}3${RESET}) Forçar atualização — reset hard + reinstalar tudo"
  echo -e "  ${CYAN}4${RESET}) Reiniciar"
  echo -e "  ${CYAN}5${RESET}) Parar"
  echo -e "  ${CYAN}6${RESET}) Status + URL de acesso"
  echo -e "  ${CYAN}7${RESET}) Logs em tempo real"
  echo ""
  echo -e "  ${BOLD}Configuração${RESET}"
  echo -e "  ${CYAN}8${RESET}) Editar .env        — API keys + secrets"
  echo -e "  ${CYAN}9${RESET}) Verificar deps e API keys"
  echo -e "  ${CYAN}c${RESET}) Instalar cron       — auto-update a cada 5min (polling)"
  echo -e "  ${CYAN}u${RESET}) Remover cron"
  echo ""
  echo -e "  ${RED}0${RESET}) Sair"
  sep
}

# ════════════════════════════════════════════════════════════
#  ARGUMENTO DIRETO
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
    check|c)         action_check        ;;
    cron)            action_cron_install ;;
    uncron)          action_cron_remove  ;;
    _watchdog)       run_watchdog        ;;  # interno — chamado pelo nohup
    _poll)           action_poll         ;;  # interno — chamado pelo cron
    help|h|--help)
      echo ""
      echo -e "  ${BOLD}Uso:${RESET} ./deploy.sh [comando]"
      echo ""
      echo "  install    Instalação completa"
      echo "  update     git pull + reiniciar"
      echo "  force      reset hard + reinstalar tudo"
      echo "  restart    reiniciar servidor"
      echo "  stop       parar servidor"
      echo "  status     ver status, URL, webhook info"
      echo "  logs       tail -f do log"
      echo "  env        editar .env (API keys)"
      echo "  check      checar dependências e API keys"
      echo "  cron       instalar polling automático (fallback)"
      echo "  uncron     remover cron"
      echo ""
      echo "  Variáveis:"
      echo "    DEPLOY_DIR=<path>    diretório de instalação"
      echo "    DEPLOY_BRANCH=<br>   branch do git"
      echo "    PORT=<num>           porta (padrão 8000)"
      echo ""
      ;;
    *) err "Comando inválido: $1"; bash "$0" help; exit 1 ;;
  esac
}

main() {
  if [[ $# -gt 0 ]]; then
    [[ "$1" != "_watchdog" && "$1" != "_poll" ]] && print_banner
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
      9) action_check        ;;
      c) action_cron_install ;;
      u) action_cron_remove  ;;
      0) echo -e "${AMBER}Saindo...${RESET}"; exit 0 ;;
      *) warn "Opção inválida: '$choice'" ;;
    esac
    echo ""
    read -rp "  Enter para continuar..." _
  done
}

main "$@"
