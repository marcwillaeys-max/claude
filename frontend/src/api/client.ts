export class ErreurApi extends Error {
  constructor(
    public statut: number,
    public detail: string,
  ) {
    super(detail);
  }
}

const CLE_JETON = "oralyse_jeton";

export const jeton = {
  lire: (): string | null => localStorage.getItem(CLE_JETON),
  ecrire: (valeur: string): void => localStorage.setItem(CLE_JETON, valeur),
  effacer: (): void => localStorage.removeItem(CLE_JETON),
};

async function extraireDetail(reponse: Response): Promise<string> {
  try {
    const corps = await reponse.json();
    if (typeof corps.detail === "string") return corps.detail;
    return JSON.stringify(corps.detail ?? corps);
  } catch {
    return `Erreur ${reponse.status}`;
  }
}

export async function api<T>(chemin: string, options: RequestInit = {}): Promise<T> {
  const entetes = new Headers(options.headers);
  const valeurJeton = jeton.lire();
  if (valeurJeton) entetes.set("Authorization", `Bearer ${valeurJeton}`);
  if (options.body && !(options.body instanceof FormData) && !entetes.has("Content-Type")) {
    entetes.set("Content-Type", "application/json");
  }
  const reponse = await fetch(chemin, { ...options, headers: entetes });
  if (!reponse.ok) throw new ErreurApi(reponse.status, await extraireDetail(reponse));
  return (await reponse.json()) as T;
}

export async function connexionApi(identifiant: string, motDePasse: string): Promise<string> {
  const corps = new URLSearchParams({ username: identifiant, password: motDePasse });
  const reponse = await fetch("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: corps,
  });
  if (!reponse.ok) throw new ErreurApi(reponse.status, await extraireDetail(reponse));
  const { access_token } = (await reponse.json()) as { access_token: string };
  return access_token;
}

export async function telechargerFichier(chemin: string, nomFichier: string): Promise<void> {
  const entetes = new Headers();
  const valeurJeton = jeton.lire();
  if (valeurJeton) entetes.set("Authorization", `Bearer ${valeurJeton}`);
  const reponse = await fetch(chemin, { headers: entetes });
  if (!reponse.ok) throw new ErreurApi(reponse.status, await extraireDetail(reponse));
  const blob = await reponse.blob();
  const url = URL.createObjectURL(blob);
  const lien = document.createElement("a");
  lien.href = url;
  lien.download = nomFichier;
  lien.click();
  URL.revokeObjectURL(url);
}
