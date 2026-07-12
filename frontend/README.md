# Oralyse Wipe — Frontend (LOT 4)

React 18 + TypeScript + Vite + Tailwind CSS v4. Pas de Tauri (spécification §1.8).
Palette : vert forêt `#1a3a2e` + cuivre `#b87333`.

## Écrans

1. **Connexion** — JWT, session conservée dans le navigateur.
2. **Tableau de bord** — supports effacés (jour/7 j/30 j), capacité totale effacée,
   durée moyenne, taux de réussite, répartitions par technologie et par statut,
   et la liste des `ECHEC` / `NON_EFFACABLE` à traiter — **visible en tête, jamais cachée**.
3. **Clients** — liste, recherche, fiche, création/édition, archivage (RESPONSABLE+).
4. **Lots** — liste filtrable (statut, client), fiche avec supports, barre
   d'avancement, ajout de supports, clôture (RESPONSABLE+).
5. **Supports** — liste filtrable, fiche détaillée : historique de TOUTES les
   opérations (échecs inclus), données SMART lisibles, alerte HPA/DCO.
6. **Import** — glisser-déposer de rapports JSON ; rejet affiché en clair avec la
   raison exacte renvoyée par le backend (hash invalide, rapport malformé, support inconnu…).
7. **Certificats** — génération depuis une opération éligible uniquement ; bouton
   désactivé **avec la raison affichée** sinon (résultat non SUCCES, pas de
   vérification, support NON_EFFACABLE, déjà certifié). Téléchargement PDF,
   lien vers la page publique de vérification.
8. **Recherche globale** — numéro de série, code interne ou modèle.
9. **Administration** (ADMINISTRATEUR) — utilisateurs (création, désactivation),
   journal d'audit avec bouton « Vérifier l'intégrité de la chaîne ».

Les statuts `ECHEC` (rouge, ✗) et `NON_EFFACABLE` (rouge sombre, bordure
tiretée, ⚠) sont visuellement impossibles à confondre avec un succès : couleur
réservée + icône + libellé, jamais la couleur seule. C'est un point de sécurité.

## Lancer

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 — proxy /api et /verif vers :8000
```

Le backend doit tourner sur `http://localhost:8000` (voir `backend/README.md`).

```bash
npm run build      # tsc strict + bundle de production dans dist/
```
