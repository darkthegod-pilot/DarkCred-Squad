"""
Autenticação PIN para o painel web DarkCred.
Cookie assinado com itsdangerous, sessão de 8h.
"""
import os
from fastapi import Request, Response
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

_PIN     = os.environ.get("WEB_PIN", "42445")
_SECRET  = os.environ.get("SECRET_KEY", "darkcred-secret-2026-xHC03")
_COOKIE  = "darkcred_session"
_MAX_AGE = 28800  # 8h

_signer = URLSafeTimedSerializer(_SECRET)


def _sign() -> str:
    return _signer.dumps("authenticated")


def _verify(token: str) -> bool:
    try:
        _signer.loads(token, max_age=_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


def is_authenticated(request: Request) -> bool:
    token = request.cookies.get(_COOKIE, "")
    return _verify(token)


def require_auth(request: Request):
    """FastAPI dependency — redireciona /login se não autenticado."""
    if not is_authenticated(request):
        raise _LoginRequired()


class _LoginRequired(Exception):
    pass


def set_session(response: Response) -> None:
    response.set_cookie(
        key=_COOKIE,
        value=_sign(),
        httponly=True,
        max_age=_MAX_AGE,
        samesite="lax",
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(_COOKIE)


def check_pin(pin: str) -> bool:
    return pin.strip() == _PIN
