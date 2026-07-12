"""Certificat d'effacement au format PDF (ReportLab).

Choix ReportLab plutôt que WeasyPrint : pur Python (aucune dépendance système
Pango/Cairo), rendu déterministe, largement suffisant pour un document d'une
page à mise en page fixe. Le QR code est dessiné en vectoriel depuis la
matrice de `qrcode`, sans dépendance image.

Le PDF est une REPRÉSENTATION des données certifiées : la preuve est la
signature Ed25519 sur le hash des données, vérifiable via l'URL du QR.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import qrcode
from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas

from app.config import get_settings

if TYPE_CHECKING:
    from app.models.certificat import Certificat

VERT_FORET = HexColor("#1a3a2e")
CUIVRE = HexColor("#b87333")
GRIS_TEXTE = HexColor("#333333")
GRIS_CLAIR = Color(0, 0, 0, alpha=0.06)

MENTION_PIED_DE_PAGE = (
    "Certificat d'effacement sécurisé. Opération réalisée conformément aux "
    "recommandations NIST SP 800-88 Rev. 1. Vérifiable sur {url}."
)


def _capacite_lisible(octets: int | None) -> str:
    if octets is None:
        return "—"
    valeur = float(octets)
    for unite in ("octets", "Ko", "Mo", "Go", "To", "Po"):
        if valeur < 1000 or unite == "Po":
            return f"{valeur:.0f} {unite}" if unite == "octets" else f"{valeur:.2f} {unite}"
        valeur /= 1000
    return f"{octets} octets"


def _duree_lisible(secondes: int | None) -> str:
    if secondes is None:
        return "—"
    heures, reste = divmod(secondes, 3600)
    minutes, sec = divmod(reste, 60)
    return f"{heures} h {minutes:02d} min {sec:02d} s"


def _dessiner_qr(canvas: Canvas, url: str, x: float, y: float, taille: float) -> None:
    """QR vectoriel : un rectangle par module, aucun fichier image."""
    qr = qrcode.QRCode(border=0, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(url)
    qr.make(fit=True)
    matrice = qr.get_matrix()
    pas = taille / len(matrice)
    canvas.setFillColor(VERT_FORET)
    for ligne, cellules in enumerate(matrice):
        for colonne, actif in enumerate(cellules):
            if actif:
                canvas.rect(x + colonne * pas, y + taille - (ligne + 1) * pas, pas, pas, stroke=0, fill=1)


def generer_pdf(chemin: str, donnees: dict, certificat: "Certificat") -> None:
    settings = get_settings()
    url_verif = f"{settings.base_url_verification}/verif/{certificat.token_verif}"
    largeur, hauteur = A4
    marge = 18 * mm
    canvas = Canvas(chemin, pagesize=A4)
    canvas.setTitle(f"Certificat d'effacement {donnees['numero_cert']}")
    canvas.setAuthor("Oralyse SAS")

    # ── Bandeau d'en-tête ────────────────────────────────────────────────
    canvas.setFillColor(VERT_FORET)
    canvas.rect(0, hauteur - 34 * mm, largeur, 34 * mm, stroke=0, fill=1)
    # « Logo » typographique sobre.
    canvas.setFillColor(white)
    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawString(marge, hauteur - 15 * mm, "ORALYSE")
    canvas.setFillColor(CUIVRE)
    canvas.setFont("Helvetica", 9)
    canvas.drawString(marge, hauteur - 20 * mm, "Traçabilité & effacement sécurisé de supports de données")
    canvas.setFillColor(white)
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawString(marge, hauteur - 28.5 * mm, "CERTIFICAT D'EFFACEMENT SÉCURISÉ")
    canvas.setFillColor(CUIVRE)
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawRightString(largeur - marge, hauteur - 28.5 * mm, donnees["numero_cert"])

    # ── Sections ─────────────────────────────────────────────────────────
    y = hauteur - 45 * mm

    def section(titre: str) -> None:
        nonlocal y
        canvas.setFillColor(CUIVRE)
        canvas.setFont("Helvetica-Bold", 10.5)
        canvas.drawString(marge, y, titre.upper())
        canvas.setStrokeColor(CUIVRE)
        canvas.setLineWidth(0.8)
        canvas.line(marge, y - 1.8 * mm, largeur - marge, y - 1.8 * mm)
        y -= 8 * mm

    def ligne(libelle: str, valeur: str, alterne: bool) -> None:
        nonlocal y
        if alterne:
            canvas.setFillColor(GRIS_CLAIR)
            canvas.rect(marge, y - 1.6 * mm, largeur - 2 * marge, 5.6 * mm, stroke=0, fill=1)
        canvas.setFillColor(VERT_FORET)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(marge + 1.5 * mm, y, libelle)
        canvas.setFillColor(GRIS_TEXTE)
        canvas.setFont("Helvetica", 9)
        canvas.drawString(marge + 58 * mm, y, valeur)
        y -= 5.6 * mm

    def bloc(titre: str, lignes: list[tuple[str, str]]) -> None:
        nonlocal y
        section(titre)
        for indice, (libelle, valeur) in enumerate(lignes):
            ligne(libelle, valeur, indice % 2 == 0)
        y -= 4 * mm

    client, lot = donnees["client"], donnees["lot"]
    support, operation = donnees["support"], donnees["operation"]

    bloc(
        "Client",
        [
            ("Raison sociale", client["raison_sociale"]),
            ("N° client", client["numero"]),
            ("N° de lot", f"{lot['numero']}  (réception : {lot['date_reception']})"),
        ],
    )
    bloc(
        "Support effacé",
        [
            ("Code interne", support["code_interne"]),
            ("N° de série", support["numero_serie"] or "non relevé"),
            ("Constructeur / modèle", f"{support['constructeur'] or '—'} / {support['modele'] or '—'}"),
            ("Capacité", _capacite_lisible(support["capacite_octets"])),
            ("Technologie", support["technologie"] or "—"),
        ],
    )
    bloc(
        "Opération d'effacement",
        [
            ("Méthode", operation["methode"]),
            ("Norme de référence", operation["norme_reference"]),
            ("Nombre de passes", str(operation["nb_passes"]) if operation["nb_passes"] else "—"),
            ("Début", operation["debut"]),
            ("Fin", operation["fin"] or "—"),
            ("Durée", _duree_lisible(operation["duree_secondes"])),
            ("Outil", operation["outil_version"] or "—"),
            ("Technicien", donnees["technicien"]),
        ],
    )
    bloc(
        "Vérification post-effacement",
        [
            (
                "Résultat",
                "CONFORME — relecture d'échantillons concluante"
                if operation["verification_ok"] == 1
                else "NON VÉRIFIÉ",
            ),
        ],
    )
    bloc(
        "Intégrité et signature",
        [
            ("SHA-256 du log", operation["log_sha256"]),
            ("Empreinte des données", certificat.contenu_sha256),
            ("Signature Ed25519", certificat.signature[:44] + "…"),
            ("Clé publique (id)", certificat.cle_publique_id),
            ("Généré le", donnees["genere_le"]),
        ],
    )

    # ── QR de vérification ───────────────────────────────────────────────
    taille_qr = 26 * mm
    _dessiner_qr(canvas, url_verif, largeur - marge - taille_qr, 24 * mm, taille_qr)
    canvas.setFillColor(GRIS_TEXTE)
    canvas.setFont("Helvetica", 6.5)
    canvas.drawRightString(largeur - marge, 21 * mm, "Scanner pour vérifier l'authenticité")

    # ── Pied de page — mention obligatoire, mot pour mot ────────────────
    canvas.setStrokeColor(VERT_FORET)
    canvas.setLineWidth(0.5)
    canvas.line(marge, 16 * mm, largeur - marge, 16 * mm)
    canvas.setFillColor(VERT_FORET)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(marge, 12 * mm, MENTION_PIED_DE_PAGE.format(url=url_verif)[:130])
    reste = MENTION_PIED_DE_PAGE.format(url=url_verif)[130:]
    if reste:
        canvas.drawString(marge, 8.5 * mm, reste)

    canvas.showPage()
    canvas.save()
