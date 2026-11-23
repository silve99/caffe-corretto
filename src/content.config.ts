import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

// Ogni articolo è un file Markdown in src/content/articoli/.
// L'agente scrive qui; con `bozza: true` l'articolo non viene pubblicato.
const articoli = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/articoli' }),
  schema: z.object({
    titolo: z.string().max(110),
    descrizione: z.string().max(170), // meta description SEO
    data: z.coerce.date(),
    tipo: z.enum(['riepilogo', 'breve', 'settimanale', 'pagina']).default('breve'),
    categorie: z.array(z.enum(['azioni', 'cripto', 'macro', 'valute', 'materie-prime'])).default([]),
    fonti: z
      .array(z.object({ nome: z.string(), url: z.string().url() }))
      .default([]),
    bozza: z.boolean().default(false),
  }),
});

export const collections = { articoli };
