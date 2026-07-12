export function capaciteLisible(octets: number | null): string {
  if (octets === null || octets === undefined) return "—";
  let valeur = octets;
  for (const unite of ["octets", "Ko", "Mo", "Go", "To", "Po"]) {
    if (valeur < 1000 || unite === "Po") {
      return unite === "octets" ? `${valeur} ${unite}` : `${valeur.toFixed(2)} ${unite}`;
    }
    valeur /= 1000;
  }
  return `${octets} octets`;
}

export function dureeLisible(secondes: number | null): string {
  if (secondes === null || secondes === undefined) return "—";
  const heures = Math.floor(secondes / 3600);
  const minutes = Math.floor((secondes % 3600) / 60);
  return heures > 0 ? `${heures} h ${String(minutes).padStart(2, "0")} min` : `${minutes} min`;
}

export function dateLisible(iso: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
}

export function pourcentage(ratio: number | null): string {
  return ratio === null || ratio === undefined ? "—" : `${(ratio * 100).toFixed(1)} %`;
}
