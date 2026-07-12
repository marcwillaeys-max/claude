import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Client, Lot, Support } from "../api/types";
import { useAuth } from "../auth";
import { StatutLotBadge, StatutSupportBadge } from "../components/StatutBadge";
import { Bouton, Carte, Cellule, Champ, InfoLigne, Ligne, MessageErreur, Tableau } from "../components/ui";
import { capaciteLisible } from "../format";

const STATUTS_EFFACES = ["EFFACE_VERIFIE", "EFFACE_NON_VERIFIE", "DETRUIT_PHYSIQUEMENT"];

export function Lots() {
  const [lots, setLots] = useState<Lot[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [filtreStatut, setFiltreStatut] = useState("");
  const [filtreClient, setFiltreClient] = useState("");
  const [creation, setCreation] = useState(false);
  const [nouveau, setNouveau] = useState({ client_id: "", date_reception: "", nb_supports_annonce: "" });
  const [erreur, setErreur] = useState("");
  const naviguer = useNavigate();

  const charger = useCallback(() => {
    const parametres = new URLSearchParams();
    if (filtreStatut) parametres.set("statut", filtreStatut);
    if (filtreClient) parametres.set("client_id", filtreClient);
    api<Lot[]>(`/api/v1/lots?${parametres}`).then(setLots).catch(() => setLots([]));
  }, [filtreStatut, filtreClient]);

  useEffect(charger, [charger]);
  useEffect(() => {
    api<Client[]>("/api/v1/clients").then(setClients).catch(() => setClients([]));
  }, []);

  const nomClient = (id: number) => clients.find((c) => c.id === id)?.raison_sociale ?? `#${id}`;

  async function creer(evenement: React.FormEvent) {
    evenement.preventDefault();
    setErreur("");
    try {
      const lot = await api<Lot>("/api/v1/lots", {
        method: "POST",
        body: JSON.stringify({
          client_id: Number(nouveau.client_id),
          date_reception: nouveau.date_reception,
          nb_supports_annonce: nouveau.nb_supports_annonce ? Number(nouveau.nb_supports_annonce) : null,
        }),
      });
      naviguer(`/lots/${lot.id}`);
    } catch (exception) {
      setErreur(exception instanceof Error ? exception.message : "Erreur");
    }
  }

  const classeSelect =
    "rounded border border-gray-300 px-2.5 py-1.5 text-sm focus:border-cuivre focus:outline-none";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-foret">Lots</h1>
        <Bouton onClick={() => setCreation((v) => !v)}>{creation ? "Annuler" : "+ Nouveau lot"}</Bouton>
      </div>
      {creation && (
        <Carte titre="Nouveau lot — prise en charge de matériel">
          <form onSubmit={creer} className="flex flex-wrap items-end gap-3">
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-foret">Client *</span>
              <select
                required
                value={nouveau.client_id}
                onChange={(e) => setNouveau((v) => ({ ...v, client_id: e.target.value }))}
                className={classeSelect}
              >
                <option value="">— choisir —</option>
                {clients.map((client) => (
                  <option key={client.id} value={client.id}>
                    {client.raison_sociale}
                  </option>
                ))}
              </select>
            </label>
            <Champ
              libelle="Date de réception *"
              type="date"
              required
              value={nouveau.date_reception}
              onChange={(e) => setNouveau((v) => ({ ...v, date_reception: e.target.value }))}
            />
            <Champ
              libelle="Nb supports annoncés"
              type="number"
              min={0}
              value={nouveau.nb_supports_annonce}
              onChange={(e) => setNouveau((v) => ({ ...v, nb_supports_annonce: e.target.value }))}
            />
            <Bouton type="submit">Créer le lot</Bouton>
            <MessageErreur>{erreur}</MessageErreur>
          </form>
        </Carte>
      )}
      <div className="flex gap-3">
        <select value={filtreStatut} onChange={(e) => setFiltreStatut(e.target.value)} className={classeSelect}>
          <option value="">Tous les statuts</option>
          {["OUVERT", "EN_COURS", "TERMINE", "CLOTURE"].map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <select value={filtreClient} onChange={(e) => setFiltreClient(e.target.value)} className={classeSelect}>
          <option value="">Tous les clients</option>
          {clients.map((client) => (
            <option key={client.id} value={client.id}>
              {client.raison_sociale}
            </option>
          ))}
        </select>
      </div>
      <Carte>
        <Tableau entetes={["N° de lot", "Client", "Réception", "Statut", "Annoncés"]}>
          {lots.map((lot) => (
            <Ligne key={lot.id} onClick={() => naviguer(`/lots/${lot.id}`)}>
              <Cellule>
                <span className="font-mono text-xs">{lot.numero_lot}</span>
              </Cellule>
              <Cellule>{nomClient(lot.client_id)}</Cellule>
              <Cellule>{lot.date_reception}</Cellule>
              <Cellule>
                <StatutLotBadge statut={lot.statut} />
              </Cellule>
              <Cellule>{lot.nb_supports_annonce ?? "—"}</Cellule>
            </Ligne>
          ))}
        </Tableau>
        {lots.length === 0 && <p className="text-sm text-gray-500">Aucun lot</p>}
      </Carte>
    </div>
  );
}

const TECHNOLOGIES = ["HDD_SATA", "SSD_SATA", "SSD_NVME", "SAS", "USB", "SD", "SED", "INCONNU"];

export function LotFiche() {
  const { id } = useParams();
  const { aLeRole } = useAuth();
  const [lot, setLot] = useState<Lot | null>(null);
  const [supports, setSupports] = useState<Support[]>([]);
  const [ajout, setAjout] = useState(false);
  const [nouveau, setNouveau] = useState({ numero_serie: "", modele: "", technologie: "", capacite_octets: "" });
  const [erreur, setErreur] = useState("");

  const charger = useCallback(() => {
    api<Lot>(`/api/v1/lots/${id}`).then(setLot).catch((e) => setErreur(e.message));
    api<Support[]>(`/api/v1/supports?lot_id=${id}`).then(setSupports).catch(() => setSupports([]));
  }, [id]);
  useEffect(charger, [charger]);

  if (erreur && !lot) return <MessageErreur>{erreur}</MessageErreur>;
  if (!lot) return <p className="text-sm text-gray-500">Chargement…</p>;

  const effaces = supports.filter((s) => STATUTS_EFFACES.includes(s.statut)).length;
  const total = lot.nb_supports_annonce ?? supports.length;
  const avancement = total > 0 ? Math.round((effaces / total) * 100) : 0;

  async function ajouterSupport(evenement: React.FormEvent) {
    evenement.preventDefault();
    setErreur("");
    try {
      await api<Support>("/api/v1/supports", {
        method: "POST",
        body: JSON.stringify({
          lot_id: lot!.id,
          numero_serie: nouveau.numero_serie || null,
          modele: nouveau.modele || null,
          technologie: nouveau.technologie || null,
          capacite_octets: nouveau.capacite_octets ? Number(nouveau.capacite_octets) : null,
        }),
      });
      setNouveau({ numero_serie: "", modele: "", technologie: "", capacite_octets: "" });
      charger();
    } catch (exception) {
      setErreur(exception instanceof Error ? exception.message : "Erreur");
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-foret">
          Lot <span className="font-mono text-cuivre">{lot.numero_lot}</span>{" "}
          <StatutLotBadge statut={lot.statut} />
        </h1>
        {aLeRole("RESPONSABLE") && lot.statut !== "CLOTURE" && (
          <Bouton
            variante="secondaire"
            onClick={() => api<Lot>(`/api/v1/lots/${lot.id}/cloturer`, { method: "POST" }).then(setLot)}
          >
            Clôturer le lot
          </Bouton>
        )}
      </div>
      <Carte>
        <div className="max-w-xl">
          <InfoLigne
            libelle="Client"
            valeur={
              <Link to={`/clients/${lot.client_id}`} className="text-cuivre underline">
                Voir la fiche client
              </Link>
            }
          />
          <InfoLigne libelle="Réception" valeur={lot.date_reception} />
          <InfoLigne libelle="Supports annoncés" valeur={lot.nb_supports_annonce} />
          <InfoLigne libelle="Clôturé le" valeur={lot.cloture_le} />
        </div>
        <div className="mt-3">
          <div className="mb-1 flex justify-between text-xs text-gray-600">
            <span>
              Avancement : {effaces}/{total} supports effacés ou détruits
            </span>
            <span>{avancement} %</span>
          </div>
          <div className="h-3 rounded-sm bg-gray-100">
            <div className="h-3 rounded-sm bg-cuivre" style={{ width: `${Math.min(avancement, 100)}%` }} />
          </div>
        </div>
      </Carte>
      <Carte titre={`Supports du lot (${supports.length})`}>
        <div className="mb-3 flex items-center justify-between">
          <span className="text-sm text-gray-500">
            Chaque support reçoit un code interne unique à coller (QR).
          </span>
          <Bouton variante="secondaire" onClick={() => setAjout((v) => !v)}>
            {ajout ? "Annuler" : "+ Ajouter un support"}
          </Bouton>
        </div>
        {ajout && (
          <form onSubmit={ajouterSupport} className="mb-4 flex flex-wrap items-end gap-3 rounded bg-foret-pale p-3">
            <Champ
              libelle="N° de série"
              value={nouveau.numero_serie}
              onChange={(e) => setNouveau((v) => ({ ...v, numero_serie: e.target.value }))}
            />
            <Champ
              libelle="Modèle"
              value={nouveau.modele}
              onChange={(e) => setNouveau((v) => ({ ...v, modele: e.target.value }))}
            />
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-foret">Technologie</span>
              <select
                value={nouveau.technologie}
                onChange={(e) => setNouveau((v) => ({ ...v, technologie: e.target.value }))}
                className="rounded border border-gray-300 px-2.5 py-1.5 text-sm focus:border-cuivre focus:outline-none"
              >
                <option value="">—</option>
                {TECHNOLOGIES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </label>
            <Champ
              libelle="Capacité (octets)"
              type="number"
              min={0}
              value={nouveau.capacite_octets}
              onChange={(e) => setNouveau((v) => ({ ...v, capacite_octets: e.target.value }))}
            />
            <Bouton type="submit">Ajouter</Bouton>
            <MessageErreur>{erreur}</MessageErreur>
          </form>
        )}
        <Tableau entetes={["Code interne", "N° de série", "Modèle", "Techno", "Capacité", "Statut"]}>
          {supports.map((support) => (
            <Ligne key={support.id}>
              <Cellule>
                <Link to={`/supports/${support.id}`} className="font-mono text-xs text-cuivre underline">
                  {support.code_interne}
                </Link>
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
        {supports.length === 0 && <p className="text-sm text-gray-500">Aucun support enregistré</p>}
      </Carte>
    </div>
  );
}
