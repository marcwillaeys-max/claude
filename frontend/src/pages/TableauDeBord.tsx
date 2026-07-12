import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Indicateurs, Support } from "../api/types";
import { StatutSupportBadge } from "../components/StatutBadge";
import { Carte, Cellule, Ligne, MessageErreur, Tableau } from "../components/ui";
import { capaciteLisible, dureeLisible, pourcentage } from "../format";

function Tuile({ libelle, valeur }: { libelle: string; valeur: string | number }) {
  return (
    <div className="rounded-md bg-white p-4 shadow-sm">
      <div className="text-2xl font-bold text-foret">{valeur}</div>
      <div className="mt-1 text-xs uppercase tracking-wide text-gray-500">{libelle}</div>
    </div>
  );
}

function Repartition({ titre, donnees }: { titre: string; donnees: Record<string, number> }) {
  const entrees = Object.entries(donnees).sort((a, b) => b[1] - a[1]);
  const maximum = Math.max(1, ...entrees.map(([, nombre]) => nombre));
  return (
    <Carte titre={titre}>
      {entrees.length === 0 && <p className="text-sm text-gray-500">Aucune donnée</p>}
      <div className="space-y-2">
        {entrees.map(([categorie, nombre]) => (
          <div key={categorie} className="flex items-center gap-2 text-sm">
            <span className="w-44 shrink-0 truncate text-foret">{categorie}</span>
            <div className="h-4 flex-1 rounded-sm bg-gray-100">
              <div
                className="h-4 rounded-sm bg-foret"
                style={{ width: `${(nombre / maximum) * 100}%` }}
              />
            </div>
            <span className="w-10 text-right font-medium">{nombre}</span>
          </div>
        ))}
      </div>
    </Carte>
  );
}

export function TableauDeBord() {
  const [indicateurs, setIndicateurs] = useState<Indicateurs | null>(null);
  const [aTraiter, setATraiter] = useState<Support[]>([]);
  const [erreur, setErreur] = useState("");

  useEffect(() => {
    Promise.all([
      api<Indicateurs>("/api/v1/dashboard"),
      api<Support[]>("/api/v1/dashboard/a-traiter"),
    ])
      .then(([ind, supports]) => {
        setIndicateurs(ind);
        setATraiter(supports);
      })
      .catch((e) => setErreur(e.message));
  }, []);

  if (erreur) return <MessageErreur>{erreur}</MessageErreur>;
  if (!indicateurs) return <p className="text-sm text-gray-500">Chargement…</p>;

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-foret">Tableau de bord</h1>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <Tuile libelle="Effacés aujourd'hui" valeur={indicateurs.supports_traites_jour} />
        <Tuile libelle="Effacés · 7 jours" valeur={indicateurs.supports_traites_semaine} />
        <Tuile libelle="Effacés · 30 jours" valeur={indicateurs.supports_traites_mois} />
        <Tuile libelle="Capacité effacée" valeur={capaciteLisible(indicateurs.capacite_effacee_octets)} />
        <Tuile libelle="Durée moyenne" valeur={dureeLisible(indicateurs.duree_moyenne_secondes)} />
        <Tuile libelle="Taux de réussite" valeur={pourcentage(indicateurs.taux_reussite)} />
      </div>

      {/* Les échecs et non-effaçables : VISIBLES, jamais cachés. */}
      <Carte titre={`À traiter — échecs et supports non effaçables (${aTraiter.length})`}>
        {aTraiter.length === 0 ? (
          <p className="text-sm text-gray-500">Aucun support en échec. Rien à traiter.</p>
        ) : (
          <Tableau entetes={["Code interne", "N° de série", "Modèle", "Statut", ""]}>
            {aTraiter.map((support) => (
              <Ligne key={support.id}>
                <Cellule>
                  <span className="font-mono text-xs">{support.code_interne}</span>
                </Cellule>
                <Cellule>{support.numero_serie ?? "—"}</Cellule>
                <Cellule>{support.modele ?? "—"}</Cellule>
                <Cellule>
                  <StatutSupportBadge statut={support.statut} />
                </Cellule>
                <Cellule>
                  <Link to={`/supports/${support.id}`} className="text-cuivre underline">
                    Voir la fiche
                  </Link>
                </Cellule>
              </Ligne>
            ))}
          </Tableau>
        )}
      </Carte>

      <div className="grid gap-4 lg:grid-cols-2">
        <Repartition titre="Répartition par technologie" donnees={indicateurs.repartition_technologie} />
        <Carte titre="Répartition par statut">
          <div className="space-y-2">
            {Object.entries(indicateurs.repartition_statut)
              .sort((a, b) => b[1] - a[1])
              .map(([statut, nombre]) => (
                <div key={statut} className="flex items-center justify-between text-sm">
                  <StatutSupportBadge statut={statut as Support["statut"]} />
                  <span className="font-medium">{nombre}</span>
                </div>
              ))}
            {Object.keys(indicateurs.repartition_statut).length === 0 && (
              <p className="text-sm text-gray-500">Aucun support enregistré</p>
            )}
          </div>
        </Carte>
      </div>
    </div>
  );
}
