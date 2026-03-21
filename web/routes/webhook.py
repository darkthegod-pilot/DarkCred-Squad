"""
DarkCred — Webhook de auto-deploy.

Recebe POST do GitHub/GitLab/genérico e executa git pull + reinicia o servidor.
Configura o secret em .env: WEBHOOK_SECRET=sua_chave

Exemplo de chamada manual para testar:
    curl -X POST http://localhost:8000/webhook/push \
         -H "X-Webhook-Secret: sua_chave"
"""
import hashlib
import hmac
import logging
import os
import subprocess
import threading
import time
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

log = logging.getLogger("darkcred.webhook")

router = APIRouter(prefix="/webhook", tags=["webhook"])

ROOT = Path(__file__).parent.parent.parent   # raiz do projeto
RESTART_SENTINEL = ROOT / ".restart_needed"  # arquivo sentinela


def _git_pull() -> tuple[bool, str]:
    """Executa git pull na raiz do projeto. Retorna (sucesso, mensagem)."""
    try:
        result = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = (result.stdout + result.stderr).strip()
        if result.returncode == 0:
            log.info("git pull OK: %s", output)
            return True, output
        else:
            log.error("git pull falhou (rc=%d): %s", result.returncode, output)
            return False, output
    except subprocess.TimeoutExpired:
        return False, "git pull timeout (>60s)"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _restart_after_delay(delay: float = 1.5) -> None:
    """Escreve sentinela e encerra o processo após `delay` segundos.

    O watchdog loop no deploy.sh detecta a saída e reinicia o uvicorn
    automaticamente com o código atualizado.
    """
    def _do():
        time.sleep(delay)
        log.info("Reiniciando processo para aplicar atualização...")
        RESTART_SENTINEL.touch()
        os._exit(0)  # noqa: SLF001 — encerramento intencional

    threading.Thread(target=_do, daemon=True).start()


def _verify_secret(raw_body: bytes, secret: str, signature: str | None) -> bool:
    """Verifica assinatura HMAC-SHA256 no formato 'sha256=<hex>'."""
    expected = "sha256=" + hmac.new(
        secret.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    try:
        return hmac.compare_digest(expected, signature or "")
    except Exception:  # noqa: BLE001
        return False


@router.post("/push")
async def webhook_push(
    request: Request,
    x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
    x_hub_signature_256: str | None = Header(default=None, alias="X-Hub-Signature-256"),
):
    """
    Recebe notificação de push e aciona git pull + reinício.

    Autenticação (use UMA das opções):
    - Header `X-Webhook-Secret: <valor de WEBHOOK_SECRET>`   (simples)
    - Header `X-Hub-Signature-256: sha256=<hmac>`            (padrão GitHub)

    Se WEBHOOK_SECRET não estiver definido no .env, o endpoint fica
    desabilitado e retorna 403.
    """
    webhook_secret = os.environ.get("WEBHOOK_SECRET", "")

    # Sem secret configurado → endpoint desabilitado
    if not webhook_secret:
        log.warning("Webhook recebido mas WEBHOOK_SECRET não está configurado.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="WEBHOOK_SECRET não configurado no servidor.",
        )

    raw_body = await request.body()

    # Verifica autenticidade
    autenticado = False

    # Modo simples: header direto
    if x_webhook_secret:
        autenticado = hmac.compare_digest(webhook_secret, x_webhook_secret)

    # Modo GitHub: HMAC-SHA256
    if not autenticado and x_hub_signature_256:
        autenticado = _verify_secret(raw_body, webhook_secret, x_hub_signature_256)

    if not autenticado:
        log.warning("Webhook com credencial inválida rejeitado.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credencial inválida.",
        )

    # Executa git pull em background para não bloquear a resposta
    def _run():
        ok, msg = _git_pull()
        if ok:
            _restart_after_delay(1.5)
        else:
            log.error("Auto-deploy falhou: %s", msg)

    threading.Thread(target=_run, daemon=True).start()

    return JSONResponse({"status": "ok", "message": "Atualização iniciada."})


@router.get("/status")
async def webhook_status(
    x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
):
    """Retorna info do deploy atual (commit, branch). Requer autenticação."""
    webhook_secret = os.environ.get("WEBHOOK_SECRET", "")
    if webhook_secret and (not x_webhook_secret or not hmac.compare_digest(webhook_secret, x_webhook_secret)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autorizado.")

    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT), text=True
        ).strip()
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(ROOT), text=True
        ).strip()
        msg = subprocess.check_output(
            ["git", "log", "-1", "--format=%s"], cwd=str(ROOT), text=True
        ).strip()
        date = subprocess.check_output(
            ["git", "log", "-1", "--format=%ci"], cwd=str(ROOT), text=True
        ).strip()
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"error": str(exc)}, status_code=500)

    return JSONResponse({
        "commit": commit,
        "branch": branch,
        "message": msg,
        "date": date,
        "sentinel": RESTART_SENTINEL.exists(),
    })
