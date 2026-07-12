# Oralyse Wipe — Backend (LOTS 1-3)

Logiciel métier de traçabilité et de certification d'effacement sécurisé.

**Contrainte absolue :** ce logiciel n'accède **jamais** à un périphérique de
stockage. Il gère des données (clients, lots, supports) et importera des
rapports produits par la station d'effacement (ShredOS + nwipe). Aucun accès
`/dev/*`, aucun `subprocess`.

## Périmètre livré (LOT 1)

- Modèles SQLAlchemy 2.0 typés : `utilisateurs`, `clients`, `lots`, `supports`, `audit`
  (schéma SQL de la spécification, à l'identique — voir `docs/specification.md`).
- Migration Alembic initiale.
- **Journal d'audit chaîné par hash** (`app/services/audit_service.py`) :
  `hash_courant = SHA-256(horodatage|utilisateur|action|entite|entite_id|details|hash_precedent)`,
  genesis `"0"*64`. Toute écriture métier passe par ce service.
  `GET /api/v1/audit/verify` recalcule la chaîne entière et signale les ruptures.
- Authentification : mots de passe **argon2id**, jetons **JWT**, 3 rôles
  hiérarchiques (`TECHNICIEN` < `RESPONSABLE` < `ADMINISTRATEUR`).
- CRUD clients / lots / supports :
  - identifiants générés automatiquement : `CLI-0001`, `LOT-2026-0001`, `SUP-2026-000001` ;
  - **aucune suppression** : archivage (clients) ou changement de statut ; aucune
    route `DELETE` n'existe et les clés étrangères sont en `ON DELETE RESTRICT` ;
  - un support appartient obligatoirement à un lot ;
  - les statuts `EFFACE_VERIFIE` / `EFFACE_NON_VERIFIE` ne peuvent pas être posés
    à la main : seul l'import d'un rapport station (LOT 2) en fera foi.

## Périmètre livré (LOT 2) — import des rapports station

- Modèle `operations` + migration : chaque tentative d'effacement est conservée,
  échecs compris — une opération ne se modifie jamais, c'est une preuve.
- Contrat d'interface (`app/schemas/rapport.py`) : validation Pydantic **stricte**
  du rapport station (spécification §4) — champ inconnu, champ manquant ou
  `format_version` inattendue → rejet complet, jamais d'import partiel.
- Service d'import (`app/services/import_service.py`) :
  - rattachement au support par `code_interne` ; support inconnu → erreur
    explicite, aucune création à l'aveugle ;
  - intégrité : SHA-256(`log_brut`) recalculé et comparé à `log_sha256` — toute
    divergence rejette le rapport ;
  - transitions de statut strictes :
    `SUCCES + verification.ok` → `EFFACE_VERIFIE` ·
    `SUCCES` sans vérification → `EFFACE_NON_VERIFIE` ·
    `ECHEC` / `INTERROMPU` / vérification négative → `ECHEC` ·
    HPA ou DCO détecté → `NON_EFFACABLE` (prime sur tout) ;
  - idempotent : même support + même hash de log = même opération, pas de doublon ;
  - chaque import est journalisé dans l'audit chaîné.
- Routes : `POST /api/v1/operations/import` (upload JSON), `GET /api/v1/operations`
  (filtres lot / client / support / résultat / technicien / période),
  `GET /api/v1/operations/{id}` (avec log brut),
  `GET /api/v1/supports/recherche?q=` (numéro de série, code interne, modèle).

## Périmètre livré (LOT 3) — certificats PDF signés + vérification QR

- Modèle `certificats` + migration : UNIQUE sur `operation_id` (un certificat
  par opération), token de vérification `secrets.token_urlsafe(32)`.
- **Règle bloquante** (`certificat_service.verifier_eligibilite`) : certificat
  généré UNIQUEMENT si `resultat = SUCCES` ET `verification_ok = 1`. ECHEC,
  INTERROMPU, absence de vérification, vérification négative → refus explicite,
  chacun couvert par un test dédié.
- **Signature Ed25519** (`signature_service`) : clé privée hors dépôt git
  (chemin `ORALYSE_CLE_PRIVEE_CHEMIN`, générée au premier usage, chmod 600),
  clé publique exposée sur `GET /api/v1/certificats/cle-publique`. On signe le
  SHA-256 des données certifiées (JSON canonique), pas le PDF : le PDF se
  régénère, les données non.
- **PDF** (`app/pdf/generator.py`, ReportLab — pur Python, pas de dépendance
  système contrairement à WeasyPrint) : palette vert forêt `#1a3a2e` / cuivre
  `#b87333`, toutes les données certifiées, QR code vectoriel, mention
  obligatoire NIST SP 800-88 Rev. 1 en pied de page. Aucune mention
  « juridiquement valide », nulle part.
- **Page publique `GET /verif/{token}`** (sans authentification) : reconstruit
  les données depuis la base, recalcule le hash et vérifie la signature Ed25519
  À CHAQUE APPEL. Numéro de série partiellement masqué, aucune autre donnée.
  Toute altération en base → certificat affiché INVALIDE.
- Numérotation `CERT-2026-000001`, génération auditée, téléchargement
  `GET /api/v1/certificats/{id}/pdf` (avec régénération du fichier si perdu).

## Périmètre livré (LOT 4, partie backend) — dashboard

- `GET /api/v1/dashboard` : agrégations 100 % SQL — supports effacés
  (jour/7 j/30 j, uniquement si le statut final du support l'atteste), capacité
  totale effacée, durée moyenne, taux de réussite, répartitions par technologie
  et par statut.
- `GET /api/v1/dashboard/a-traiter` : les supports `ECHEC` et `NON_EFFACABLE`.
- Règle renforcée (spécification §1.6) : un support `ECHEC` ou `NON_EFFACABLE`
  ne peut pas produire de certificat, même si un rapport annonce SUCCES.

Le frontend (LOT 4) vit dans `../frontend/`.

## Architecture

```
api/v1/     routes FastAPI — aucune logique, aucun SQL
services/   logique métier — ne connaît pas HTTP (exceptions métier de core/exceptions.py)
models/     ORM SQLAlchemy
schemas/    Pydantic v2 (entrées/sorties API)
core/       argon2 + JWT + exceptions
```

## Lancer

Prérequis : Python 3.11+, [uv](https://docs.astral.sh/uv/).

```bash
cd backend
uv sync                      # crée .venv et installe les dépendances

# Configuration (variables d'environnement, préfixe ORALYSE_) :
export ORALYSE_DATABASE_URL="sqlite:///./oralyse.db"          # défaut
export ORALYSE_JWT_SECRET="une-valeur-secrete-forte"          # OBLIGATOIRE en production
export ORALYSE_ADMIN_INITIAL_MOT_DE_PASSE="un-mot-de-passe"   # premier démarrage

uv run alembic upgrade head  # crée le schéma
uv run uvicorn app.main:app --reload
```

Au premier démarrage, si la table `utilisateurs` est vide, un compte
`ADMINISTRATEUR` est créé (`ORALYSE_ADMIN_INITIAL_IDENTIFIANT`, défaut `admin`).
Changez son mot de passe immédiatement.

API documentée sur <http://127.0.0.1:8000/docs>.

## Tests

```bash
cd backend
uv run pytest --cov=app/services --cov-report=term
```

102 tests (unitaires : chaînage d'audit, détection de rupture/suppression/réécriture,
numérotation, import — transitions et rejets, signature Ed25519, certificats —
tous les cas de refus ; intégration : auth + rôles, CRUD complet, absence totale
de suppression, upload de rapports, génération/téléchargement de certificats,
page publique de vérification, altération → invalide). Couverture `services/` : 96 %.

## Notes de sécurité

- Le journal d'audit détecte les altérations a posteriori (chaînage de hash) ;
  il ne les empêche pas. Prévoir l'export append-only périodique hors machine
  (voir spécification §1.3, lots suivants).
- SQLite : `PRAGMA foreign_keys=ON` est activé sur chaque connexion par
  `app/database.py` — sans lui, `ON DELETE RESTRICT` serait ignoré.
