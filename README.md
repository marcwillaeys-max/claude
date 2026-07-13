# Oralyse Wipe

Logiciel de traçabilité et de certification d'effacement sécurisé (Oralyse SAS).

Deux systèmes strictement séparés :

- **Station d'effacement** — machine dédiée hors réseau sous ShredOS/nwipe.
  Elle seule touche les disques. *(Scripts : LOT 5, non développés.)*
- **Logiciel métier** *(ce dépôt, dossier `backend/`)* — gère clients, lots,
  supports, historique chaîné et certificats. **N'accède jamais à un
  périphérique de stockage.**

| Dossier | Contenu |
|---------|---------|
| `docs/specification.md` | Spécification complète + prompts des 5 lots |
| `backend/` | LOTS 1-3 : fondations, auth, CRUD, audit chaîné, import des rapports station, certificats PDF signés Ed25519 + vérification QR publique, dashboard — voir `backend/README.md` |
| `frontend/` | LOT 4 : React + TypeScript + Vite + Tailwind, 9 écrans — voir `frontend/README.md` |
| `station/` | LOT 5 : scripts ShredOS (root, hors réseau) — inventaire, triple sécurité, effacement, vérification, rapport — voir `station/README.md` |

Avancement : **LOTS 1-5 terminés.** Le projet couvre l'intégralité de la
spécification. La station (`station/`) est le seul composant qui touche au
matériel ; elle communique avec le logiciel métier uniquement via le rapport
JSON (contrat d'interface §4), jamais directement.
