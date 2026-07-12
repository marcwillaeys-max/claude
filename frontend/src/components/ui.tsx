import type { ReactNode } from "react";

export function Carte({ titre, children, classe = "" }: { titre?: string; children: ReactNode; classe?: string }) {
  return (
    <div className={`rounded-md bg-white shadow-sm ${classe}`}>
      {titre && (
        <div className="border-b border-gray-100 px-4 py-2.5 text-sm font-bold text-foret">{titre}</div>
      )}
      <div className="p-4">{children}</div>
    </div>
  );
}

export function Bouton({
  children,
  variante = "primaire",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variante?: "primaire" | "secondaire" | "danger" }) {
  const classes = {
    primaire: "bg-foret text-white hover:bg-foret-clair",
    secondaire: "border border-foret text-foret hover:bg-foret-pale",
    danger: "bg-red-700 text-white hover:bg-red-800",
  }[variante];
  return (
    <button
      {...props}
      className={`rounded px-3 py-1.5 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${classes} ${props.className ?? ""}`}
    >
      {children}
    </button>
  );
}

export function Champ({
  libelle,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & { libelle: string }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-foret">{libelle}</span>
      <input
        {...props}
        className="w-full rounded border border-gray-300 px-2.5 py-1.5 text-sm focus:border-cuivre focus:outline-none"
      />
    </label>
  );
}

export function MessageErreur({ children }: { children: ReactNode }) {
  if (!children) return null;
  return (
    <div className="rounded border-l-4 border-red-600 bg-red-50 px-3 py-2 text-sm text-red-900">
      {children}
    </div>
  );
}

export function Tableau({ entetes, children }: { entetes: string[]; children: ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b-2 border-foret text-left text-xs uppercase tracking-wide text-foret">
            {entetes.map((entete) => (
              <th key={entete} className="px-2 py-2 font-bold">
                {entete}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

export function Ligne({ children, onClick }: { children: ReactNode; onClick?: () => void }) {
  return (
    <tr
      onClick={onClick}
      className={`border-b border-gray-100 ${onClick ? "cursor-pointer hover:bg-foret-pale" : ""}`}
    >
      {children}
    </tr>
  );
}

export function Cellule({ children }: { children: ReactNode }) {
  return <td className="px-2 py-2 align-middle">{children}</td>;
}

export function InfoLigne({ libelle, valeur }: { libelle: string; valeur: ReactNode }) {
  return (
    <div className="flex justify-between gap-4 border-b border-gray-50 py-1.5 text-sm">
      <span className="font-medium text-foret">{libelle}</span>
      <span className="text-right">{valeur ?? "—"}</span>
    </div>
  );
}
