// Trasforma i link al glossario in parole con spiegazione al passaggio del mouse (o al tocco).
// Nei testi si scrive: [taglio minimo](/glossario/taglio-minimo/)
// La spiegazione viene da src/data/glossario.json (modificabile dal pannello).
import { readFileSync } from 'node:fs';

const FILE = new URL('../data/glossario.json', import.meta.url);
const PERCORSO = /^\/glossario\/([a-z0-9-]+)\/?$/;

function caricaGlossario() {
  const { termini = [] } = JSON.parse(readFileSync(FILE, 'utf8'));
  return new Map(termini.map((t) => [t.id, t]));
}

function testo(valore) {
  return { type: 'text', value: valore };
}

export default function rehypeGlossario() {
  return (albero, file) => {
    const glossario = caricaGlossario();
    const visita = (nodo) => {
      if (!nodo.children) return;
      nodo.children = nodo.children.map((figlio) => {
        if (figlio.type === 'element' && figlio.tagName === 'a') {
          const m = PERCORSO.exec(String(figlio.properties?.href ?? ''));
          if (m) {
            const voce = glossario.get(m[1]);
            if (!voce) {
              console.warn(`[glossario] termine "${m[1]}" non trovato in src/data/glossario.json (${file?.path ?? ''}): lo mostro come testo normale.`);
              return { type: 'element', tagName: 'span', properties: {}, children: figlio.children };
            }
            return {
              type: 'element',
              tagName: 'span',
              properties: { className: ['termine'], tabIndex: 0, dataTitolo: voce.termine },
              children: [
                ...figlio.children,
                {
                  type: 'element',
                  tagName: 'span',
                  properties: { className: ['termine-spiega'] },
                  children: [testo(` (${voce.spiegazione})`)],
                },
              ],
            };
          }
        }
        visita(figlio);
        return figlio;
      });
    };
    visita(albero);
  };
}
