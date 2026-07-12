import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { api, connexionApi, jeton } from "./api/client";
import type { Role, Utilisateur } from "./api/types";

interface ContexteAuth {
  utilisateur: Utilisateur | null;
  chargement: boolean;
  connexion: (identifiant: string, motDePasse: string) => Promise<void>;
  deconnexion: () => void;
  aLeRole: (minimum: Role) => boolean;
}

const NIVEAUX: Record<Role, number> = { TECHNICIEN: 1, RESPONSABLE: 2, ADMINISTRATEUR: 3 };

const Contexte = createContext<ContexteAuth | null>(null);

export function FournisseurAuth({ children }: { children: ReactNode }) {
  const [utilisateur, setUtilisateur] = useState<Utilisateur | null>(null);
  const [chargement, setChargement] = useState(true);

  useEffect(() => {
    if (!jeton.lire()) {
      setChargement(false);
      return;
    }
    api<Utilisateur>("/api/v1/auth/me")
      .then(setUtilisateur)
      .catch(() => jeton.effacer())
      .finally(() => setChargement(false));
  }, []);

  const connexion = useCallback(async (identifiant: string, motDePasse: string) => {
    jeton.ecrire(await connexionApi(identifiant, motDePasse));
    setUtilisateur(await api<Utilisateur>("/api/v1/auth/me"));
  }, []);

  const deconnexion = useCallback(() => {
    jeton.effacer();
    setUtilisateur(null);
  }, []);

  const aLeRole = useCallback(
    (minimum: Role) => utilisateur !== null && NIVEAUX[utilisateur.role] >= NIVEAUX[minimum],
    [utilisateur],
  );

  return (
    <Contexte.Provider value={{ utilisateur, chargement, connexion, deconnexion, aLeRole }}>
      {children}
    </Contexte.Provider>
  );
}

export function useAuth(): ContexteAuth {
  const contexte = useContext(Contexte);
  if (!contexte) throw new Error("useAuth doit être utilisé sous FournisseurAuth");
  return contexte;
}
