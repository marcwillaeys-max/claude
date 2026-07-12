import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

const LIENS = [
  { vers: "/", libelle: "Tableau de bord" },
  { vers: "/clients", libelle: "Clients" },
  { vers: "/lots", libelle: "Lots" },
  { vers: "/supports", libelle: "Supports" },
  { vers: "/import", libelle: "Import rapports" },
  { vers: "/certificats", libelle: "Certificats" },
  { vers: "/recherche", libelle: "Recherche" },
];

export function Layout() {
  const { utilisateur, deconnexion, aLeRole } = useAuth();
  const naviguer = useNavigate();

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-56 shrink-0 flex-col bg-foret text-white">
        <div className="border-b border-foret-clair px-4 py-4">
          <div className="text-lg font-bold tracking-wide">ORALYSE</div>
          <div className="text-xs text-cuivre-clair">Effacement sécurisé</div>
        </div>
        <nav className="flex-1 py-2">
          {LIENS.map((lien) => (
            <NavLink
              key={lien.vers}
              to={lien.vers}
              end={lien.vers === "/"}
              className={({ isActive }) =>
                `block border-l-4 px-4 py-2 text-sm ${
                  isActive
                    ? "border-cuivre bg-foret-clair font-medium"
                    : "border-transparent hover:bg-foret-clair/60"
                }`
              }
            >
              {lien.libelle}
            </NavLink>
          ))}
          {aLeRole("ADMINISTRATEUR") && (
            <NavLink
              to="/administration"
              className={({ isActive }) =>
                `block border-l-4 px-4 py-2 text-sm ${
                  isActive
                    ? "border-cuivre bg-foret-clair font-medium"
                    : "border-transparent hover:bg-foret-clair/60"
                }`
              }
            >
              Administration
            </NavLink>
          )}
        </nav>
        <div className="border-t border-foret-clair px-4 py-3 text-xs">
          <div className="font-medium">{utilisateur?.nom_complet}</div>
          <div className="text-cuivre-clair">{utilisateur?.role}</div>
          <button
            onClick={() => {
              deconnexion();
              naviguer("/connexion");
            }}
            className="mt-2 text-white/70 underline hover:text-white"
          >
            Se déconnecter
          </button>
        </div>
      </aside>
      <main className="min-w-0 flex-1 p-6">
        <Outlet />
      </main>
    </div>
  );
}
