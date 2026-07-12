from __future__ import annotations

import hashlib
from pathlib import Path

from app.config import get_settings
from app.services import signature_service


def test_signature_et_verification() -> None:
    empreinte = hashlib.sha256(b"donnees certifiees").hexdigest()
    signature = signature_service.signer(empreinte)
    assert signature_service.verifier(empreinte, signature)


def test_donnees_alterees_signature_invalide() -> None:
    empreinte = hashlib.sha256(b"donnees certifiees").hexdigest()
    signature = signature_service.signer(empreinte)
    autre_empreinte = hashlib.sha256(b"donnees ALTEREES").hexdigest()
    assert not signature_service.verifier(autre_empreinte, signature)


def test_signature_corrompue_invalide() -> None:
    empreinte = hashlib.sha256(b"donnees").hexdigest()
    assert not signature_service.verifier(empreinte, "cGFzIHVuZSBzaWduYXR1cmU=")
    assert not signature_service.verifier(empreinte, "pas-du-base64-!!!")


def test_cle_creee_sur_disque_et_rechargee() -> None:
    signature_service.signer(hashlib.sha256(b"x").hexdigest())  # force la création
    chemin = Path(get_settings().cle_privee_chemin)
    assert chemin.exists()
    identifiant_avant = signature_service.cle_publique_id()
    # Rechargement depuis le fichier : même clé, même empreinte.
    signature_service._cache.clear()
    assert signature_service.cle_publique_id() == identifiant_avant


def test_cle_publique_pem_exposable() -> None:
    pem = signature_service.cle_publique_pem()
    assert pem.startswith("-----BEGIN PUBLIC KEY-----")
    assert len(signature_service.cle_publique_id()) == 16
