import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { Support } from "../api/types";
import { StatutSupportBadge } from "../components/StatutBadge";
import { Bouton, Carte, Cellule, Ligne, Tableau } from "../components/ui";
import { capaciteLisible } from "../format";

export function Recherche() {
  const [terme, setTerme] = useState("");
  const [resultats, setResultats] = useState<Support[] | null>(null);
  const naviguer = useNavigate();

  async function rechercher(evenement: React.FormEvent) {
    evenement.preventDefault();
    if (!terme.trim()) return;
    setResultats(await api<Support[]>(`/api/v1/supports/recherche?q=${encodeURIComponent(terme)}`));
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-foret">Recherche globale</h1>
      <form onSubmit={rechercher} className="flex gap-2">
        <input
          autoFocus
          placeholder="Numéro de série, code interne ou modèle…"
          value={terme}
          onChange={(e) => setTerme(e.target.value)}
          className="w-96 rounded border border-gray-300 px-2.5 py-1.5 text-sm focus:border-cuivre focus:outline-none"
        />
        <Bouton type="submit">Rechercher</Bouton>
      </form>
      {resultats !== null && (
        <Carte titre={`${resultats.length} résultat(s)`}>
          <Tableau entetes={["Code interne", "N° de série", "Modèle", "Capacité", "Statut"]}>
            {resultats.map((support) => (
              <Ligne key={support.id} onClick={() => naviguer(`/supports/${support.id}`)}>
                <Cellule>
                  <span className="font-mono text-xs">{support.code_interne}</span>
                </Cellule>
                <Cellule>{support.numero_serie ?? "—"}</Cellule>
                <Cellule>{support.modele ?? "—"}</Cellule>
                <Cellule>{capaciteLisible(support.capacite_octets)}</Cellule>
                <Cellule>
                  <StatutSupportBadge statut={support.statut} />
                </Cellule>
              </Ligne>
            ))}
          </Tableau>
          {resultats.length === 0 && (
            <p className="text-sm text-gray-500">Aucun support ne correspond à « {terme} »</p>
          )}
        </Carte>
      )}
    </div>
  );
}
