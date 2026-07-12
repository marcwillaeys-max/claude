import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { LigneAudit, Utilisateur, VerificationChaine } from "../api/types";
import { Bouton, Carte, Cellule, Champ, Ligne, MessageErreur, Tableau } from "../components/ui";
import { dateLisible } from "../format";

function GestionUtilisateurs() {
  const [utilisateurs, setUtilisateurs] = useState<Utilisateur[]>([]);
  const [nouveau, setNouveau] = useState({ identifiant: "", nom_complet: "", mot_de_passe: "", role: "TECHNICIEN" });
  const [erreur, setErreur] = useState("");

  const charger = useCallback(() => {
    api<Utilisateur[]>("/api/v1/auth/utilisateurs").then(setUtilisateurs).catch(() => setUtilisateurs([]));
  }, []);
  useEffect(charger, [charger]);

  async function creer(evenement: React.FormEvent) {
    evenement.preventDefault();
    setErreur("");
    try {
      await api("/api/v1/auth/utilisateurs", { method: "POST", body: JSON.stringify(nouveau) });
      setNouveau({ identifiant: "", nom_complet: "", mot_de_passe: "", role: "TECHNICIEN" });
      charger();
    } catch (exception) {
      setErreur(exception instanceof Error ? exception.message : "Erreur");
    }
  }

  return (
    <Carte titre="Utilisateurs">
      <form onSubmit={creer} className="mb-4 flex flex-wrap items-end gap-3 rounded bg-foret-pale p-3">
        <Champ
          libelle="Identifiant"
          required
          value={nouveau.identifiant}
          onChange={(e) => setNouveau((v) => ({ ...v, identifiant: e.target.value }))}
        />
        <Champ
          libelle="Nom complet"
          required
          value={nouveau.nom_complet}
          onChange={(e) => setNouveau((v) => ({ ...v, nom_complet: e.target.value }))}
        />
        <Champ
          libelle="Mot de passe (8 car. min)"
          type="password"
          required
          minLength={8}
          value={nouveau.mot_de_passe}
          onChange={(e) => setNouveau((v) => ({ ...v, mot_de_passe: e.target.value }))}
        />
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-foret">Rôle</span>
          <select
            value={nouveau.role}
            onChange={(e) => setNouveau((v) => ({ ...v, role: e.target.value }))}
            className="rounded border border-gray-300 px-2.5 py-1.5 text-sm focus:border-cuivre focus:outline-none"
          >
            {["TECHNICIEN", "RESPONSABLE", "ADMINISTRATEUR"].map((role) => (
              <option key={role} value={role}>
                {role}
              </option>
            ))}
          </select>
        </label>
        <Bouton type="submit">Créer</Bouton>
        <MessageErreur>{erreur}</MessageErreur>
      </form>
      <Tableau entetes={["Identifiant", "Nom", "Rôle", "Actif", "Dernière connexion", ""]}>
        {utilisateurs.map((utilisateur) => (
          <Ligne key={utilisateur.id}>
            <Cellule>
              <span className="font-mono text-xs">{utilisateur.identifiant}</span>
            </Cellule>
            <Cellule>{utilisateur.nom_complet}</Cellule>
            <Cellule>{utilisateur.role}</Cellule>
            <Cellule>{utilisateur.actif === 1 ? "Oui" : "Non"}</Cellule>
            <Cellule>{dateLisible(utilisateur.derniere_conn)}</Cellule>
            <Cellule>
              {utilisateur.actif === 1 && (
                <button
                  onClick={() =>
                    api(`/api/v1/auth/utilisateurs/${utilisateur.id}/desactiver`, { method: "POST" }).then(
                      charger,
                    )
                  }
                  className="text-red-700 underline"
                >
                  Désactiver
                </button>
              )}
            </Cellule>
          </Ligne>
        ))}
      </Tableau>
    </Carte>
  );
}

function JournalAudit() {
  const [lignes, setLignes] = useState<LigneAudit[]>([]);
  const [verification, setVerification] = useState<VerificationChaine | null>(null);

  useEffect(() => {
    api<LigneAudit[]>("/api/v1/audit?limite=100").then(setLignes).catch(() => setLignes([]));
  }, []);

  return (
    <Carte titre="Journal d'audit — chaîné par hash, inaltérable sans détection">
      <div className="mb-3 flex items-center gap-3">
        <Bouton
          variante="secondaire"
          onClick={() => api<VerificationChaine>("/api/v1/audit/verify").then(setVerification)}
        >
          Vérifier l'intégrité de la chaîne
        </Bouton>
        {verification &&
          (verification.valide ? (
            <span className="rounded bg-foret px-2 py-1 text-xs font-bold text-white">
              ✓ Chaîne intègre — {verification.nb_lignes} lignes vérifiées
            </span>
          ) : (
            <span className="rounded bg-red-600 px-2 py-1 text-xs font-bold text-white">
              ✗ CHAÎNE ROMPUE — {verification.ruptures.length} rupture(s)
            </span>
          ))}
      </div>
      {verification && !verification.valide && (
        <ul className="mb-3 space-y-1 text-sm text-red-900">
          {verification.ruptures.map((rupture) => (
            <li key={`${rupture.audit_id}-${rupture.raison}`}>
              Ligne {rupture.audit_id} : {rupture.raison}
            </li>
          ))}
        </ul>
      )}
      <Tableau entetes={["#", "Horodatage", "Utilisateur", "Action", "Entité", "Détails"]}>
        {lignes.map((ligne) => (
          <Ligne key={ligne.id}>
            <Cellule>{ligne.id}</Cellule>
            <Cellule>{dateLisible(ligne.horodatage)}</Cellule>
            <Cellule>{ligne.utilisateur_id ?? "—"}</Cellule>
            <Cellule>
              <span className="font-mono text-xs">{ligne.action}</span>
            </Cellule>
            <Cellule>
              {ligne.entite}
              {ligne.entite_id !== null && ` #${ligne.entite_id}`}
            </Cellule>
            <Cellule>
              <span className="block max-w-xs truncate font-mono text-xs" title={ligne.details ?? ""}>
                {ligne.details ?? "—"}
              </span>
            </Cellule>
          </Ligne>
        ))}
      </Tableau>
    </Carte>
  );
}

export function Administration() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-foret">Administration</h1>
      <GestionUtilisateurs />
      <JournalAudit />
    </div>
  );
}
