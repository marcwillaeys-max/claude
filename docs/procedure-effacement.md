# Procédure d'effacement sécurisé des supports de données

**Oralyse SAS**
Référentiel appliqué : NIST SP 800-88 Rev. 1 (*Guidelines for Media Sanitization*)
Version du document : 1.0
Diffusion : clients, RSSI, DPO, auditeurs, assureur RC professionnelle

> Ce document décrit la procédure opérationnelle d'effacement et la chaîne de
> preuve associée. Il n'emploie jamais la formule « juridiquement valide » :
> Oralyse atteste une **opération réalisée conformément aux recommandations
> NIST SP 800-88 Rev. 1**, tracée et vérifiée. L'appréciation juridique relève
> du client et de son conseil.

---

## 1. Périmètre

Cette procédure s'applique à tout support de stockage confié à Oralyse en vue de
sa réutilisation, de sa valorisation ou de sa destruction :

- disques durs magnétiques (HDD) SATA et SAS ;
- disques à mémoire flash (SSD) SATA et NVMe ;
- disques auto-chiffrants (SED / TCG Opal) ;
- clés USB et cartes mémoire (SD, microSD).

Elle couvre l'ensemble de la chaîne : réception, inventaire, effacement,
vérification, certification, et sort des supports non effaçables. Elle **exclut**
explicitement :

- la récupération de données (Oralyse ne restaure aucune donnée) ;
- les supports optiques (CD/DVD/Blu-ray) et les bandes, orientés destruction physique ;
- les téléphones et tablettes, hors périmètre de la présente version.

### Séparation des responsabilités techniques

Deux systèmes de nature différente interviennent, **strictement séparés** :

| | Station d'effacement | Logiciel métier |
|---|---|---|
| Rôle | efface réellement les supports | trace, gère, certifie |
| Environnement | machine dédiée, **hors réseau** | poste bureautique |
| Accès disque | root, accès matériel direct | **aucun** |

Le logiciel métier ne touche jamais un périphérique de stockage. Il importe un
rapport signé produit par la station. Cette séparation est une garantie de
sécurité : une erreur du logiciel de gestion ne peut pas provoquer d'effacement,
et le poste de gestion ne manipule aucune donnée client.

---

## 2. Réception et scellement des supports

1. **Réception** : le matériel est réceptionné contre un bordereau signé
   indiquant le client, la date, et le nombre de supports annoncés. Un **lot**
   (`LOT-AAAA-NNNN`) est ouvert dans le logiciel métier.
2. **Marquage** : chaque support reçoit immédiatement un **code interne unique**
   (`SUP-AAAA-NNNNNN`) matérialisé par une étiquette et un QR code physiquement
   collés. Ce code — et non le numéro de série — est l'identifiant de référence :
   les numéros de série sont fréquemment absents, illisibles sur matériel
   défaillant, ou dupliqués sur des contrefaçons.
3. **Scellement** : les supports en attente de traitement sont conservés dans une
   zone à accès restreint. Les entrées et sorties de cette zone sont journalisées.
4. **Inventaire** : la station relève automatiquement, en lecture seule, le
   modèle, la capacité, la technologie, l'état SMART et la présence éventuelle de
   zones masquées (HPA/DCO). Ces éléments sont consignés dans le rapport.

Aucun support ne quitte la zone scellée sans que son statut soit passé à
`EFFACE_VERIFIE`, `DETRUIT_PHYSIQUEMENT`, ou consigné explicitement dans un autre
état tracé.

---

## 3. Référentiel appliqué : NIST SP 800-88 Rev. 1

Le NIST SP 800-88 Rev. 1 définit trois niveaux d'assainissement (*sanitization*) :

| Niveau | Principe | Usage chez Oralyse |
|--------|----------|--------------------|
| **Clear** | réécriture logique via les commandes standard | HDD réutilisés, clés USB/SD |
| **Purge** | commandes matérielles (secure erase, sanitize, crypto-erase) rendant la récupération infaisable même en laboratoire | SSD, NVMe, SED |
| **Destroy** | destruction physique du support | supports non effaçables de façon fiable |

Le choix du niveau dépend de la technologie du support (section 4) et de la
sensibilité déclarée par le client. En l'absence d'indication contraire, Oralyse
applique **au minimum le niveau Clear pour les HDD et le niveau Purge pour les
mémoires flash**, ce qui correspond à l'état de l'art pour un réemploi hors
contexte classifié.

---

## 4. Table des méthodes par technologie

La méthode d'effacement n'est **pas** laissée au libre choix de l'opérateur :
elle est déterminée par la technologie du support, selon la table suivante.
L'ordre de préférence intègre les limites connues de chaque commande.

| Technologie | Méthode 1 | Repli 1 | Repli 2 | Niveau NIST |
|-------------|-----------|---------|---------|-------------|
| **HDD SATA / SAS** | `nwipe` 1 passe de zéros | 3 passes si le client l'exige | — | Clear |
| **SSD SATA** | `hdparm --security-erase-enhanced` | `blkdiscard -s` (secure discard) | overwrite `nwipe` + vérification | Purge |
| **NVMe** | `nvme sanitize` (block erase) | `nvme format -s 1` (crypto erase) | `nvme format -s 2` | Purge |
| **SED / auto-chiffrant** | crypto-erase (révocation de la clé) | — | — | Purge |
| **Clé USB / carte SD** | overwrite `nwipe` + vérification | — | — | Clear |

### Points d'attention techniques

- **Le `hdparm --security-erase` seul est insuffisant sur certains SSD** : des
  firmwares acceptent la commande et ne réalisent aucun effacement effectif.
  C'est pourquoi la méthode SSD SATA prévoit une **vérification par relecture**
  et un repli.
- **Un code de retour 0 ne prouve rien.** Après chaque commande, la station
  relit le **statut renvoyé par le disque lui-même** (`nvme sanitize-log`,
  `hdparm -I`). L'opération n'est déclarée en succès que si ce statut confirme
  l'achèvement.
- **Une seule passe de zéros suffit pour un HDD moderne** (niveau Clear NIST).
  Les passes multiples ne sont appliquées que sur exigence contractuelle du
  client ; elles n'augmentent pas la sécurité sur les supports magnétiques
  actuels.

---

## 5. Vérification post-effacement

**Sans vérification, un certificat n'atteste qu'une intention d'effacer, pas un
résultat.** Oralyse impose donc une vérification par relecture d'échantillons
après chaque effacement.

Zones relues, au minimum :

- les **100 premiers Mo** du support ;
- les **100 derniers Mo** du support ;
- **1000 secteurs** tirés aléatoirement sur l'ensemble de la surface adressable.

Chaque octet relu est comparé au motif attendu (0x00 après une passe de zéros).
Toute divergence constitue une **anomalie** et est consignée dans le rapport. Le
résultat de la vérification (`faite`, `ok`, secteurs testés, anomalies) est un
**champ obligatoire** du rapport et une condition **bloquante** de la
certification.

Cas particulier du **crypto-erase** (SED, `nvme format -s 1/2`) : le motif après
effacement n'est pas déterministe (les données subsistent mais deviennent
illisibles, la clé ayant été détruite). La vérification par relecture de motif
n'est donc pas applicable ; la preuve repose sur le statut de révocation de clé
renvoyé par le disque, et le support n'est pas certifié comme « vérifié par
relecture ».

---

## 6. Zones masquées : HPA, DCO, secteurs réalloués

Certaines zones d'un disque peuvent être **masquées au système d'exploitation**
et échapper à un effacement naïf :

- **HPA** (*Host Protected Area*) — zone réservée en fin de disque, détectée par
  `hdparm -N` ;
- **DCO** (*Device Configuration Overlay*) — reconfiguration masquant de la
  capacité, détectée par `hdparm --dco-identify` ;
- **secteurs réalloués** — secteurs défaillants remappés par le firmware, dont le
  contenu d'origine peut rester physiquement présent.

Procédure :

1. La station **détecte** HPA/DCO lors de l'inventaire. En cas de statut
   indéterminé, le support est traité **par prudence** comme porteur d'une zone
   masquée.
2. Si une zone masquée est présente, elle doit être **désactivée** avant
   effacement (restauration de la pleine capacité native), puis l'effacement est
   relancé sur l'intégralité du support.
3. Si la désactivation n'est pas possible ou pas vérifiable, le support est
   déclaré **`NON_EFFACABLE`** de façon fiable et basculé vers le **circuit de
   destruction physique** (section 8). Il ne reçoit **jamais** de certificat
   d'effacement.

Un nombre élevé de secteurs réalloués fait passer l'état de santé du support à
`DEGRADE` ou `DEFAILLANT` et oriente en général vers la destruction physique
plutôt que le réemploi.

---

## 7. Traçabilité et chaîne de preuve

### 7.1 Statuts d'un support

Le cycle de vie d'un support est explicitement modélisé :

`EN_ATTENTE` → `EN_COURS` → { `EFFACE_VERIFIE` · `EFFACE_NON_VERIFIE` · `ECHEC` ·
`NON_EFFACABLE` } → `DETRUIT_PHYSIQUEMENT` le cas échéant.

Un support en `ECHEC` ou `NON_EFFACABLE` **ne peut pas** générer de certificat
d'effacement. C'est une règle contrôlée par le logiciel, pas une consigne.

### 7.2 Conservation de toutes les tentatives

Chaque tentative d'effacement (**opération**) est conservée, y compris les
échecs. Un échec n'est jamais écrasé par une tentative ultérieure réussie :
l'historique complet reste consultable. Rien ne se supprime dans le système ;
les entités obsolètes sont archivées, pas effacées, afin de préserver la preuve.

### 7.3 Journal d'audit chaîné

Toute action (création, import de rapport, génération de certificat…) est
inscrite dans un **journal d'audit chaîné par empreinte cryptographique** :
chaque enregistrement contient le SHA-256 de l'enregistrement précédent. Toute
modification ou suppression a posteriori d'une ligne rompt la chaîne et devient
**détectable**. Un contrôle d'intégrité recalcule l'ensemble de la chaîne à la
demande et signale toute rupture.

Cette mesure ne rend pas le journal *impossible* à modifier — aucun fichier ne
l'est — mais rend toute altération **démontrable**. Un export horodaté et
append-only hors de la machine complète le dispositif.

### 7.4 Contrat d'interface station ↔ logiciel métier

La station et le logiciel métier ne communiquent que par un **fichier JSON par
support**, au format figé (version 1.0). Ce rapport contient l'identité du
support, les paramètres et le résultat de l'opération, le détail de la
vérification, le log brut de l'outil et son empreinte SHA-256. À l'import, le
logiciel métier **recalcule cette empreinte** et rejette tout rapport dont
l'intégrité n'est pas confirmée.

---

## 8. Sort des supports non effaçables → destruction physique

Un support est orienté vers la destruction physique dès lors que :

- une zone masquée (HPA/DCO) ne peut être ni désactivée ni vérifiée ;
- l'effacement échoue de façon répétée (`ECHEC`) ;
- l'état de santé est `DEFAILLANT` (le support ne répond plus de façon fiable) ;
- le numéro de série est illisible et la confirmation manuelle du disque cible
  impossible.

La destruction physique (broyage, déchiquetage) est réalisée conformément au
niveau **Destroy** du NIST SP 800-88, par Oralyse ou un prestataire agréé. Elle
fait l'objet d'un **enregistrement dédié** (`DETRUIT_PHYSIQUEMENT`) et, le cas
échéant, d'un certificat de destruction distinct du certificat d'effacement.

Aucun support destiné à la destruction ne peut être réintroduit dans le circuit
de réemploi.

---

## 9. Modèle de certificat

Pour chaque opération éligible — **résultat `SUCCES` ET vérification
post-effacement positive**, sur un support qui n'est ni en `ECHEC` ni
`NON_EFFACABLE` — un **certificat d'effacement sécurisé** est émis. Il comporte :

- l'identité du client, le numéro de lot, le code interne et le numéro de série
  du support, son modèle, sa capacité et sa technologie ;
- la méthode employée, la norme de référence (NIST SP 800-88 Rev. 1), les
  horodatages de début et de fin, la durée, et l'identité du technicien ;
- le **résultat de la vérification post-effacement** ;
- l'empreinte SHA-256 du log d'effacement ;
- une **signature numérique Ed25519** portant sur l'empreinte des données
  certifiées (et non sur le PDF, qui peut être régénéré) ;
- un **QR code** renvoyant vers une page de vérification publique.

La page de vérification recalcule la signature à chaque consultation et n'expose
que le strict nécessaire (numéro de série partiellement masqué). Toute altération
des données certifiées invalide la signature.

Mention portée sur chaque certificat, mot pour mot :

> « Certificat d'effacement sécurisé. Opération réalisée conformément aux
> recommandations NIST SP 800-88 Rev. 1. Vérifiable sur [URL]/verif/{token}. »

Sur l'échelle de valeur probante, la signature Ed25519 auto-hébergée constitue le
socle honnête et vérifiable du MVP. Une **évolution vers un horodatage qualifié
RFC 3161** (autorité d'horodatage tierce) est prévue pour renforcer la valeur
juridique, à coût modéré.

---

## 10. Sous-traitance et RGPD (article 28)

Lorsqu'Oralyse traite des supports contenant des données à caractère personnel,
elle agit en qualité de **sous-traitant** au sens de l'article 28 du RGPD, pour
le compte du client responsable de traitement. À ce titre :

- l'opération d'effacement s'inscrit dans une logique de **minimisation** et de
  respect des durées de conservation (l'effacement est une modalité d'exercice
  du droit à l'effacement et de fin de vie de la donnée) ;
- Oralyse s'engage par contrat à ne traiter les supports que sur **instruction
  documentée** du client, à garantir la **confidentialité** du personnel
  habilité, et à assister le client en cas de contrôle ;
- la **traçabilité** décrite en section 7 constitue l'élément de preuve du
  respect de ces obligations ;
- aucune donnée client n'est copiée, exportée ou conservée : la station opère
  hors réseau et le logiciel métier ne manipule que des métadonnées et des logs
  d'effacement.

Un **accord de sous-traitance** (clauses article 28) est signé préalablement à
toute prise en charge de supports porteurs de données personnelles. Il précise la
nature et la finalité du traitement, la durée, les mesures de sécurité, et le
sort des supports en fin d'opération.

---

## 11. Assurance et responsabilité

Oralyse est couverte par une **assurance responsabilité civile professionnelle**
adaptée à l'activité de traitement et de destruction de supports de données. Les
limites de garantie et les exclusions sont précisées au contrat cadre.

La chaîne de preuve (journal d'audit chaîné, rapports signés, certificats
vérifiables) constitue l'élément documentaire sur lequel s'appuie, le cas
échéant, la mise en jeu de cette garantie. Elle permet, pour chaque support, de
démontrer :

- **quel** support a été traité (code interne + numéro de série) ;
- **quand**, **par qui** et **avec quelle méthode** ;
- que l'effacement a été **vérifié**, ou à défaut que le support a été orienté
  vers la **destruction physique**.

---

## Annexe — Glossaire

| Terme | Définition |
|-------|------------|
| **Clear / Purge / Destroy** | les trois niveaux d'assainissement du NIST SP 800-88 Rev. 1 |
| **HPA** | *Host Protected Area* — zone de disque masquée au système d'exploitation |
| **DCO** | *Device Configuration Overlay* — reconfiguration masquant de la capacité |
| **SED** | *Self-Encrypting Drive* — disque auto-chiffrant (crypto-erase par révocation de clé) |
| **SMART** | système d'auto-surveillance des disques, renseigne l'état de santé |
| **crypto-erase** | effacement par destruction de la clé de chiffrement, rendant les données illisibles |
| **Ed25519** | schéma de signature numérique à courbe elliptique |
| **RFC 3161** | protocole d'horodatage numérique par autorité tierce |
| **Code interne** | identifiant `SUP-AAAA-NNNNNN` attribué par Oralyse, collé sur le support |
