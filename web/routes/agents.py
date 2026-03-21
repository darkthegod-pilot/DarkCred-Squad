"""Chat com os agentes via Server-Sent Events (SSE)."""
import asyncio
import os
from pathlib import Path

import anthropic
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sse_starlette.sse import EventSourceResponse

from web.auth import require_auth

# Importa personas
from alina.persona import SYSTEM_PROMPT as ALINA_SP
from agentes.vera.persona  import SYSTEM_PROMPT as VERA_SP,  NOME as VERA_NOME,  TITULO as VERA_TITULO
from agentes.dasha.persona import SYSTEM_PROMPT as DASHA_SP, NOME as DASHA_NOME, TITULO as DASHA_TITULO
from agentes.mila.persona  import SYSTEM_PROMPT as MILA_SP,  NOME as MILA_NOME,  TITULO as MILA_TITULO
from agentes.igor.persona  import SYSTEM_PROMPT as IGOR_SP,  NOME as IGOR_NOME,  TITULO as IGOR_TITULO

router = APIRouter()
ROOT = Path(__file__).parent.parent.parent
templates = Jinja2Templates(directory=str(ROOT / "web" / "templates"))

AGENTS: dict[str, dict] = {
    "alina": {
        "id":     "alina",
        "nome":   "Alina Pretrov",
        "titulo": "Diretora Criativa",
        "cor":    "amber",
        "inicial":"A",
        "sp":     ALINA_SP,
    },
    "vera": {
        "id":     "vera",
        "nome":   VERA_NOME,
        "titulo": VERA_TITULO,
        "cor":    "rose",
        "inicial":"V",
        "sp":     VERA_SP,
    },
    "dasha": {
        "id":     "dasha",
        "nome":   DASHA_NOME,
        "titulo": DASHA_TITULO,
        "cor":    "violet",
        "inicial":"D",
        "sp":     DASHA_SP,
    },
    "mila": {
        "id":     "mila",
        "nome":   MILA_NOME,
        "titulo": MILA_TITULO,
        "cor":    "emerald",
        "inicial":"M",
        "sp":     MILA_SP,
    },
    "igor": {
        "id":     "igor",
        "nome":   IGOR_NOME,
        "titulo": IGOR_TITULO,
        "cor":    "sky",
        "inicial":"I",
        "sp":     IGOR_SP,
    },
}

# Histórico em memória por agent_id
_histories: dict[str, list[dict]] = {k: [] for k in AGENTS}


@router.get("/agents/{agent_id}", response_class=HTMLResponse)
async def agent_chat(request: Request, agent_id: str):
    require_auth(request)
    if agent_id not in AGENTS:
        return RedirectResponse("/dashboard")
    agent   = AGENTS[agent_id]
    history = _histories[agent_id]
    return templates.TemplateResponse("agent_chat.html", {
        "request": request,
        "agent":   agent,
        "history": history,
        "agents":  AGENTS,
    })


@router.post("/agents/{agent_id}/clear")
async def agent_clear(request: Request, agent_id: str):
    require_auth(request)
    if agent_id in _histories:
        _histories[agent_id] = []
    return RedirectResponse(f"/agents/{agent_id}", status_code=303)


@router.get("/agents/{agent_id}/stream")
async def agent_stream(request: Request, agent_id: str, msg: str = ""):
    require_auth(request)
    if agent_id not in AGENTS or not msg.strip():
        return HTMLResponse("", status_code=400)

    agent   = AGENTS[agent_id]
    history = _histories[agent_id]

    # Adiciona mensagem do usuário ao histórico
    history.append({"role": "user", "content": msg.strip()})

    async def event_generator():
        client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        full_response = []
        try:
            async with client.messages.stream(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=agent["sp"],
                messages=history[-20:],  # últimas 20 mensagens para contexto
            ) as stream:
                async for text in stream.text_stream:
                    if await request.is_disconnected():
                        break
                    full_response.append(text)
                    # Escapa para SSE: substitui newlines
                    safe = text.replace("\n", "\\n")
                    yield {"data": safe}
        except Exception as e:
            yield {"data": f"[ERRO: {e}]"}
        finally:
            # Salva resposta completa no histórico
            if full_response:
                history.append({"role": "assistant", "content": "".join(full_response)})
            yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())
