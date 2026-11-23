import { getCollection, type CollectionEntry } from 'astro:content';

export type Articolo = CollectionEntry<'articoli'>;

export async function articoliPubblicati(): Promise<Articolo[]> {
  const tutti = await getCollection('articoli', ({ data }) => !data.bozza && data.tipo !== 'pagina');
  return tutti.sort((a, b) => b.data.data.getTime() - a.data.data.getTime());
}

export const formatoData = (d: Date) =>
  d.toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', timeZone: 'Europe/Rome' });

export const etichettaTipo: Record<string, string> = {
  riepilogo: 'Il caffè delle 06:30',
  breve: 'In breve',
  settimanale: 'La settimana',
};
