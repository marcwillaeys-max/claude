# ORALYSE WIPE — Spécification & prompts Claude Code

**Projet :** logiciel de traçabilité et de certification d'effacement sécurisé
**Commanditaire :** Oralyse SAS
**Version :** 1.0
**Usage :** chaque section « PROMPT LOT N » se colle directement dans Claude Code, une session par lot.

---

## 0. Principes fondateurs (à lire avant tout)

### 0.1 Deux logiciels, pas un

Le projet initial mélangeait deux systèmes de nature totalement différente. On les sépare :

|            | A. Station d'effacement                  | B. Logiciel métier                                |
|------------|------------------------------------------|---------------------------------------------------|
| Rôle       | Efface réellement les disques            | Gère clients, lots, historique, certificats       |
| Privilèges | root, accès matériel                     | aucun accès disque                                 |
| Risque     | destruction irréversible de données      | un PDF mal formaté                                 |
| Décision   | NE PAS L'ÉCRIRE → ShredOS + nwipe        | **C'EST LE PROJET**                                |

**Règle absolue :** le logiciel métier ne touche jamais un périphérique de stockage. Il lit des fichiers de log produits par la station. Cette séparation est la principale garantie de sécurité de l'architecture.

### 0.2 Ce qu'on n'écrit pas

- Aucun algorithme d'effacement (on utilise nwipe, hdparm, nvme-cli).
- Aucune interface graphique pilotant un effacement depuis le logiciel métier.
- Aucun accès direct à `/dev/*` depuis le backend web.

### 0.3 Chaîne de traitement cible

```
┌─────────────────────────────┐
│ STATION D'EFFACEMENT        │   Machine dédiée, hors réseau
│ ShredOS (clé USB bootable)  │
│   ├─ smartctl / nvme-cli    │   → inventaire du support
│   ├─ nwipe / nvme sanitize  │   → effacement
│   └─ vérification post-wipe │   → relecture d'échantillons
└──────────────┬──────────────┘
               │  fichier JSON signé (1 par support)
               ▼
┌─────────────────────────────┐
│ LOGICIEL MÉTIER (ce projet) │   PC bureau, aucun disque client branché
│   FastAPI + SQLite          │
│   React (navigateur)        │
│   ├─ Import des rapports    │
│   ├─ Clients / Lots         │
│   ├─ Historique chaîné      │
│   ├─ Certificat PDF + QR    │
│   └─ Dashboard              │
└─────────────────────────────┘
```

---

## 1. Corrections apportées au cahier des charges initial

Ces 8 points sont des erreurs ou des manques du prompt d'origine. Ils sont intégrés aux lots.

### 1.1 Vérification post-effacement — MANQUANT, CRITIQUE

Le cahier des charges initial ne demandait aucune vérification. Sans elle, le certificat atteste une intention d'effacer, pas un résultat.

→ Après effacement : relire au minimum 1000 secteurs aléatoires + les 100 premiers Mo + les 100 derniers Mo, vérifier qu'ils correspondent au motif attendu. Le résultat de cette vérification est un champ obligatoire du rapport.

### 1.2 hdparm --security-erase sur SSD — MAUVAISE RECOMMANDATION

Certains firmwares SSD acceptent la commande et ne font rien. Ordre de préférence correct :

| Technologie          | Méthode 1                              | Méthode 2 (repli)              | Méthode 3           |
|----------------------|----------------------------------------|--------------------------------|---------------------|
| HDD SATA/SAS         | nwipe 1 passe zéros (NIST 800-88 Clear)| 3 passes si exigé par le client| —                   |
| SSD SATA             | hdparm --security-erase-enhanced       | blkdiscard -s (secure discard) | overwrite nwipe + vérif |
| NVMe                 | nvme sanitize (block erase)            | nvme format -s 1 (crypto erase)| nvme format -s 2    |
| SED / auto-chiffrant | crypto-erase (révocation de clé)       | —                              | —                   |
| Clé USB / SD         | overwrite nwipe + vérification         | —                              | —                   |

Toujours vérifier le code de retour ET le statut renvoyé par le disque (`nvme sanitize-log`, `hdparm -I`). Un exit 0 ne prouve rien.

### 1.3 Historique « impossible à modifier » — CONTRADICTION

Un fichier SQLite s'édite avec n'importe quel éditeur.

→ **Chaînage de hash :** chaque enregistrement d'audit contient le SHA-256 du précédent. Toute modification rompt la chaîne et devient détectable. Un endpoint `/audit/verify` recalcule la chaîne entière.
→ Export append-only périodique hors machine (fichier `.jsonl` horodaté).

### 1.4 Signature numérique — DÉCORATIVE SANS PKI

Une signature auto-générée sans autorité de certification n'a aucune valeur probante.

→ **MVP :** signature Ed25519 avec clé privée du poste + clé publique publiée. Honnête, vérifiable, suffisant.
→ **Évolution :** horodatage qualifié RFC 3161 (quelques euros/an, valeur juridique réelle).

### 1.5 HPA / DCO / secteurs réalloués — NON TRAITÉ

Des zones du disque peuvent être masquées au système et échapper à l'effacement.

→ Détecter HPA/DCO (`hdparm -N`, `hdparm --dco-identify`), les désactiver avant effacement, ou marquer le support « non effaçable de façon fiable → destruction physique ».

### 1.6 Gestion de l'échec — NON TRAITÉ

Statuts possibles d'un support, obligatoires dans le modèle :

`EN_ATTENTE · EN_COURS · EFFACE_VERIFIE · EFFACE_NON_VERIFIE · ECHEC · NON_EFFACABLE · DETRUIT_PHYSIQUEMENT`

Un support en `ECHEC` ou `NON_EFFACABLE` ne peut pas générer de certificat d'effacement. Il bascule vers le circuit destruction physique.

### 1.7 Certificat « juridiquement exploitable » — FORMULATION À ABANDONNER

Le logiciel ne peut pas garantir cela seul.

→ Formulation retenue sur le document : « Certificat d'effacement sécurisé — opération réalisée conformément aux recommandations NIST SP 800-88 Rev. 1 ». Jamais « juridiquement valide ».

### 1.8 Tauri au démarrage — COMPLEXITÉ INUTILE

→ **MVP :** React servi dans le navigateur. Tauri n'apporte rien tant que le logiciel ne pilote pas le matériel. À reconsidérer en v2 si besoin d'un exécutable distribuable.

---

## 2. Schéma de base de données

```sql
-- ═══════════════════════════════════════════════════
-- CLIENTS
-- ═══════════════════════════════════════════════════
CREATE TABLE clients (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_client     TEXT    NOT NULL UNIQUE,   -- ex: CLI-0001
    raison_sociale    TEXT    NOT NULL,
    siret             TEXT,
    adresse           TEXT,
    code_postal       TEXT,
    ville             TEXT,
    contact_nom       TEXT,
    contact_email     TEXT,
    contact_telephone TEXT,
    commentaires      TEXT,
    cree_le           TEXT    NOT NULL,          -- ISO-8601 UTC
    cree_par          INTEGER NOT NULL REFERENCES utilisateurs(id),
    archive           INTEGER NOT NULL DEFAULT 0 CHECK (archive IN (0,1))
);
CREATE INDEX idx_clients_raison ON clients(raison_sociale);

-- ═══════════════════════════════════════════════════
-- LOTS  (un lot = une prise en charge de matériel)
-- ═══════════════════════════════════════════════════
CREATE TABLE lots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_lot      TEXT    NOT NULL UNIQUE,     -- ex: LOT-2026-0042
    client_id       INTEGER NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
    date_reception  TEXT    NOT NULL,
    technicien_id   INTEGER NOT NULL REFERENCES utilisateurs(id),
    statut          TEXT    NOT NULL DEFAULT 'OUVERT'
                    CHECK (statut IN ('OUVERT','EN_COURS','TERMINE','CLOTURE')),
    nb_supports_annonce INTEGER,
    commentaires    TEXT,
    cree_le         TEXT    NOT NULL,
    cloture_le      TEXT
);
CREATE INDEX idx_lots_client ON lots(client_id);
CREATE INDEX idx_lots_statut ON lots(statut);
-- ON DELETE RESTRICT : on n'efface jamais un client qui a des lots.
-- La traçabilité prime sur le confort d'administration.

-- ═══════════════════════════════════════════════════
-- SUPPORTS  (un disque physique)
-- ═══════════════════════════════════════════════════
CREATE TABLE supports (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    lot_id            INTEGER NOT NULL REFERENCES lots(id) ON DELETE RESTRICT,
    code_interne      TEXT    NOT NULL UNIQUE,   -- ex: SUP-2026-000178 → QR code
    numero_serie      TEXT,                      -- peut être illisible sur disque HS
    modele            TEXT,
    constructeur      TEXT,
    capacite_octets   INTEGER,
    technologie       TEXT CHECK (technologie IN
                      ('HDD_SATA','SSD_SATA','SSD_NVME','SAS','USB','SD','SED','INCONNU')),
    interface         TEXT,
    smart_json        TEXT,                      -- dump SMART brut (JSON)
    sante             TEXT CHECK (sante IN ('OK','DEGRADE','DEFAILLANT','INCONNU')),
    hpa_detecte       INTEGER DEFAULT 0,
    dco_detecte       INTEGER DEFAULT 0,
    statut            TEXT    NOT NULL DEFAULT 'EN_ATTENTE'
                      CHECK (statut IN ('EN_ATTENTE','EN_COURS','EFFACE_VERIFIE',
                                        'EFFACE_NON_VERIFIE','ECHEC','NON_EFFACABLE',
                                        'DETRUIT_PHYSIQUEMENT')),
    destination       TEXT CHECK (destination IN ('REEMPLOI','DESTRUCTION','VALORISATION')),
    cree_le           TEXT    NOT NULL
);
CREATE INDEX idx_supports_lot    ON supports(lot_id);
CREATE INDEX idx_supports_serie  ON supports(numero_serie);   -- recherche fréquente
CREATE INDEX idx_supports_statut ON supports(statut);
CREATE UNIQUE INDEX idx_supports_code ON supports(code_interne);
-- numero_serie NON UNIQUE volontairement :
--   - certains disques HS ne le renvoient pas
--   - des contrefaçons de clés USB partagent le même S/N
-- L'identifiant fiable est code_interne, généré par nous et collé sur le support.

-- ═══════════════════════════════════════════════════
-- OPERATIONS  (une tentative d'effacement)
-- ═══════════════════════════════════════════════════
CREATE TABLE operations (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    support_id          INTEGER NOT NULL REFERENCES supports(id) ON DELETE RESTRICT,
    technicien_id       INTEGER NOT NULL REFERENCES utilisateurs(id),
    station             TEXT,                    -- hostname de la station
    methode             TEXT NOT NULL,           -- ex: nvme_sanitize_block_erase
    norme_reference     TEXT NOT NULL DEFAULT 'NIST SP 800-88 Rev.1',
    nb_passes           INTEGER,
    debut               TEXT NOT NULL,
    fin                 TEXT,
    duree_secondes      INTEGER,
    resultat            TEXT NOT NULL
                        CHECK (resultat IN ('SUCCES','ECHEC','INTERROMPU')),
    verification_faite  INTEGER NOT NULL DEFAULT 0,
    verification_ok     INTEGER,                 -- NULL si non faite
    verification_detail TEXT,                    -- JSON : secteurs testés, résultats
    log_brut            TEXT,                    -- sortie complète nwipe
    log_sha256          TEXT NOT NULL,           -- hash du log brut
    outil_version       TEXT,                    -- ex: nwipe 0.36
    importe_le          TEXT NOT NULL
);
CREATE INDEX idx_operations_support ON operations(support_id);
CREATE INDEX idx_operations_debut   ON operations(debut);
-- Plusieurs opérations possibles par support (échec → nouvelle tentative).
-- L'historique conserve TOUTES les tentatives, y compris les échecs.

-- ═══════════════════════════════════════════════════
-- CERTIFICATS
-- ═══════════════════════════════════════════════════
CREATE TABLE certificats (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_cert     TEXT    NOT NULL UNIQUE,     -- ex: CERT-2026-000341
    operation_id    INTEGER NOT NULL UNIQUE REFERENCES operations(id),
    genere_le       TEXT    NOT NULL,
    genere_par      INTEGER NOT NULL REFERENCES utilisateurs(id),
    contenu_sha256  TEXT    NOT NULL,            -- hash des données certifiées
    signature       TEXT    NOT NULL,            -- Ed25519, base64
    cle_publique_id TEXT    NOT NULL,            -- quelle clé a signé
    chemin_pdf      TEXT    NOT NULL,
    token_verif     TEXT    NOT NULL UNIQUE      -- cible du QR code
);
CREATE UNIQUE INDEX idx_cert_token ON certificats(token_verif);
-- UNIQUE sur operation_id : un certificat par opération, pas de doublon.
-- Un certificat ne peut être généré que si operations.resultat = 'SUCCES'
--   ET verification_ok = 1  → contrainte applicative, testée.

-- ═══════════════════════════════════════════════════
-- UTILISATEURS
-- ═══════════════════════════════════════════════════
CREATE TABLE utilisateurs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    identifiant    TEXT    NOT NULL UNIQUE,
    nom_complet    TEXT    NOT NULL,
    mot_de_passe   TEXT    NOT NULL,             -- argon2id
    role           TEXT    NOT NULL
                   CHECK (role IN ('TECHNICIEN','RESPONSABLE','ADMINISTRATEUR')),
    actif          INTEGER NOT NULL DEFAULT 1,
    cree_le        TEXT    NOT NULL,
    derniere_conn  TEXT
);

-- ═══════════════════════════════════════════════════
-- AUDIT  (chaîné, inaltérable)
-- ═══════════════════════════════════════════════════
CREATE TABLE audit (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    horodatage      TEXT    NOT NULL,
    utilisateur_id  INTEGER REFERENCES utilisateurs(id),
    action          TEXT    NOT NULL,            -- CREATE_CLIENT, IMPORT_OP, ...
    entite          TEXT    NOT NULL,            -- table concernée
    entite_id       INTEGER,
    details         TEXT,                        -- JSON
    hash_precedent  TEXT    NOT NULL,            -- SHA-256 de la ligne n-1
    hash_courant    TEXT    NOT NULL             -- SHA-256(contenu + hash_precedent)
);
CREATE INDEX idx_audit_horodatage ON audit(horodatage);
CREATE INDEX idx_audit_entite     ON audit(entite, entite_id);
-- La première ligne a hash_precedent = '0'*64 (genesis).
-- Toute modification/suppression d'une ligne rompt la chaîne → détectable.
```

### Justification des choix structurants

| Choix | Raison |
|-------|--------|
| `ON DELETE RESTRICT` partout | En traçabilité, rien ne se supprime. On archive. Une suppression en cascade détruirait la preuve. |
| `code_interne` plutôt que `numero_serie` comme identifiant | Les S/N sont absents, illisibles ou dupliqués sur le matériel réel. |
| Opérations multiples par support | Un échec doit rester visible dans l'historique, pas être écrasé. |
| Certificat lié à l'opération, pas au support | Le certificat atteste un acte daté, pas un état. |
| SQLite au départ | Mono-poste, zéro administration. Migration PostgreSQL prévue via SQLAlchemy (aucun SQL brut spécifique). |
| Dates en TEXT ISO-8601 UTC | SQLite n'a pas de type date. ISO-8601 se trie lexicographiquement. |

---

## 3. Arborescence du projet

```
oralyse-wipe/
├── backend/
│   ├── app/
│   │   ├── main.py                 # point d'entrée FastAPI
│   │   ├── config.py               # settings (pydantic-settings)
│   │   ├── database.py             # session SQLAlchemy
│   │   ├── models/                 # ORM
│   │   │   ├── client.py
│   │   │   ├── lot.py
│   │   │   ├── support.py
│   │   │   ├── operation.py
│   │   │   ├── certificat.py
│   │   │   ├── utilisateur.py
│   │   │   └── audit.py
│   │   ├── schemas/                # Pydantic (entrée/sortie API)
│   │   ├── api/v1/                 # routes
│   │   │   ├── clients.py
│   │   │   ├── lots.py
│   │   │   ├── supports.py
│   │   │   ├── operations.py
│   │   │   ├── certificats.py
│   │   │   ├── verification.py     # endpoint public du QR
│   │   │   ├── dashboard.py
│   │   │   └── auth.py
│   │   ├── services/               # logique métier — AUCUN accès HTTP ici
│   │   │   ├── audit_service.py    # chaînage des hash
│   │   │   ├── import_service.py   # parsing des rapports station
│   │   │   ├── certificat_service.py
│   │   │   ├── signature_service.py# Ed25519
│   │   │   └── dashboard_service.py
│   │   ├── pdf/
│   │   │   ├── generator.py
│   │   │   └── templates/
│   │   └── core/
│   │       ├── security.py         # argon2, JWT
│   │       └── exceptions.py
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── fixtures/
│   ├── alembic/                    # migrations
│   ├── pyproject.toml
│   └── README.md
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── api/
│   │   └── App.tsx
│   └── package.json
│
├── station/                        # LOT 5 — code tournant sur ShredOS
│   ├── inventaire.py               # smartctl / nvme-cli → JSON
│   ├── effacement.py               # pilote nwipe / nvme sanitize
│   ├── verification.py             # relecture d'échantillons
│   └── rapport.py                  # produit le JSON importable
│
└── docs/
    ├── procedure-effacement.md     # LE document qui a de la valeur commerciale
    ├── installation.md
    ├── utilisateur.md
    └── administration.md
```

---

## 4. Format du rapport station (contrat d'interface)

C'est le seul point de contact entre les deux systèmes. À figer avant tout développement.

```json
{
  "format_version": "1.0",
  "station": "oralyse-station-01",
  "outil": { "nom": "nwipe", "version": "0.36" },
  "support": {
    "code_interne": "SUP-2026-000178",
    "numero_serie": "WD-WCC4E1234567",
    "modele": "WDC WD10EZEX-08WN4A0",
    "constructeur": "Western Digital",
    "capacite_octets": 1000204886016,
    "technologie": "HDD_SATA",
    "interface": "SATA 3.0 6.0 Gb/s",
    "sante": "OK",
    "hpa_detecte": false,
    "dco_detecte": false,
    "smart": { "temperature_c": 34, "power_on_hours": 21455, "reallocated_sectors": 0 }
  },
  "operation": {
    "methode": "nwipe_zero_fill",
    "norme_reference": "NIST SP 800-88 Rev.1 (Clear)",
    "nb_passes": 1,
    "debut": "2026-07-12T09:14:03Z",
    "fin": "2026-07-12T11:47:52Z",
    "duree_secondes": 9229,
    "resultat": "SUCCES"
  },
  "verification": {
    "faite": true,
    "ok": true,
    "secteurs_testes": 1024,
    "zones": ["premiers_100Mo", "derniers_100Mo", "aleatoire_1000_secteurs"],
    "anomalies": []
  },
  "log_brut": "...sortie complète de nwipe...",
  "log_sha256": "a3f5...e91b"
}
```

---

## 5. PROMPTS CLAUDE CODE — un lot par session

**Règle :** ne jamais lancer deux lots dans la même session. Chaque lot doit produire quelque chose qui fonctionne et qui est testé avant de passer au suivant.

### PROMPT LOT 1 — Fondations, clients, lots, supports

> Tu es un développeur Python senior. Tu construis "Oralyse Wipe", un logiciel de
> traçabilité pour une entreprise de recyclage DEEE.
>
> CONTRAINTE ABSOLUE : ce logiciel n'accède JAMAIS à un périphérique de stockage.
> Il ne fait que gérer des données et importer des rapports produits ailleurs.
> Aucun import de bibliothèque touchant /dev/*. Aucun subprocess système.
>
> Stack : Python 3.11+, FastAPI, SQLAlchemy 2.0 (typé), SQLite, Pydantic v2,
> Alembic, pytest. Code entièrement annoté en types. Architecture en couches :
> api/ (routes, aucune logique) → services/ (logique métier) → models/ (ORM).
> Les services ne connaissent pas HTTP. Les routes ne contiennent pas de SQL.
>
> PÉRIMÈTRE DE CE LOT — rien de plus :
> 1. Structure du projet backend/ (voir arborescence fournie).
> 2. Modèles SQLAlchemy : utilisateurs, clients, lots, supports, audit.
>    Utilise EXACTEMENT le schéma SQL fourni, sans le modifier.
> 3. Migration Alembic initiale.
> 4. Service d'audit avec chaînage de hash :
>    - hash_courant = SHA-256(horodatage|utilisateur|action|entite|entite_id|details|hash_precedent)
>    - première ligne : hash_precedent = "0" * 64
>    - fonction verifier_chaine() qui recalcule toute la chaîne et retourne les ruptures
>    - TOUTE création/modification passe par ce service. Aucune exception.
> 5. Authentification : argon2id pour les mots de passe, JWT, 3 rôles
>    (TECHNICIEN, RESPONSABLE, ADMINISTRATEUR) avec dépendances FastAPI de contrôle.
> 6. CRUD complet clients / lots / supports :
>    - génération automatique des identifiants : CLI-0001, LOT-2026-0001, SUP-2026-000001
>    - PAS de suppression réelle : archivage uniquement (champ archive)
>    - un support appartient obligatoirement à un lot
> 7. Tests pytest :
>    - unitaires sur le service d'audit (chaînage, détection de rupture)
>    - intégration sur chaque route CRUD
>    - un test qui vérifie qu'aucune suppression n'est possible
>    Couverture minimale 80% sur services/.
>
> Livre : le code, les migrations, les tests, et un README expliquant comment lancer.
> Ne code PAS les certificats, PAS le PDF, PAS l'import, PAS le dashboard, PAS le frontend.

### PROMPT LOT 2 — Import des rapports station

> Suite d'Oralyse Wipe. Le LOT 1 est terminé (clients, lots, supports, audit, auth).
>
> PÉRIMÈTRE DE CE LOT :
> 1. Modèle `operations` (schéma SQL fourni) + migration Alembic.
> 2. Service d'import `import_service.py` :
>    - entrée : fichier JSON au format "rapport station" (schéma fourni)
>    - validation stricte par Pydantic : un rapport malformé est REJETÉ, jamais
>      importé partiellement
>    - rattachement au support via `code_interne` ; si le support n'existe pas,
>      erreur explicite (on ne crée pas de support à l'aveugle)
>    - vérification de l'intégrité : recalcul du SHA-256 du log_brut et comparaison
>      avec log_sha256 du rapport. Si divergence → REJET.
>    - mise à jour du statut du support selon des règles STRICTES :
>        resultat=SUCCES  ET verification.ok=true    → EFFACE_VERIFIE
>        resultat=SUCCES  ET verification.faite=false → EFFACE_NON_VERIFIE
>        resultat=ECHEC                              → ECHEC
>        hpa_detecte OU dco_detecte non résolus      → NON_EFFACABLE
>    - import idempotent : réimporter le même rapport ne crée pas de doublon
>    - chaque import écrit dans l'audit
> 3. Route POST /api/v1/operations/import (upload de fichier, rôle TECHNICIEN mini).
> 4. Route GET /api/v1/operations avec filtres : lot, client, statut, période, technicien.
> 5. Recherche : GET /api/v1/supports/recherche?q= → cherche dans numero_serie,
>    code_interne, modele.
> 6. Tests : import nominal · rapport corrompu (hash faux) → rejeté · rapport
>    malformé → rejeté · support inexistant → erreur · double import → pas de
>    doublon · chaque transition de statut.
>
> Ne touche à rien d'autre.

### PROMPT LOT 3 — Certificats PDF signés + vérification QR

> Suite d'Oralyse Wipe. LOTS 1 et 2 terminés.
>
> PÉRIMÈTRE DE CE LOT :
> 1. Modèle `certificats` + migration.
> 2. Service de signature `signature_service.py` :
>    - Ed25519 (cryptography). Clé privée lue depuis un fichier hors dépôt git,
>      chemin en configuration. Clé publique exposée en lecture.
>    - signe le SHA-256 des données certifiées (pas le PDF lui-même : le PDF peut
>      être régénéré, les données non).
> 3. Service de génération de certificat :
>    - RÈGLE BLOQUANTE : un certificat ne peut être généré QUE si
>      operation.resultat == 'SUCCES' ET operation.verification_ok == 1.
>      Tout autre cas → refus explicite avec message clair.
>      Écris un test dédié pour CHAQUE cas de refus.
>    - numérotation CERT-2026-000001
>    - token de vérification : secrets.token_urlsafe(32), unique
> 4. Génération PDF (ReportLab ou WeasyPrint — argumente ton choix) :
>    - identité visuelle : vert forêt profond (#1a3a2e environ) et cuivre chaud
>      (#b87333 environ), typographie sobre et professionnelle
>    - contenu : logo, client, n° de lot, code interne du support, n° de série,
>      modèle, capacité, technologie, méthode, norme (NIST SP 800-88 Rev.1),
>      date/heure début et fin, durée, technicien, résultat de la VÉRIFICATION
>      post-effacement, SHA-256 du log, signature Ed25519 (tronquée à l'affichage),
>      QR code
>    - mention obligatoire en pied de page, mot pour mot :
>      "Certificat d'effacement sécurisé. Opération réalisée conformément aux
>       recommandations NIST SP 800-88 Rev. 1. Vérifiable sur [URL]/verif/{token}."
>    - NE JAMAIS écrire "juridiquement valide" ou équivalent nulle part.
> 5. Endpoint PUBLIC (sans authentification) GET /verif/{token} :
>    - page HTML simple : certificat valide/invalide, client, date, support
>      (numéro de série partiellement masqué), méthode, résultat
>    - ne divulgue AUCUNE donnée sensible au-delà de ça
>    - vérifie la signature Ed25519 à chaque appel
> 6. Tests : génération, refus dans tous les cas invalides, vérification de
>    signature, token invalide, altération des données → signature invalide.

### PROMPT LOT 4 — Frontend React + dashboard

> Suite d'Oralyse Wipe. Backend LOTS 1-3 terminés (API documentée sur /docs).
>
> Frontend React + TypeScript + Vite. Pas de Tauri. Tailwind.
> Design : sobre, dense, professionnel. Palette vert forêt profond + cuivre.
> Objectif : un technicien doit être opérationnel après 5 minutes de formation.
>
> ÉCRANS :
> 1. Connexion
> 2. Tableau de bord : supports traités (jour/semaine/mois), capacité totale
>    effacée, durée moyenne, taux de réussite, répartition par technologie,
>    liste des échecs et NON_EFFACABLE à traiter (visible, pas caché)
> 3. Clients : liste, recherche, fiche, création/édition
> 4. Lots : liste filtrable, fiche lot avec ses supports, avancement
> 5. Supports : liste, fiche détaillée avec historique de TOUTES les opérations
>    (échecs inclus), données SMART lisibles
> 6. Import : glisser-déposer d'un rapport JSON, retour d'erreur EXPLICITE si rejet
> 7. Certificats : génération depuis une opération éligible, téléchargement,
>    bouton désactivé + raison affichée si non éligible
> 8. Recherche globale : numéro de série ou code interne
> 9. Administration (rôle ADMIN uniquement) : utilisateurs, journal d'audit avec
>    bouton "vérifier l'intégrité de la chaîne"
>
> Les statuts ECHEC et NON_EFFACABLE doivent être VISUELLEMENT DISTINCTS et
> impossibles à confondre avec un succès. C'est un point de sécurité, pas d'esthétique.
>
> Backend : ajoute les routes /dashboard nécessaires (agrégations SQL, pas de
> calcul en Python sur des milliers de lignes).

### PROMPT LOT 5 — Scripts station (à ne lancer qu'en dernier)

> Suite d'Oralyse Wipe. Dossier station/ uniquement. Ce code tourne en root sur une
> machine dédiée (ShredOS/Debian live), SANS réseau, sur des disques CLIENTS.
>
> ⚠️ CE CODE PEUT DÉTRUIRE DES DONNÉES DE FAÇON IRRÉVERSIBLE.
> Priorité absolue : sécurité et refus par défaut. Aucune optimisation, aucune
> élégance, aucune abstraction inutile. Du code ennuyeux, explicite et vérifiable.
>
> TRIPLE SÉCURITÉ OBLIGATOIRE avant tout effacement :
> 1. Refus catégorique si le périphérique contient le système de fichiers racine,
>    /boot, ou le support de démarrage. Détection par plusieurs méthodes croisées.
> 2. Whitelist explicite : le périphérique doit être passé en argument, jamais
>    découvert et effacé automatiquement.
> 3. Confirmation par saisie MANUELLE du numéro de série complet du disque cible.
>    Une simple confirmation "oui/o/y" est INTERDITE.
>
> MODULES :
> - inventaire.py : lsblk, smartctl, nvme-cli, hdparm → dict Python.
>   Détection HPA (hdparm -N) et DCO (hdparm --dco-identify). Détection SED.
> - effacement.py : sélection de la méthode selon la technologie, table de décision :
>     HDD SATA/SAS → nwipe zero fill 1 passe
>     SSD SATA     → hdparm --security-erase-enhanced, repli blkdiscard -s
>     NVMe         → nvme sanitize (block erase), repli nvme format -s 1
>     SED          → crypto-erase
>     USB/SD       → nwipe overwrite
>   Vérifie TOUJOURS le statut renvoyé par le disque après la commande
>   (nvme sanitize-log, hdparm -I). Un exit code 0 ne prouve RIEN.
> - verification.py : après effacement, relecture de
>     - les 100 premiers Mo
>     - les 100 derniers Mo
>     - 1000 secteurs aléatoires
>   et vérification du motif attendu. Rapport détaillé des anomalies.
> - rapport.py : produit le JSON au format d'interface (fourni), avec log_sha256.
>
> Tests : pytest avec subprocess ENTIÈREMENT mocké. AUCUN test ne doit pouvoir
> toucher un vrai périphérique. Teste en priorité tous les cas de REFUS.

---

## 6. Ordre d'exécution et estimation

| Lot | Contenu                       | Effort | Dépendance                   |
|-----|-------------------------------|--------|------------------------------|
| 1   | Fondations, CRUD, audit chaîné| 2–3 j  | —                            |
| 2   | Import des rapports           | 1–2 j  | 1                            |
| 3   | Certificats PDF + QR          | 2 j    | 2                            |
| 4   | Frontend + dashboard          | 3–4 j  | 3                            |
| 5   | Scripts station               | 2–3 j  | format d'interface figé      |

Le lot 5 peut attendre : tant qu'il n'existe pas, la station tourne sous ShredOS/nwipe standard et un opérateur remplit le JSON manuellement. C'est acceptable pour les premiers volumes.

---

## 7. Ce qui a plus de valeur commerciale que ce logiciel

À produire en parallèle, et probablement avant :

**`docs/procedure-effacement.md`** — 5 à 10 pages :
périmètre · réception et scellement des supports · référentiel appliqué (NIST SP 800-88 Rev. 1) · table des méthodes par technologie · vérification post-effacement · traçabilité · modèle de certificat · sort des supports non effaçables (→ destruction physique) · sous-traitance RGPD art. 28 · assurance RC pro.

C'est ce document qu'un RSSI lit. Il ne lira jamais le code.
