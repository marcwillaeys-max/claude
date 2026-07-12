import type { StatutLot, StatutSupport } from "../api/types";

/** Point de sécurité, pas d'esthétique : ECHEC et NON_EFFACABLE doivent être
 * impossibles à confondre avec un succès. Couleur RÉSERVÉE + icône + libellé —
 * jamais la couleur seule. */
const SUPPORTS: Record<StatutSupport, { classe: string; icone: string; libelle: string }> = {
  EN_ATTENTE: { classe: "bg-gray-200 text-gray-700", icone: "◌", libelle: "En attente" },
  EN_COURS: { classe: "bg-sky-100 text-sky-800", icone: "◔", libelle: "En cours" },
  EFFACE_VERIFIE: { classe: "bg-foret text-white", icone: "✓", libelle: "Effacé · vérifié" },
  EFFACE_NON_VERIFIE: {
    classe: "bg-amber-100 text-amber-900 border border-amber-400",
    icone: "~",
    libelle: "Effacé · NON vérifié",
  },
  ECHEC: { classe: "bg-red-600 text-white font-bold", icone: "✗", libelle: "ÉCHEC" },
  NON_EFFACABLE: {
    classe: "bg-red-950 text-white font-bold border-2 border-dashed border-red-400",
    icone: "⚠",
    libelle: "NON EFFAÇABLE",
  },
  DETRUIT_PHYSIQUEMENT: {
    classe: "bg-slate-700 text-white",
    icone: "▣",
    libelle: "Détruit physiquement",
  },
};

export function StatutSupportBadge({ statut }: { statut: StatutSupport }) {
  const style = SUPPORTS[statut];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs whitespace-nowrap ${style.classe}`}
    >
      <span aria-hidden>{style.icone}</span>
      {style.libelle}
    </span>
  );
}

const LOTS: Record<StatutLot, { classe: string; libelle: string }> = {
  OUVERT: { classe: "bg-foret-pale text-foret", libelle: "Ouvert" },
  EN_COURS: { classe: "bg-sky-100 text-sky-800", libelle: "En cours" },
  TERMINE: { classe: "bg-foret text-white", libelle: "Terminé" },
  CLOTURE: { classe: "bg-slate-200 text-slate-700", libelle: "Clôturé" },
};

export function StatutLotBadge({ statut }: { statut: StatutLot }) {
  const style = LOTS[statut];
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs whitespace-nowrap ${style.classe}`}>
      {style.libelle}
    </span>
  );
}

export function ResultatBadge({ resultat }: { resultat: "SUCCES" | "ECHEC" | "INTERROMPU" }) {
  if (resultat === "SUCCES")
    return (
      <span className="inline-flex items-center gap-1 rounded bg-foret px-2 py-0.5 text-xs text-white">
        ✓ Succès
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1 rounded bg-red-600 px-2 py-0.5 text-xs font-bold text-white">
      ✗ {resultat === "ECHEC" ? "Échec" : "Interrompu"}
    </span>
  );
}
