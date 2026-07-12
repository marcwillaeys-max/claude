export type Role = "TECHNICIEN" | "RESPONSABLE" | "ADMINISTRATEUR";

export type StatutSupport =
  | "EN_ATTENTE"
  | "EN_COURS"
  | "EFFACE_VERIFIE"
  | "EFFACE_NON_VERIFIE"
  | "ECHEC"
  | "NON_EFFACABLE"
  | "DETRUIT_PHYSIQUEMENT";

export type StatutLot = "OUVERT" | "EN_COURS" | "TERMINE" | "CLOTURE";

export interface Utilisateur {
  id: number;
  identifiant: string;
  nom_complet: string;
  role: Role;
  actif: number;
  cree_le: string;
  derniere_conn: string | null;
}

export interface Client {
  id: number;
  numero_client: string;
  raison_sociale: string;
  siret: string | null;
  adresse: string | null;
  code_postal: string | null;
  ville: string | null;
  contact_nom: string | null;
  contact_email: string | null;
  contact_telephone: string | null;
  commentaires: string | null;
  cree_le: string;
  archive: number;
}

export interface Lot {
  id: number;
  numero_lot: string;
  client_id: number;
  date_reception: string;
  technicien_id: number;
  statut: StatutLot;
  nb_supports_annonce: number | null;
  commentaires: string | null;
  cree_le: string;
  cloture_le: string | null;
}

export interface Support {
  id: number;
  lot_id: number;
  code_interne: string;
  numero_serie: string | null;
  modele: string | null;
  constructeur: string | null;
  capacite_octets: number | null;
  technologie: string | null;
  interface: string | null;
  smart_json: string | null;
  sante: string | null;
  hpa_detecte: number | null;
  dco_detecte: number | null;
  statut: StatutSupport;
  destination: string | null;
  cree_le: string;
}

export interface Operation {
  id: number;
  support_id: number;
  technicien_id: number;
  station: string | null;
  methode: string;
  norme_reference: string;
  nb_passes: number | null;
  debut: string;
  fin: string | null;
  duree_secondes: number | null;
  resultat: "SUCCES" | "ECHEC" | "INTERROMPU";
  verification_faite: number;
  verification_ok: number | null;
  verification_detail: string | null;
  log_sha256: string;
  outil_version: string | null;
  importe_le: string;
}

export interface Certificat {
  id: number;
  numero_cert: string;
  operation_id: number;
  genere_le: string;
  genere_par: number;
  contenu_sha256: string;
  signature: string;
  cle_publique_id: string;
  token_verif: string;
}

export interface ResultatImport {
  deja_importe: boolean;
  statut_support: StatutSupport;
  operation: Operation;
}

export interface Indicateurs {
  supports_traites_jour: number;
  supports_traites_semaine: number;
  supports_traites_mois: number;
  capacite_effacee_octets: number;
  duree_moyenne_secondes: number | null;
  taux_reussite: number | null;
  nb_operations: number;
  repartition_technologie: Record<string, number>;
  repartition_statut: Record<string, number>;
}

export interface LigneAudit {
  id: number;
  horodatage: string;
  utilisateur_id: number | null;
  action: string;
  entite: string;
  entite_id: number | null;
  details: string | null;
  hash_precedent: string;
  hash_courant: string;
}

export interface VerificationChaine {
  valide: boolean;
  nb_lignes: number;
  ruptures: { audit_id: number; raison: string }[];
}
