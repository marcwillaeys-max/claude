"""Signature Ed25519 des données certifiées.

- La clé privée vit dans un fichier HORS du dépôt git (chemin en configuration,
  motif exclu par .gitignore). Elle est générée au premier usage si absente.
- On signe le SHA-256 des données certifiées, pas le PDF : le PDF peut être
  régénéré à l'identique ou non, les données signées ne changent jamais.
- MVP sans PKI (spécification §1.4) : la clé publique est publiée et chaque
  vérification recalcule la signature. Évolution prévue : horodatage RFC 3161.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from app.config import get_settings

_logger = logging.getLogger("oralyse.signature")

_cache: dict[str, Ed25519PrivateKey] = {}


def _charger_ou_creer_cle() -> Ed25519PrivateKey:
    chemin = str(Path(get_settings().cle_privee_chemin).resolve())
    if chemin in _cache:
        return _cache[chemin]
    fichier = Path(chemin)
    if fichier.exists():
        cle = serialization.load_pem_private_key(fichier.read_bytes(), password=None)
        if not isinstance(cle, Ed25519PrivateKey):
            raise ValueError(f"{chemin} n'est pas une clé privée Ed25519")
    else:
        _logger.warning("Clé privée absente, génération d'une nouvelle clé Ed25519 dans %s", chemin)
        cle = Ed25519PrivateKey.generate()
        fichier.parent.mkdir(parents=True, exist_ok=True)
        fichier.write_bytes(
            cle.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
        os.chmod(fichier, 0o600)
    _cache[chemin] = cle
    return cle


def cle_publique() -> Ed25519PublicKey:
    return _charger_ou_creer_cle().public_key()


def cle_publique_pem() -> str:
    return cle_publique().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")


def cle_publique_id() -> str:
    """Empreinte courte identifiant la clé qui a signé (SHA-256 des octets bruts)."""
    brut = cle_publique().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    return hashlib.sha256(brut).hexdigest()[:16]


def signer(contenu_sha256: str) -> str:
    """Signe le hash hexadécimal des données certifiées. Retourne base64."""
    signature = _charger_ou_creer_cle().sign(contenu_sha256.encode("ascii"))
    return base64.b64encode(signature).decode("ascii")


def verifier(contenu_sha256: str, signature_b64: str) -> bool:
    try:
        cle_publique().verify(base64.b64decode(signature_b64), contenu_sha256.encode("ascii"))
        return True
    except (InvalidSignature, ValueError):
        return False
