# Caffè Corretto

Notiziario del mattino su borse, cripto ed economia, pubblicato ogni giorno alle 06:30.
Sito statico [Astro](https://astro.build) ospitato su Cloudflare Pages.

## Comandi

```sh
npm install
npm run dev      # anteprima locale su http://localhost:4321
npm run build    # genera il sito in dist/
```

## Articoli

Ogni articolo è un file Markdown in `src/content/articoli/` (campi definiti in `src/content.config.ts`).
Con `bozza: true` l'articolo resta nel repository ma non viene pubblicato.

## Cloudflare Pages

- Comando di build: `npm run build`
- Cartella di output: `dist`
- Variabile facoltativa `SITE_URL` quando ci sarà il dominio (es. `https://caffecorrettomercati.com`)
