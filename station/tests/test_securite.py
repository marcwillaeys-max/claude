"""Tests de sécurité — PRIORITÉ ABSOLUE. Les cas de REFUS d'abord."""
from __future__ import annotations

import stat

import pytest

from station import securite
from station.tests.conftest import Simulateur


# ── Garde-fou 3 : confirmation par numéro de série ──────────────────────────


def test_confirmation_oui_interdite() -> None:
    for reponse in ("oui", "o", "y", "yes", "OK", "1", "true"):
        with pytest.raises(securite.RefusSecurite, match="interdite"):
            securite.confirmer_numero_serie("WD-WCC4E1234567", reponse)


def test_confirmation_mauvais_numero_refusee() -> None:
    with pytest.raises(securite.RefusSecurite, match="ne correspond pas"):
        securite.confirmer_numero_serie("WD-WCC4E1234567", "WD-AUTRE-9999999")


def test_confirmation_numero_absent_refusee() -> None:
    with pytest.raises(securite.RefusSecurite, match="destruction physique"):
        securite.confirmer_numero_serie("", "peu importe")
    with pytest.raises(securite.RefusSecurite):
        securite.confirmer_numero_serie(None, "peu importe")  # type: ignore[arg-type]


def test_confirmation_exacte_acceptee() -> None:
    # Ne lève pas.
    securite.confirmer_numero_serie("WD-WCC4E1234567", "WD-WCC4E1234567")
    securite.confirmer_numero_serie("WD-WCC4E1234567", "  WD-WCC4E1234567  ")


def test_confirmation_sensible_a_la_casse() -> None:
    with pytest.raises(securite.RefusSecurite):
        securite.confirmer_numero_serie("WD-ABC123", "wd-abc123")


# ── Garde-fou 2 : whitelist explicite ───────────────────────────────────────


def test_refus_chemin_hors_dev() -> None:
    with pytest.raises(securite.RefusSecurite, match="chemin /dev/"):
        securite.verifier_peripherique_bloc("sdb")
    with pytest.raises(securite.RefusSecurite, match="chemin /dev/"):
        securite.verifier_peripherique_bloc("/home/user/fichier")


def test_refus_motif_glob() -> None:
    with pytest.raises(securite.RefusSecurite, match="motif"):
        securite.verifier_peripherique_bloc("/dev/sd*")


def test_refus_peripherique_inexistant() -> None:
    with pytest.raises(securite.RefusSecurite, match="n'existe pas"):
        securite.verifier_peripherique_bloc("/dev/nexiste_pas_1234")


def test_refus_non_bloc(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    fichier = tmp_path / "faux"
    fichier.write_text("pas un disque")
    vrai_stat = securite.os.stat
    monkeypatch.setattr(securite.os.path, "exists", lambda p: True if p == "/dev/regfile" else False)
    # N'intercepter QUE le chemin cible : sinon pytest casse à son propre teardown.
    monkeypatch.setattr(
        securite.os,
        "stat",
        lambda p, **k: fichier.stat() if p == "/dev/regfile" else vrai_stat(p, **k),
    )
    with pytest.raises(securite.RefusSecurite, match="type bloc"):
        securite.verifier_peripherique_bloc("/dev/regfile")


def test_bloc_valide_accepte(monkeypatch: pytest.MonkeyPatch) -> None:
    vrai_stat = securite.os.stat
    monkeypatch.setattr(securite.os.path, "exists", lambda p: p == "/dev/sdb")

    class FauxStat:
        st_mode = stat.S_IFBLK | 0o660

    monkeypatch.setattr(
        securite.os, "stat", lambda p, **k: FauxStat() if p == "/dev/sdb" else vrai_stat(p, **k)
    )
    securite.verifier_peripherique_bloc("/dev/sdb")  # ne lève pas


# ── Garde-fou 1 : refus des périphériques système ───────────────────────────


def test_refus_disque_systeme_via_findmnt(commandes_simulees: Simulateur) -> None:
    commandes_simulees.repondre_si(
        lambda c: c[0] == "findmnt",
        sortie="/dev/sda2 /\n/dev/sda1 /boot\n",
    )
    commandes_simulees.repondre_si(lambda c: c[0] == "lsblk" and "pkname" in c, sortie="sda\n")
    commandes_simulees.repondre_si(lambda c: c[0] == "lsblk", sortie='{"blockdevices": []}')
    # /dev/sda porte / et /boot → refus d'effacer /dev/sda.
    with pytest.raises(securite.RefusSecurite, match="système"):
        securite.verifier_non_systeme("/dev/sda")


def test_refus_partition_systeme(commandes_simulees: Simulateur) -> None:
    commandes_simulees.repondre_si(lambda c: c[0] == "findmnt", sortie="/dev/sda2 /\n")
    commandes_simulees.repondre_si(
        lambda c: c[0] == "lsblk" and "pkname" in c, sortie="sda\n"
    )
    commandes_simulees.repondre_si(lambda c: c[0] == "lsblk", sortie='{"blockdevices": []}')
    # /dev/sda2 est une partition ; son disque parent /dev/sda est système.
    with pytest.raises(securite.RefusSecurite):
        securite.verifier_non_systeme("/dev/sda2")


def test_refus_via_lsblk_json(commandes_simulees: Simulateur) -> None:
    commandes_simulees.repondre_si(lambda c: c[0] == "findmnt", sortie="")
    arbre = (
        '{"blockdevices":[{"name":"sda","path":"/dev/sda","mountpoint":null,'
        '"children":[{"name":"sda1","path":"/dev/sda1","mountpoint":"/boot"}]}]}'
    )
    commandes_simulees.repondre_si(lambda c: c[0] == "lsblk" and "-J" in c, sortie=arbre)
    with pytest.raises(securite.RefusSecurite, match="système"):
        securite.verifier_non_systeme("/dev/sda")


def test_disque_non_systeme_accepte(commandes_simulees: Simulateur) -> None:
    # /dev/sdb ne porte aucun montage critique ; /dev/sda est le disque système.
    commandes_simulees.repondre_si(lambda c: c[0] == "findmnt", sortie="/dev/sda2 /\n")
    commandes_simulees.repondre_si(
        lambda c: c[0] == "lsblk" and "-J" in c,
        sortie='{"blockdevices":[{"name":"sdb","path":"/dev/sdb","mountpoint":null}]}',
    )
    securite.verifier_non_systeme("/dev/sdb")  # ne lève pas


def test_refus_si_les_deux_sources_echouent_mais_montage_direct(commandes_simulees: Simulateur) -> None:
    # findmnt indique que /dev/sdb1 est monté sur / directement.
    commandes_simulees.repondre_si(lambda c: c[0] == "findmnt", sortie="/dev/sdb1 /\n")
    commandes_simulees.repondre_si(lambda c: c[0] == "lsblk" and "pkname" in c, sortie="sdb\n")
    commandes_simulees.repondre_si(lambda c: c[0] == "lsblk", sortie='{"blockdevices": []}')
    with pytest.raises(securite.RefusSecurite):
        securite.verifier_non_systeme("/dev/sdb1")


def test_disque_parent_nvme() -> None:
    assert securite._disque_parent_syntaxique("/dev/nvme0n1p3") == "/dev/nvme0n1"
    assert securite._disque_parent_syntaxique("/dev/sda3") == "/dev/sda"
    assert securite._disque_parent_syntaxique("/dev/mmcblk0p2") == "/dev/mmcblk0"
