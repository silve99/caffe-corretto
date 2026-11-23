import rss from '@astrojs/rss';
import type { APIContext } from 'astro';
import { articoliPubblicati } from '../lib/articoli';
import { SITO } from '../config';

export async function GET(context: APIContext) {
  const tutti = await articoliPubblicati();
  return rss({
    title: SITO.nome,
    description: SITO.descrizione,
    site: context.site!,
    customData: '<language>it-it</language>',
    items: tutti.slice(0, 50).map((a) => ({
      title: a.data.titolo,
      description: a.data.descrizione,
      pubDate: a.data.data,
      link: `/articoli/${a.id}/`,
    })),
  });
}
