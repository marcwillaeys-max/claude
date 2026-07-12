# Oralyse Wipe — Backend (LOT 1)

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

Non inclus (lots suivants) : import des rapports, certificats PDF, dashboard, frontend.

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

47 tests (unitaires : chaînage d'audit, détection de rupture/suppression/réécriture,
numérotation ; intégration : auth + rôles, CRUD complet, absence totale de
suppression). Couverture `services/` : 93 %.

## Notes de sécurité

- Le journal d'audit détecte les altérations a posteriori (chaînage de hash) ;
  il ne les empêche pas. Prévoir l'export append-only périodique hors machine
  (voir spécification §1.3, lots suivants).
- SQLite : `PRAGMA foreign_keys=ON` est activé sur chaque connexion par
  `app/database.py` — sans lui, `ON DELETE RESTRICT` serait ignoré.
