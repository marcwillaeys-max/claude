import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Operation, Support } from "../api/types";
import { ResultatBadge, StatutSupportBadge } from "../components/StatutBadge";
import { Carte, Cellule, InfoLigne, Ligne, MessageErreur, Tableau } from "../components/ui";
import { capaciteLisible, dateLisible, dureeLisible } from "../format";

const STATUTS = [
  "EN_ATTENTE",
  "EN_COURS",
  "EFFACE_VERIFIE",
  "EFFACE_NON_VERIFIE",
  "ECHEC",
  "NON_EFFACABLE",
  "DETRUIT_PHYSIQUEMENT",
] as const;

export function Supports() {
  const [supports, setSupports] = useState<Support[]>([]);
  const [filtreStatut, setFiltreStatut] = useState("");
  const naviguer = useNavigate();

  const charger = useCallback(() => {
    const parametres = filtreStatut ? `?statut=${filtreStatut}` : "";
    api<Support[]>(`/api/v1/supports${parametres}`).then(setSupports).catch(() => setSupports([]));
  }, [filtreStatut]);
  useEffect(charger, [charger]);

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-foret">Supports</h1>
      <select
        value={filtreStatut}
        onChange={(e) => setFiltreStatut(e.target.value)}
        className="rounded border border-gray-300 px-2.5 py-1.5 text-sm focus:border-cuivre focus:outline-none"
      >
        <option value="">Tous les statuts</option>
        {STATUTS.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>
      <Carte>
        <Tableau entetes={["Code interne", "N° de série", "Modèle", "Techno", "Capacité", "Statut"]}>
          {supports.map((support) => (
            <Ligne key={support.id} onClick={() => naviguer(`/supports/${support.id}`)}>
              <Cellule>
                <span className="font-mono text-xs">{support.code_interne}</span>
              </Cellule>
              <Cellule>{support.numero_serie ?? "—"}</Cellule>
              <Cellule>{support.modele ?? "—"}</Cellule>
              <Cellule>{support.technologie ?? "—"}</Cellule>
              <Cellule>{capaciteLisible(support.capacite_octets)}</Cellule>
              <Cellule>
                <StatutSupportBadge statut={support.statut} />
              </Cellule>
            </Ligne>
          ))}
        </Tableau>
        {supports.length === 0 && <p className="text-sm text-gray-500">Aucun support</p>}
      </Carte>
    </div>
  );
}

const LIBELLES_SMART: Record<string, string> = {
  temperature_c: "Température (°C)",
  power_on_hours: "Heures de fonctionnement",
  reallocated_sectors: "Secteurs réalloués",
};

function TableSmart({ smartJson }: { smartJson: string | null }) {
  if (!smartJson) return <p className="text-sm text-gray-500">Aucune donnée SMART importée</p>;
  let donnees: Record<string, unknown>;
  try {
    donnees = JSON.parse(smartJson);
  } catch {
    return <pre className="overflow-x-auto text-xs">{smartJson}</pre>;
  }
  return (
    <div className="max-w-xl">
      {Object.entries(donnees).map(([cle, valeur]) => (
        <InfoLigne key={cle} libelle={LIBELLES_SMART[cle] ?? cle} valeur={String(valeur)} />
      ))}
    </div>
  );
}

export function SupportFiche() {
  const { id } = useParams();
  const [support, setSupport] = useState<Support | null>(null);
  const [operations, setOperations] = useState<Operation[]>([]);
  const [erreur, setErreur] = useState("");

  useEffect(() => {
    api<Support>(`/api/v1/supports/${id}`).then(setSupport).catch((e) => setErreur(e.message));
    api<Operation[]>(`/api/v1/operations?support_id=${id}`).then(setOperations).catch(() => setOperations([]));
  }, [id]);

  if (erreur) return <MessageErreur>{erreur}</MessageErreur>;
  if (!support) return <p className="text-sm text-gray-500">Chargement…</p>;

  return (
    <div className="space-y-4">
      <h1 className="flex items-center gap-3 text-xl font-bold text-foret">
        Support <span className="font-mono text-cuivre">{support.code_interne}</span>
        <StatutSupportBadge statut={support.statut} />
      </h1>
      {(support.hpa_detecte === 1 || support.dco_detecte === 1) && (
        <MessageErreur>
          {support.hpa_detecte === 1 && "Zone HPA détectée. "}
          {support.dco_detecte === 1 && "Configuration DCO détectée. "}
          Des zones du disque peuvent échapper à l'effacement → circuit destruction physique.
        </MessageErreur>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        <Carte titre="Identification">
          <InfoLigne libelle="N° de série" valeur={support.numero_serie} />
          <InfoLigne libelle="Constructeur" valeur={support.constructeur} />
          <InfoLigne libelle="Modèle" valeur={support.modele} />
          <InfoLigne libelle="Capacité" valeur={capaciteLisible(support.capacite_octets)} />
          <InfoLigne libelle="Technologie" valeur={support.technologie} />
          <InfoLigne libelle="Interface" valeur={support.interface} />
          <InfoLigne libelle="Santé" valeur={support.sante} />
          <InfoLigne libelle="Destination" valeur={support.destination} />
          <InfoLigne
            libelle="Lot"
            valeur={
              <Link to={`/lots/${support.lot_id}`} className="text-cuivre underline">
                Voir le lot
              </Link>
            }
          />
        </Carte>
        <Carte titre="Données SMART">
          <TableSmart smartJson={support.smart_json} />
        </Carte>
      </div>
      <Carte titre={`Historique des opérations — TOUTES les tentatives, échecs inclus (${operations.length})`}>
        <Tableau entetes={["#", "Méthode", "Début", "Durée", "Résultat", "Vérification", "SHA-256 du log"]}>
          {operations.map((operation) => (
            <Ligne key={operation.id}>
              <Cellule>{operation.id}</Cellule>
              <Cellule>
                {operation.methode}
                <span className="block text-xs text-gray-500">{operation.outil_version}</span>
              </Cellule>
              <Cellule>{dateLisible(operation.debut)}</Cellule>
              <Cellule>{dureeLisible(operation.duree_secondes)}</Cellule>
              <Cellule>
                <ResultatBadge resultat={operation.resultat} />
              </Cellule>
              <Cellule>
                {operation.verification_faite === 0
                  ? "Non faite"
                  : operation.verification_ok === 1
                    ? "✓ Conforme"
                    : "✗ Non conforme"}
              </Cellule>
              <Cellule>
                <span className="font-mono text-xs" title={operation.log_sha256}>
                  {operation.log_sha256.slice(0, 16)}…
                </span>
              </Cellule>
            </Ligne>
          ))}
        </Tableau>
        {operations.length === 0 && (
          <p className="text-sm text-gray-500">Aucune opération importée pour ce support</p>
        )}
      </Carte>
    </div>
  );
}
