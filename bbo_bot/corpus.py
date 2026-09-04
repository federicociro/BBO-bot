"""Carga el corpus y el canon como texto plano.

Sin chunking, sin embeddings, sin índice: son ~26k tokens y la ventana es de 1M.
Se lee una vez al arrancar — el prefijo tiene que ser byte a byte idéntico en
cada request o la caché no sirve de nada.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

TITULOS = {
    "00-manifesto-bbo": "Manifiesto BBO (Barcelona Bitcoin Only, 2023)",
    "01-crypto-anarchist-manifesto": "The Crypto Anarchist Manifesto (Timothy C. May, 1988)",
    "02-cypherpunks-manifesto": "A Cypherpunk's Manifesto (Eric Hughes, 1993)",
    "03-crypto-anarchy-virtual-communities": (
        "Crypto Anarchy and Virtual Communities (Timothy C. May, 1994)"
    ),
    "04-bitcoin-whitepaper": "Bitcoin: A Peer-to-Peer Electronic Cash System (Nakamoto, 2008)",
}


@lru_cache(maxsize=1)
def cargar(corpus_dir: Path, canon_path: Path, reglas_path: Path) -> str:
    """Corpus + reglas + canon en un solo bloque, con orden estable."""
    partes = ["# CORPUS FUNDACIONAL\n"]
    for md in sorted(corpus_dir.glob("*.md")):
        titulo = TITULOS.get(md.stem, md.stem)
        partes.append(f"\n## {titulo}\n\n{md.read_text(encoding='utf-8').strip()}\n")

    partes.append("\n\n# REGLAS DEL GRUPO (texto oficial, se citan verbatim)\n\n")
    partes.append(reglas_path.read_text(encoding="utf-8").strip())

    partes.append("\n\n# CANON — respuestas de la comunidad\n\n")
    partes.append(canon_path.read_text(encoding="utf-8").strip())
    partes.append("\n")
    return "".join(partes)
