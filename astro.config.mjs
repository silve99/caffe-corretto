import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// Indirizzo pubblico del sito. Quando ci sarà il dominio, basta cambiarlo qui.
const SITE = process.env.SITE_URL || 'https://caffe-corretto.pages.dev';

export default defineConfig({
  site: SITE,
  trailingSlash: 'always',
  integrations: [sitemap()],
});
