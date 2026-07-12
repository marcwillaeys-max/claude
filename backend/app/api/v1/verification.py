"""Page publique de vérification des certificats — cible du QR code.

SANS authentification, volontairement : n'importe qui en possession du
certificat papier doit pouvoir vérifier son authenticité. La page ne
divulgue que le strict nécessaire (numéro de série partiellement masqué,
aucune donnée de contact, aucun log).
"""
from __future__ import annotations

from html import escape
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import certificat_service
from app.services.certificat_service import ResultatVerificationPublique

router = APIRouter(tags=["verification publique"])

_STYLE = """
body{font-family:Helvetica,Arial,sans-serif;background:#f4f4f2;color:#333;margin:0}
.carte{max-width:560px;margin:48px auto;background:#fff;border-radius:6px;
  box-shadow:0 2px 12px rgba(0,0,0,.08);overflow:hidden}
.entete{background:#1a3a2e;color:#fff;padding:20px 28px}
.entete h1{margin:0;font-size:17px}.entete p{margin:4px 0 0;color:#b87333;font-size:12px}
.statut{padding:18px 28px;font-size:20px;font-weight:bold}
.valide{color:#1a3a2e;background:#e8f2ec}.invalide{color:#8a1f1f;background:#f9e8e8}
table{width:100%;border-collapse:collapse;margin:0}
td{padding:10px 28px;font-size:14px;border-top:1px solid #eee}
td:first-child{color:#1a3a2e;font-weight:bold;width:44%}
.pied{padding:16px 28px;font-size:11px;color:#777}
"""


def _page(titre_statut: str, classe: str, lignes: list[tuple[str, str]], raison: str | None) -> str:
    corps_tableau = "".join(
        f"<tr><td>{escape(libelle)}</td><td>{escape(valeur)}</td></tr>" for libelle, valeur in lignes
    )
    detail_raison = f"<p>{escape(raison)}</p>" if raison else ""
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Vérification de certificat — Oralyse</title><style>{_STYLE}</style></head>
<body><div class="carte">
<div class="entete"><h1>ORALYSE — Vérification de certificat</h1>
<p>Effacement sécurisé selon les recommandations NIST SP 800-88 Rev. 1</p></div>
<div class="statut {classe}">{escape(titre_statut)}</div>
<table>{corps_tableau}</table>
<div class="pied">{detail_raison}
<p>La signature Ed25519 des données certifiées est recalculée à chaque consultation.</p>
</div></div></body></html>"""


def _rendre(resultat: ResultatVerificationPublique) -> HTMLResponse:
    if not resultat.valide:
        lignes = [("Certificat", resultat.numero_cert)] if resultat.numero_cert else []
        return HTMLResponse(
            _page("✗ CERTIFICAT INVALIDE", "invalide", lignes, resultat.raison),
            status_code=404 if resultat.raison == "Certificat introuvable" else 200,
        )
    lignes = [
        ("Certificat", resultat.numero_cert or ""),
        ("Client", resultat.client or ""),
        ("Date de l'opération", resultat.date_operation or ""),
        ("Certificat généré le", resultat.genere_le or ""),
        ("N° de série du support", resultat.numero_serie_masque or ""),
        ("Méthode d'effacement", resultat.methode or ""),
        ("Vérification post-effacement", resultat.resultat_verification or ""),
    ]
    return HTMLResponse(_page("✓ CERTIFICAT VALIDE", "valide", lignes, None))


@router.get("/verif/{token}", response_class=HTMLResponse)
def verifier_certificat(token: str, db: Annotated[Session, Depends(get_db)]) -> HTMLResponse:
    return _rendre(certificat_service.verifier_token(db, token))
