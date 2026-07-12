import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { Bouton, Champ, MessageErreur } from "../components/ui";

export function Connexion() {
  const { connexion } = useAuth();
  const naviguer = useNavigate();
  const [identifiant, setIdentifiant] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [erreur, setErreur] = useState("");
  const [enCours, setEnCours] = useState(false);

  async function soumettre(evenement: React.FormEvent) {
    evenement.preventDefault();
    setErreur("");
    setEnCours(true);
    try {
      await connexion(identifiant, motDePasse);
      naviguer("/");
    } catch (exception) {
      setErreur(exception instanceof Error ? exception.message : "Connexion impossible");
    } finally {
      setEnCours(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-foret">
      <form onSubmit={soumettre} className="w-80 space-y-4 rounded-md bg-white p-6 shadow-lg">
        <div className="text-center">
          <div className="text-xl font-bold tracking-wide text-foret">ORALYSE WIPE</div>
          <div className="text-xs text-cuivre">Traçabilité d'effacement sécurisé</div>
        </div>
        <Champ
          libelle="Identifiant"
          value={identifiant}
          onChange={(e) => setIdentifiant(e.target.value)}
          autoFocus
          required
        />
        <Champ
          libelle="Mot de passe"
          type="password"
          value={motDePasse}
          onChange={(e) => setMotDePasse(e.target.value)}
          required
        />
        <MessageErreur>{erreur}</MessageErreur>
        <Bouton type="submit" disabled={enCours} className="w-full">
          {enCours ? "Connexion…" : "Se connecter"}
        </Bouton>
      </form>
    </div>
  );
}
