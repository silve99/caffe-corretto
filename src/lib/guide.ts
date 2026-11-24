import { getCollection, type CollectionEntry } from 'astro:content';
import dati from '../data/sito.json';

export type Guida = CollectionEntry<'guide'>;

// Nome e testi della sezione: si cambiano dal pannello (Dati del sito → Sezione guide).
export const SEZIONE_GUIDE = {
  nome: dati.guide?.nome ?? 'Guide',
  sottotitolo: dati.guide?.sottotitolo ?? '',
  descrizione: dati.guide?.descrizione ?? '',
};

export async function guidePubblicate(): Promise<Guida[]> {
  const tutte = await getCollection('guide', ({ data }) => !data.bozza);
  return tutte.sort((a, b) => b.data.data.getTime() - a.data.data.getTime());
}

export const etichettaTema: Record<string, string> = {
  basi: 'Le basi',
  risparmio: 'Risparmio',
  azioni: 'Azioni',
  obbligazioni: 'Obbligazioni e BTP',
  'etf-fondi': 'ETF e fondi',
  cripto: 'Cripto',
  tasse: 'Tasse',
};

// Minuti di lettura stimati (circa 200 parole al minuto).
export const minutiLettura = (testo = '') =>
  Math.max(1, Math.round(testo.split(/\s+/).filter(Boolean).length / 200));
