import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { ResultatImport } from "../api/types";
import { StatutSupportBadge } from "../components/StatutBadge";
import { Carte } from "../components/ui";

interface LigneResultat {
  fichier: string;
  resultat?: ResultatImport;
  erreur?: string;
}

export function Import() {
  const [resultats, setResultats] = useState<LigneResultat[]>([]);
  const [survol, setSurvol] = useState(false);
  const refFichier = useRef<HTMLInputElement>(null);

  async function importer(fichiers: FileList | File[]) {
    for (const fichier of Array.from(fichiers)) {
      const donnees = new FormData();
      donnees.append("fichier", fichier);
      try {
        const resultat = await api<ResultatImport>("/api/v1/operations/import", {
          method: "POST",
          body: donnees,
        });
        setResultats((liste) => [{ fichier: fichier.name, resultat }, ...liste]);
      } catch (exception) {
        setResultats((liste) => [
          { fichier: fichier.name, erreur: exception instanceof Error ? exception.message : "Erreur" },
          ...liste,
        ]);
      }
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-foret">Import des rapports station</h1>
      <p className="max-w-2xl text-sm text-gray-600">
        Déposez les fichiers JSON produits par la station d'effacement. Un rapport malformé ou dont
        l'empreinte SHA-256 ne correspond pas est <strong>rejeté en bloc</strong> — jamais importé
        partiellement.
      </p>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setSurvol(true);
        }}
        onDragLeave={() => setSurvol(false)}
        onDrop={(e) => {
          e.preventDefault();
          setSurvol(false);
          importer(e.dataTransfer.files);
        }}
        onClick={() => refFichier.current?.click()}
        className={`cursor-pointer rounded-md border-2 border-dashed p-10 text-center transition-colors ${
          survol ? "border-cuivre bg-foret-pale" : "border-foret/40 bg-white"
        }`}
      >
        <div className="text-3xl text-cuivre">⬇</div>
        <p className="mt-2 text-sm font-medium text-foret">
          Glissez-déposez les rapports JSON ici, ou cliquez pour choisir
        </p>
        <input
          ref={refFichier}
          type="file"
          accept="application/json,.json"
          multiple
          hidden
          onChange={(e) => e.target.files && importer(e.target.files)}
        />
      </div>
      {resultats.length > 0 && (
        <Carte titre="Résultats d'import">
          <ul className="space-y-2">
            {resultats.map((ligne, indice) => (
              <li
                key={indice}
                className={`rounded border-l-4 px-3 py-2 text-sm ${
                  ligne.erreur ? "border-red-600 bg-red-50" : "border-foret bg-foret-pale"
                }`}
              >
                <span className="font-mono text-xs">{ligne.fichier}</span>
                {ligne.erreur ? (
                  <p className="mt-1 font-medium text-red-900">✗ REJETÉ — {ligne.erreur}</p>
                ) : (
                  <p className="mt-1 flex flex-wrap items-center gap-2">
                    {ligne.resultat!.deja_importe ? (
                      <span className="text-amber-800">Déjà importé — aucun doublon créé.</span>
                    ) : (
                      <span className="text-foret">✓ Importé.</span>
                    )}
                    <span>Statut du support :</span>
                    <StatutSupportBadge statut={ligne.resultat!.statut_support} />
                    <Link
                      to={`/supports/${ligne.resultat!.operation.support_id}`}
                      className="text-cuivre underline"
                    >
                      Voir la fiche
                    </Link>
                  </p>
                )}
              </li>
            ))}
          </ul>
        </Carte>
      )}
    </div>
  );
}
