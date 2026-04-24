export interface ChatMessage {
  role: "user" | "assistant" | "status";
  content: string;
}

export interface TraceStep {
  step: number;
  action: string;
  params?: Record<string, unknown>;
  result_summary?: string;
  reasoning?: string;
  duration_ms?: number;
  batch_size?: number;
}

export interface Kalkulation {
  positionen?: Array<{
    dienstleistung: string;
    beschreibung?: string;
    menge?: number;
    einheitspreis?: number;
    einheit?: string;
    betrag: number;
    berechnung?: string;
  }>;
  zuschlaege?: Array<{ name: string; grund?: string; betrag: number }>;
  rabatte?: Array<{ name: string; grund?: string; betrag: number }>;
  gesamtbetrag?: number;
  rueckfragen?: string[];
  empfehlungen?: Array<{
    dienstleistung: string;
    grund: string;
    geschaetzter_preis?: number;
  }>;
  facts?: Array<{ claim: string; source: string }>;
  raw_response?: string;
}
