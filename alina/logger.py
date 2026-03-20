"""
Sistema de Logging — Alina Pretrov
Registra todas as operações em arquivo diário.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path


def configurar_logger(nome: str = "alina") -> logging.Logger:
    """Configura e retorna o logger da aplicação."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logger = logging.getLogger(nome)

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Handler para arquivo diário
    nome_arquivo = log_dir / f"alina_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(nome_arquivo, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# Logger global da aplicação
log = configurar_logger()
