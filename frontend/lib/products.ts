export interface ProductConfig {
  id: string;
  name: string;
  subtitle: string;
  shortLabel: string;
  apiPrefix: string;
  lpvRef: string;
  placeholder: string;
  suggestions: { label: string; text: string; auditAnchor?: string }[];
}

export const PRODUCTS: ProductConfig[] = [
  {
    id: "blitzschutz",
    name: "Blitzschutz",
    subtitle: "Äußere Blitzschutzanlage · LPV B04 §8.1 · 33€/Messstelle",
    shortLabel: "⚡",
    apiPrefix: "/api/blitzschutz",
    lpvRef: "MA570",
    placeholder: "Beschreiben Sie Ihre Blitzschutzanlage...",
    suggestions: [
      {
        label: "🏫 Schule Würzburg — komplett",
        text: "Volksschule in Würzburg, 97080, Schulstraße 12. 35 Trennstellen, Schutzklasse III, Kupferableitungen. Wiederkehrende Prüfung, Rahmenvertrag vorhanden.",
        auditAnchor: "s1",
      },
      {
        label: "🏥 Krankenhaus Hamburg — komplex",
        text: "Krankenhaus in Hamburg, 120 Ableitungen, Schutzklasse II, Sonderbau nach §2 SPrüfV. Erstprüfung vor Inbetriebnahme, kein Rahmenvertrag.",
        auditAnchor: "s2",
      },
      {
        label: "🏭 Industriehalle — grob",
        text: "Ich habe eine Industriehalle in Augsburg, brauche ein Angebot für die Blitzschutzprüfung. Ungefähr 80 Messstellen.",
        auditAnchor: "s3",
      },
      {
        label: "🏠 Kleines Wohngebäude",
        text: "Einfamilienhaus in München, Blitzschutzanlage mit 4 Ableitungen.",
        auditAnchor: "s4",
      },
    ],
  },
  {
    id: "dguv_v3",
    name: "DGUV V3",
    subtitle: "Ortsfeste elektrische Anlage · LPV B04 Kap. 2 · 250€ + m²×Kat",
    shortLabel: "V3",
    apiPrefix: "/api/dguv-v3",
    lpvRef: "MA507",
    placeholder: "Beschreiben Sie Ihre elektrische Anlage...",
    suggestions: [
      {
        label: "🏢 Bürogebäude Regensburg — Standard",
        text: "Bürogebäude in Regensburg, Kumpfmühler Straße 52, 93051. Circa 2.000 m², Baujahr 2017, TN-C-S Netzform, Netzbetreiber Rewag. 8 Unterverteilungen, 2 Hauptverteilungen.",
        auditAnchor: "s9",
      },
      {
        label: "🏭 Industrieanlage — komplex mit NEA",
        text: "Industrieanlage in Augsburg, 8.000 m² Produktionsfläche, 20 Unterverteilungen, 4 Hauptverteilungen, 1 NSHV. Netzersatzanlage vorhanden, 400 kVA Trafo. Erstprüfung, kein Rahmenvertrag.",
        auditAnchor: "s10",
      },
      {
        label: "🏥 Krankenhaus — Sonderfläche",
        text: "Krankenhaus München, 20.000 m², davon OP-Säle und Intensivstation. Sicherheitsstromversorgung und Netzersatzanlage vorhanden. 30 UV, 5 HV, 2 NSHV.",
        auditAnchor: "s11",
      },
      {
        label: "👴 Seniorentreff — klein",
        text: "Seniorentreff in Regensburg, kleines Beratungsbüro, circa 200 Quadratmeter, 1 Unterverteilung.",
        auditAnchor: "s12",
      },
    ],
  },
];

export const DEFAULT_PRODUCT = PRODUCTS[0];
