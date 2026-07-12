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

Avancement : **LOTS 1-4 terminés** · LOT 5 (scripts station) — à venir.
