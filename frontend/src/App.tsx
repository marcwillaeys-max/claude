import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import { FournisseurAuth, useAuth } from "./auth";
import { Layout } from "./components/Layout";
import { Administration } from "./pages/Administration";
import { Certificats } from "./pages/Certificats";
import { ClientFiche, Clients } from "./pages/Clients";
import { Connexion } from "./pages/Connexion";
import { Import } from "./pages/Import";
import { LotFiche, Lots } from "./pages/Lots";
import { Recherche } from "./pages/Recherche";
import { SupportFiche, Supports } from "./pages/Supports";
import { TableauDeBord } from "./pages/TableauDeBord";

function RouteProtegee({ children, admin = false }: { children: ReactNode; admin?: boolean }) {
  const { utilisateur, chargement, aLeRole } = useAuth();
  if (chargement) return null;
  if (!utilisateur) return <Navigate to="/connexion" replace />;
  if (admin && !aLeRole("ADMINISTRATEUR")) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export function App() {
  return (
    <FournisseurAuth>
      <BrowserRouter>
        <Routes>
          <Route path="/connexion" element={<Connexion />} />
          <Route
            element={
              <RouteProtegee>
                <Layout />
              </RouteProtegee>
            }
          >
            <Route path="/" element={<TableauDeBord />} />
            <Route path="/clients" element={<Clients />} />
            <Route path="/clients/:id" element={<ClientFiche />} />
            <Route path="/lots" element={<Lots />} />
            <Route path="/lots/:id" element={<LotFiche />} />
            <Route path="/supports" element={<Supports />} />
            <Route path="/supports/:id" element={<SupportFiche />} />
            <Route path="/import" element={<Import />} />
            <Route path="/certificats" element={<Certificats />} />
            <Route path="/recherche" element={<Recherche />} />
            <Route
              path="/administration"
              element={
                <RouteProtegee admin>
                  <Administration />
                </RouteProtegee>
              }
            />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </FournisseurAuth>
  );
}
