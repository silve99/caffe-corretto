import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import rehypeGlossario from './src/plugins/rehype-glossario.mjs';
import { readdirSync, readFileSync } from 'node:fs';

// Indirizzo pubblico del sito (dominio proprio dal 26/11/2026). Per cambiarlo basta modificarlo qui.
const SITE = process.env.SITE_URL || 'https://caffecorrettomercati.com';

// Data dell'ultima modifica di ogni articolo e guida, per la mappa del sito (aiuta Google
// a capire cosa è nuovo). Legge "data" e "aggiornato" dal frontmatter; salta le bozze.
function dateContenuti() {
  const date = new Map();
  for (const [cartella, sezione] of [['articoli', 'articoli'], ['guide', 'guide']]) {
    const dir = new URL(`./src/content/${cartella}/`, import.meta.url);
    for (const file of readdirSync(dir).filter((f) => f.endsWith('.md'))) {
      const testa = readFileSync(new URL(file, dir), 'utf8').split(/^---$/m)[1] ?? '';
      if (/^bozza:\s*true/m.test(testa)) continue;
      const campo = (k) => testa.match(new RegExp(`^${k}:\\s*["']?([^"'\\n]+)`, 'm'))?.[1];
      const quando = new Date(campo('aggiornato') ?? campo('data') ?? '');
      if (!isNaN(quando)) date.set(`/${sezione}/${file.replace(/\.md$/, '')}/`, quando);
    }
  }
  return date;
}
const DATE = dateContenuti();

export default defineConfig({
  site: SITE,
  trailingSlash: 'always',
  integrations: [
    sitemap({
      serialize(voce) {
        const quando = DATE.get(new URL(voce.url).pathname);
        if (quando) voce.lastmod = quando.toISOString();
        return voce;
      },
    }),
  ],
  markdown: {
    // [parola](/glossario/id/) → parola sottolineata con la spiegazione al passaggio del mouse
    rehypePlugins: [rehypeGlossario],
  },
});
