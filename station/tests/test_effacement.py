from __future__ import annotations

import pytest

from station import effacement
from station.tests.conftest import Simulateur


def test_technologie_inconnue_refusee() -> None:
    with pytest.raises(effacement.TechnologieNonEffacable):
        effacement.choisir_et_effacer("INCONNU", "/dev/sdb")


def test_hdd_zero_fill_succes(commandes_simulees: Simulateur) -> None:
    commandes_simulees.repondre_si(lambda c: c[0] == "nwipe" and "--version" not in c, sortie="wiped ok")
    commandes_simulees.repondre_si(lambda c: "--version" in c, sortie="nwipe 0.36")
    resultat = effacement.effacer_hdd("/dev/sdb")
    assert resultat.resultat == "SUCCES"
    assert resultat.methode == "nwipe_zero_fill"
    assert resultat.motif_pattern == 0


def test_hdd_echec_si_erreur_dans_sortie(commandes_simulees: Simulateur) -> None:
    commandes_simulees.repondre_si(
        lambda c: c[0] == "nwipe" and "--version" not in c, sortie="I/O error on sector 42"
    )
    resultat = effacement.effacer_hdd("/dev/sdb")
    assert resultat.resultat == "ECHEC"


def test_hdd_echec_si_code_non_nul(commandes_simulees: Simulateur) -> None:
    commandes_simulees.repondre_si(lambda c: c[0] == "nwipe" and "--version" not in c, code=1)
    assert effacement.effacer_hdd("/dev/sdb").resultat == "ECHEC"


def test_nvme_sanitize_verifie_le_log(commandes_simulees: Simulateur) -> None:
    """Un exit 0 ne suffit PAS : le sanitize-log doit confirmer le succès."""
    commandes_simulees.repondre_si(lambda c: c[:2] == ["nvme", "sanitize"], code=0)
    commandes_simulees.repondre_si(
        lambda c: c[:2] == ["nvme", "sanitize-log"], sortie="Sanitize completed successfully"
    )
    commandes_simulees.repondre_si(lambda c: "version" in c, sortie="nvme 2.0")
    resultat = effacement.effacer_nvme("/dev/nvme0n1")
    assert resultat.resultat == "SUCCES"
    assert resultat.methode == "nvme_sanitize_block_erase"


def test_nvme_exit0_mais_log_incomplet_bascule_repli(commandes_simulees: Simulateur) -> None:
    # sanitize renvoie 0 mais le log ne confirme pas → repli nvme format.
    commandes_simulees.repondre_si(lambda c: c[:2] == ["nvme", "sanitize"], code=0)
    commandes_simulees.repondre_si(
        lambda c: c[:2] == ["nvme", "sanitize-log"], sortie="Sanitize in progress (45%)"
    )
    commandes_simulees.repondre_si(lambda c: c[:2] == ["nvme", "format"], code=0)
    commandes_simulees.repondre_si(lambda c: "version" in c, sortie="nvme 2.0")
    resultat = effacement.effacer_nvme("/dev/nvme0n1")
    assert resultat.resultat == "SUCCES"
    assert resultat.methode == "nvme_format_crypto_erase"


def test_nvme_echec_total(commandes_simulees: Simulateur) -> None:
    commandes_simulees.repondre_si(lambda c: c[:2] == ["nvme", "sanitize"], code=1)
    commandes_simulees.repondre_si(lambda c: c[:2] == ["nvme", "format"], code=1)
    commandes_simulees.repondre_si(lambda c: "version" in c, sortie="nvme 2.0")
    assert effacement.effacer_nvme("/dev/nvme0n1").resultat == "ECHEC"


def test_ssd_sata_secure_erase_verifie_deverrouillage(commandes_simulees: Simulateur) -> None:
    commandes_simulees.repondre_si(lambda c: "--security-set-pass" in c, code=0)
    commandes_simulees.repondre_si(lambda c: "--security-erase-enhanced" in c, code=0)
    commandes_simulees.repondre_si(
        lambda c: c[0] == "hdparm" and "-I" in c, sortie="Security:\n\tnot\tenabled"
    )
    commandes_simulees.repondre_si(lambda c: "-V" in c, sortie="hdparm v9.60")
    resultat = effacement.effacer_ssd_sata("/dev/sdb")
    assert resultat.resultat == "SUCCES"
    assert resultat.methode == "hdparm_security_erase_enhanced"


def test_ssd_sata_reste_verrouille_bascule_blkdiscard(commandes_simulees: Simulateur) -> None:
    commandes_simulees.repondre_si(lambda c: "--security-set-pass" in c, code=0)
    commandes_simulees.repondre_si(lambda c: "--security-erase-enhanced" in c, code=0)
    # hdparm -I montre « enabled » sans « not » → disque resté verrouillé → repli.
    commandes_simulees.repondre_si(
        lambda c: c[0] == "hdparm" and "-I" in c, sortie="Security:\n\tenabled\n\tlocked"
    )
    commandes_simulees.repondre_si(lambda c: c[0] == "blkdiscard", code=0)
    commandes_simulees.repondre_si(lambda c: "-V" in c or "--version" in c, sortie="v")
    resultat = effacement.effacer_ssd_sata("/dev/sdb")
    assert resultat.resultat == "SUCCES"
    assert resultat.methode == "blkdiscard_secure"


def test_sed_crypto_erase(commandes_simulees: Simulateur) -> None:
    commandes_simulees.repondre_si(lambda c: c[0] == "sedutil-cli", code=0)
    resultat = effacement.effacer_sed("/dev/sdb")
    assert resultat.resultat == "SUCCES"
    assert resultat.methode == "sed_crypto_erase"
    # Crypto-erase : motif non déterministe → pas de vérification par relecture.
    assert resultat.motif_pattern is None


def test_aiguillage_par_technologie(commandes_simulees: Simulateur) -> None:
    commandes_simulees.par_defaut = commandes_simulees.reponses.get(
        "x", __import__("station.commandes", fromlist=["Resultat"]).Resultat(0, "ok", "")
    )
    for techno, methode_attendue in [
        ("HDD_SATA", "nwipe_zero_fill"),
        ("SAS", "nwipe_zero_fill"),
        ("USB", "nwipe_overwrite_zero"),
        ("SD", "nwipe_overwrite_zero"),
    ]:
        resultat = effacement.choisir_et_effacer(techno, "/dev/sdb")
        assert resultat.methode == methode_attendue
