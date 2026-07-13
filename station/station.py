"""Orchestrateur de la station : inventaire → sécurité → effacement → vérif → rapport.

Usage (en root, sur la station, hors réseau) :
    sudo python3 -m station.station --peripherique /dev/sdX --code-interne SUP-2026-000123

L'ordre est impératif et non contournable :
    1. garde-fou 2 : le périphérique est un bloc /dev/* explicite et existant ;
    2. inventaire (lecture seule) ;
    3. garde-fou 1 : refus si périphérique système ;
    4. si HPA/DCO détecté et non résolu → NON_EFFACABLE, on n'efface pas ;
    5. garde-fou 3 : saisie manuelle du numéro de série complet ;
    6. effacement selon la technologie ;
    7. vérification post-effacement par relecture ;
    8. rapport JSON signable, écrit sur disque.
"""
from __future__ import annotations

import argparse
import sys
import time

from station import effacement as mod_effacement
from station import inventaire as mod_inventaire
from station import rapport as mod_rapport
from station import securite
from station import verification as mod_verification


def executer_station(
    peripherique: str,
    code_interne: str,
    saisie_confirmation: str | None,
    chemin_rapport: str,
    autoriser_hpa_dco: bool = False,
    demander_interactif: bool = True,
) -> dict:
    """Retourne le rapport (dict). Lève securite.RefusSecurite en cas de refus.

    saisie_confirmation : si fourni (tests, automatisation contrôlée), utilisé au
    lieu de l'invite interactive. En usage normal, laisser None → saisie clavier.
    """
    # 1. Garde-fou 2 — whitelist explicite.
    securite.verifier_peripherique_bloc(peripherique)

    # 2. Inventaire (lecture seule).
    inventaire = mod_inventaire.inventorier(peripherique)

    # 3. Garde-fou 1 — refus si système.
    securite.verifier_non_systeme(peripherique)

    # 4. HPA / DCO non résolus → NON_EFFACABLE, on n'efface pas.
    if (inventaire.get("hpa_detecte") or inventaire.get("dco_detecte")) and not autoriser_hpa_dco:
        raise securite.RefusSecurite(
            f"REFUS : zone masquée détectée (HPA={inventaire.get('hpa_detecte')}, "
            f"DCO={inventaire.get('dco_detecte')}) sur {peripherique}. Des secteurs peuvent "
            "échapper à l'effacement → support NON EFFAÇABLE de façon fiable, destruction physique."
        )

    # 5. Garde-fou 3 — confirmation par numéro de série complet.
    numero_serie = inventaire.get("numero_serie")
    if saisie_confirmation is not None:
        securite.confirmer_numero_serie(numero_serie, saisie_confirmation)
    elif demander_interactif:
        securite.demander_confirmation_interactive(numero_serie, peripherique)
    else:
        raise securite.RefusSecurite("REFUS : aucune confirmation fournie.")

    # 6. Effacement.
    debut = mod_rapport.horodatage_iso()
    horloge = time.monotonic()
    resultat = mod_effacement.choisir_et_effacer(inventaire["technologie"], peripherique)
    duree = int(time.monotonic() - horloge)
    fin = mod_rapport.horodatage_iso()

    # 7. Vérification post-effacement (uniquement si l'effacement a réussi).
    if resultat.resultat == "SUCCES":
        verification = mod_verification.verifier(peripherique, resultat.motif_pattern)
    else:
        verification = mod_verification.ResultatVerification(
            faite=False, ok=False, secteurs_testes=0, zones=[], anomalies=["Effacement non réussi."]
        )

    # 8. Rapport.
    rapport = mod_rapport.construire_rapport(
        code_interne=code_interne,
        inventaire=inventaire,
        effacement=resultat,
        verification=verification,
        debut=debut,
        fin=fin,
        duree_secondes=duree,
    )
    mod_rapport.ecrire_rapport(rapport, chemin_rapport)
    return rapport


def principal(argv: list[str] | None = None) -> int:
    analyseur = argparse.ArgumentParser(
        description="Station d'effacement Oralyse — À N'EXÉCUTER QUE SUR LA STATION DÉDIÉE."
    )
    analyseur.add_argument("--peripherique", required=True, help="Chemin /dev/* explicite (ex: /dev/sdb)")
    analyseur.add_argument("--code-interne", required=True, help="Code interne du support (ex: SUP-2026-000123)")
    analyseur.add_argument("--rapport", default=None, help="Chemin du rapport JSON de sortie")
    analyseur.add_argument(
        "--autoriser-hpa-dco",
        action="store_true",
        help="Effacer malgré HPA/DCO (seulement après désactivation manuelle vérifiée)",
    )
    arguments = analyseur.parse_args(argv)

    chemin = arguments.rapport or f"rapport_{arguments.code_interne}.json"
    try:
        rapport = executer_station(
            peripherique=arguments.peripherique,
            code_interne=arguments.code_interne,
            saisie_confirmation=None,
            chemin_rapport=chemin,
            autoriser_hpa_dco=arguments.autoriser_hpa_dco,
        )
    except securite.RefusSecurite as refus:
        print(f"\n{refus}", file=sys.stderr)
        return 2
    except mod_effacement.TechnologieNonEffacable as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 3

    operation = rapport["operation"]
    verification = rapport["verification"]
    print(f"\nRapport écrit : {chemin}")
    print(f"Résultat effacement : {operation['resultat']} ({operation['methode']})")
    print(f"Vérification : faite={verification['faite']} ok={verification['ok']}")
    return 0 if operation["resultat"] == "SUCCES" and verification["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(principal())
