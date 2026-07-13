# Oralyse Wipe — Scripts station (LOT 5)

⚠️ **CE CODE PEUT DÉTRUIRE DES DONNÉES DE FAÇON IRRÉVERSIBLE.**

Ces scripts tournent **en root**, sur une machine dédiée (ShredOS / Debian live),
**sans réseau**, sur des disques **clients**. Ils sont volontairement écrits pour
être ennuyeux, explicites et vérifiables. Aucune optimisation, aucune abstraction
inutile, refus par défaut partout.

Ils ne font PAS partie du logiciel métier (`backend/`, `frontend/`) : ils
produisent le fichier JSON que le logiciel métier importe ensuite (contrat
d'interface, spécification §4). Les deux systèmes ne communiquent que par ce fichier.

## Triple sécurité avant tout effacement

1. **Refus catégorique** si le périphérique porte le système racine, `/boot`, ou
   le support de démarrage. Détection croisée par plusieurs méthodes
   (`findmnt`, `lsblk`, comparaison de disque parent).
2. **Whitelist explicite** : le périphérique est passé en argument. Rien n'est
   jamais découvert puis effacé automatiquement.
3. **Confirmation par saisie manuelle** du numéro de série COMPLET du disque
   cible. Une réponse « oui / o / y » est refusée.

Après la commande d'effacement, le **statut renvoyé par le disque** est toujours
relu (`nvme sanitize-log`, `hdparm -I`) : un code de retour 0 ne prouve rien.

## Modules

| Fichier | Rôle |
|---------|------|
| `securite.py` | Les trois garde-fous. Refus par défaut. |
| `inventaire.py` | `lsblk`/`smartctl`/`nvme`/`hdparm` → dict. Détection HPA, DCO, SED. |
| `effacement.py` | Table de décision méthode ↔ technologie, vérification du statut disque. |
| `verification.py` | Relecture 100 premiers Mo + 100 derniers Mo + 1000 secteurs aléatoires. |
| `rapport.py` | Produit le JSON au format d'interface, avec `log_sha256`. |
| `station.py` | Orchestrateur : inventaire → sécurité → effacement → vérif → rapport. |

## Usage (sur la station uniquement)

```bash
sudo python3 -m station.station --peripherique /dev/sdX --code-interne SUP-2026-000123
```

Le script exige la saisie manuelle du numéro de série avant d'agir, et refuse
tout périphérique système.

## Tests

```bash
cd station && python3 -m pytest
```

`subprocess` est **entièrement mocké** : aucun test ne peut toucher un vrai
périphérique. Les cas de REFUS sont testés en priorité.
