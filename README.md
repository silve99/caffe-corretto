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

## Raccolta notizie

`raccolta/raccogli.py` gira ogni 30 minuti con GitHub Actions (`.github/workflows/raccolta.yml`).
Prende titoli e link da fonti gratuite (`raccolta/fonti.json`), toglie i doppioni, raggruppa le notizie
uguali, assegna un punteggio e salva tutto nel branch **`dati`**:

- `notizie/AAAA-MM-GG.json`: tutte le notizie del giorno (ora italiana)
- `selezione.json`: le notizie delle ultime 26 ore ordinate per rilevanza; `verificata` = fonte ufficiale o almeno due fonti indipendenti
- `mercati/ultimo.json`: cambi BCE e prezzi cripto (Powered by CoinGecko)
- `stato.json`: esito dell'ultima raccolta fonte per fonte

Serve il secret `COINGECKO_API_KEY` (Settings → Secrets and variables → Actions).
