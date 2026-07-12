import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Client, Lot } from "../api/types";
import { StatutLotBadge } from "../components/StatutBadge";
import { Bouton, Carte, Cellule, Champ, InfoLigne, Ligne, MessageErreur, Tableau } from "../components/ui";
import { useAuth } from "../auth";
import { dateLisible } from "../format";

const CHAMPS: { cle: keyof Client; libelle: string }[] = [
  { cle: "raison_sociale", libelle: "Raison sociale *" },
  { cle: "siret", libelle: "SIRET" },
  { cle: "adresse", libelle: "Adresse" },
  { cle: "code_postal", libelle: "Code postal" },
  { cle: "ville", libelle: "Ville" },
  { cle: "contact_nom", libelle: "Contact" },
  { cle: "contact_email", libelle: "Email" },
  { cle: "contact_telephone", libelle: "Téléphone" },
  { cle: "commentaires", libelle: "Commentaires" },
];

function FormulaireClient({
  initial,
  onEnregistre,
}: {
  initial?: Client;
  onEnregistre: (client: Client) => void;
}) {
  const [valeurs, setValeurs] = useState<Record<string, string>>(() =>
    Object.fromEntries(CHAMPS.map(({ cle }) => [cle, (initial?.[cle] as string) ?? ""])),
  );
  const [erreur, setErreur] = useState("");

  async function soumettre(evenement: React.FormEvent) {
    evenement.preventDefault();
    setErreur("");
    const corps = Object.fromEntries(
      Object.entries(valeurs).map(([cle, valeur]) => [cle, valeur || null]),
    );
    try {
      const client = initial
        ? await api<Client>(`/api/v1/clients/${initial.id}`, {
            method: "PATCH",
            body: JSON.stringify(corps),
          })
        : await api<Client>("/api/v1/clients", { method: "POST", body: JSON.stringify(corps) });
      onEnregistre(client);
    } catch (exception) {
      setErreur(exception instanceof Error ? exception.message : "Erreur");
    }
  }

  return (
    <form onSubmit={soumettre} className="grid gap-3 md:grid-cols-3">
      {CHAMPS.map(({ cle, libelle }) => (
        <Champ
          key={cle}
          libelle={libelle}
          value={valeurs[cle]}
          required={cle === "raison_sociale"}
          onChange={(e) => setValeurs((v) => ({ ...v, [cle]: e.target.value }))}
        />
      ))}
      <div className="md:col-span-3">
        <MessageErreur>{erreur}</MessageErreur>
        <Bouton type="submit" className="mt-2">
          {initial ? "Enregistrer" : "Créer le client"}
        </Bouton>
      </div>
    </form>
  );
}

export function Clients() {
  const [clients, setClients] = useState<Client[]>([]);
  const [recherche, setRecherche] = useState("");
  const [creation, setCreation] = useState(false);
  const naviguer = useNavigate();

  const charger = useCallback(() => {
    const parametres = recherche ? `?recherche=${encodeURIComponent(recherche)}` : "";
    api<Client[]>(`/api/v1/clients${parametres}`).then(setClients).catch(() => setClients([]));
  }, [recherche]);

  useEffect(charger, [charger]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-foret">Clients</h1>
        <Bouton onClick={() => setCreation((v) => !v)}>
          {creation ? "Annuler" : "+ Nouveau client"}
        </Bouton>
      </div>
      {creation && (
        <Carte titre="Nouveau client">
          <FormulaireClient
            onEnregistre={(client) => {
              setCreation(false);
              naviguer(`/clients/${client.id}`);
            }}
          />
        </Carte>
      )}
      <input
        placeholder="Rechercher par raison sociale…"
        value={recherche}
        onChange={(e) => setRecherche(e.target.value)}
        className="w-72 rounded border border-gray-300 px-2.5 py-1.5 text-sm focus:border-cuivre focus:outline-none"
      />
      <Carte>
        <Tableau entetes={["N°", "Raison sociale", "Ville", "Contact", "Créé le"]}>
          {clients.map((client) => (
            <Ligne key={client.id} onClick={() => naviguer(`/clients/${client.id}`)}>
              <Cellule>
                <span className="font-mono text-xs">{client.numero_client}</span>
              </Cellule>
              <Cellule>{client.raison_sociale}</Cellule>
              <Cellule>{client.ville ?? "—"}</Cellule>
              <Cellule>{client.contact_nom ?? "—"}</Cellule>
              <Cellule>{dateLisible(client.cree_le)}</Cellule>
            </Ligne>
          ))}
        </Tableau>
        {clients.length === 0 && <p className="text-sm text-gray-500">Aucun client</p>}
      </Carte>
    </div>
  );
}

export function ClientFiche() {
  const { id } = useParams();
  const [client, setClient] = useState<Client | null>(null);
  const [lots, setLots] = useState<Lot[]>([]);
  const [edition, setEdition] = useState(false);
  const [erreur, setErreur] = useState("");
  const { aLeRole } = useAuth();

  useEffect(() => {
    api<Client>(`/api/v1/clients/${id}`).then(setClient).catch((e) => setErreur(e.message));
    api<Lot[]>(`/api/v1/lots?client_id=${id}`).then(setLots).catch(() => setLots([]));
  }, [id]);

  if (erreur) return <MessageErreur>{erreur}</MessageErreur>;
  if (!client) return <p className="text-sm text-gray-500">Chargement…</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-foret">
          {client.raison_sociale}{" "}
          <span className="font-mono text-sm text-cuivre">{client.numero_client}</span>
          {client.archive === 1 && (
            <span className="ml-2 rounded bg-slate-200 px-2 py-0.5 text-xs">Archivé</span>
          )}
        </h1>
        <div className="flex gap-2">
          <Bouton variante="secondaire" onClick={() => setEdition((v) => !v)}>
            {edition ? "Annuler" : "Modifier"}
          </Bouton>
          {aLeRole("RESPONSABLE") && client.archive === 0 && (
            <Bouton
              variante="danger"
              onClick={() =>
                api<Client>(`/api/v1/clients/${client.id}/archiver`, { method: "POST" }).then(setClient)
              }
            >
              Archiver
            </Bouton>
          )}
        </div>
      </div>
      {edition ? (
        <Carte titre="Modifier le client">
          <FormulaireClient
            initial={client}
            onEnregistre={(maj) => {
              setClient(maj);
              setEdition(false);
            }}
          />
        </Carte>
      ) : (
        <Carte titre="Coordonnées">
          <div className="max-w-xl">
            <InfoLigne libelle="SIRET" valeur={client.siret} />
            <InfoLigne
              libelle="Adresse"
              valeur={[client.adresse, client.code_postal, client.ville].filter(Boolean).join(", ") || "—"}
            />
            <InfoLigne libelle="Contact" valeur={client.contact_nom} />
            <InfoLigne libelle="Email" valeur={client.contact_email} />
            <InfoLigne libelle="Téléphone" valeur={client.contact_telephone} />
            <InfoLigne libelle="Commentaires" valeur={client.commentaires} />
          </div>
        </Carte>
      )}
      <Carte titre={`Lots (${lots.length})`}>
        <Tableau entetes={["N° de lot", "Réception", "Statut", "Supports annoncés"]}>
          {lots.map((lot) => (
            <Ligne key={lot.id}>
              <Cellule>
                <Link to={`/lots/${lot.id}`} className="font-mono text-xs text-cuivre underline">
                  {lot.numero_lot}
                </Link>
              </Cellule>
              <Cellule>{lot.date_reception}</Cellule>
              <Cellule>
                <StatutLotBadge statut={lot.statut} />
              </Cellule>
              <Cellule>{lot.nb_supports_annonce ?? "—"}</Cellule>
            </Ligne>
          ))}
        </Tableau>
        {lots.length === 0 && <p className="text-sm text-gray-500">Aucun lot pour ce client</p>}
      </Carte>
    </div>
  );
}
