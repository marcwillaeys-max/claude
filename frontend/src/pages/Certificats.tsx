import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, telechargerFichier } from "../api/client";
import type { Certificat, Operation, Support } from "../api/types";
import { ResultatBadge } from "../components/StatutBadge";
import { Bouton, Carte, Cellule, Ligne, MessageErreur, Tableau } from "../components/ui";
import { dateLisible } from "../format";

/** Miroir de la règle bloquante du backend, pour expliquer le refus AVANT le clic. */
function raisonInegibilite(
  operation: Operation,
  support: Support | undefined,
  dejaCertifiee: boolean,
): string | null {
  if (dejaCertifiee) return "Un certificat existe déjà pour cette opération";
  if (operation.resultat !== "SUCCES") return `Résultat ${operation.resultat} : non certifiable`;
  if (operation.verification_faite === 0) return "Pas de vérification post-effacement";
  if (operation.verification_ok !== 1) return "Vérification post-effacement négative";
  if (support && (support.statut === "NON_EFFACABLE" || support.statut === "ECHEC"))
    return `Support ${support.statut} → destruction physique, pas de certificat`;
  return null;
}

export function Certificats() {
  const [operations, setOperations] = useState<Operation[]>([]);
  const [certificats, setCertificats] = useState<Certificat[]>([]);
  const [supports, setSupports] = useState<Support[]>([]);
  const [erreur, setErreur] = useState("");

  const charger = useCallback(() => {
    api<Operation[]>("/api/v1/operations").then(setOperations).catch(() => setOperations([]));
    api<Certificat[]>("/api/v1/certificats").then(setCertificats).catch(() => setCertificats([]));
    api<Support[]>("/api/v1/supports").then(setSupports).catch(() => setSupports([]));
  }, []);
  useEffect(charger, [charger]);

  const codeInterne = (supportId: number) =>
    supports.find((s) => s.id === supportId)?.code_interne ?? `#${supportId}`;
  const certificatDe = (operationId: number) =>
    certificats.find((c) => c.operation_id === operationId);

  async function generer(operationId: number) {
    setErreur("");
    try {
      await api<Certificat>("/api/v1/certificats", {
        method: "POST",
        body: JSON.stringify({ operation_id: operationId }),
      });
      charger();
    } catch (exception) {
      setErreur(exception instanceof Error ? exception.message : "Erreur");
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-foret">Certificats d'effacement</h1>
      <MessageErreur>{erreur}</MessageErreur>
      <Carte titre="Opérations importées — génération de certificat">
        <p className="mb-3 text-sm text-gray-600">
          Un certificat n'est délivrable que pour un effacement en <strong>SUCCÈS</strong> avec{" "}
          <strong>vérification post-effacement positive</strong>. Tout autre cas est bloqué.
        </p>
        <Tableau entetes={["Support", "Méthode", "Début", "Résultat", "Vérif.", "Certificat"]}>
          {operations.map((operation) => {
            const certificat = certificatDe(operation.id);
            const support = supports.find((s) => s.id === operation.support_id);
            const raison = raisonInegibilite(operation, support, certificat !== undefined);
            return (
              <Ligne key={operation.id}>
                <Cellule>
                  <Link
                    to={`/supports/${operation.support_id}`}
                    className="font-mono text-xs text-cuivre underline"
                  >
                    {codeInterne(operation.support_id)}
                  </Link>
                </Cellule>
                <Cellule>{operation.methode}</Cellule>
                <Cellule>{dateLisible(operation.debut)}</Cellule>
                <Cellule>
                  <ResultatBadge resultat={operation.resultat} />
                </Cellule>
                <Cellule>
                  {operation.verification_faite === 0
                    ? "—"
                    : operation.verification_ok === 1
                      ? "✓"
                      : "✗"}
                </Cellule>
                <Cellule>
                  {certificat ? (
                    <span className="font-mono text-xs">{certificat.numero_cert}</span>
                  ) : (
                    <span className="inline-flex items-center gap-2">
                      <Bouton
                        disabled={raison !== null}
                        title={raison ?? undefined}
                        onClick={() => generer(operation.id)}
                      >
                        Générer
                      </Bouton>
                      {raison && <span className="text-xs text-red-800">{raison}</span>}
                    </span>
                  )}
                </Cellule>
              </Ligne>
            );
          })}
        </Tableau>
        {operations.length === 0 && <p className="text-sm text-gray-500">Aucune opération importée</p>}
      </Carte>
      <Carte titre={`Certificats émis (${certificats.length})`}>
        <Tableau entetes={["N°", "Généré le", "Empreinte des données", "Clé", ""]}>
          {certificats.map((certificat) => (
            <Ligne key={certificat.id}>
              <Cellule>
                <span className="font-mono text-xs">{certificat.numero_cert}</span>
              </Cellule>
              <Cellule>{dateLisible(certificat.genere_le)}</Cellule>
              <Cellule>
                <span className="font-mono text-xs" title={certificat.contenu_sha256}>
                  {certificat.contenu_sha256.slice(0, 16)}…
                </span>
              </Cellule>
              <Cellule>
                <span className="font-mono text-xs">{certificat.cle_publique_id}</span>
              </Cellule>
              <Cellule>
                <span className="flex gap-3">
                  <button
                    onClick={() =>
                      telechargerFichier(
                        `/api/v1/certificats/${certificat.id}/pdf`,
                        `${certificat.numero_cert}.pdf`,
                      )
                    }
                    className="text-cuivre underline"
                  >
                    Télécharger le PDF
                  </button>
                  <a
                    href={`/verif/${certificat.token_verif}`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-foret underline"
                  >
                    Page de vérification
                  </a>
                </span>
              </Cellule>
            </Ligne>
          ))}
        </Tableau>
        {certificats.length === 0 && <p className="text-sm text-gray-500">Aucun certificat émis</p>}
      </Carte>
    </div>
  );
}
