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

## Guide

Seconda sezione del sito (nome in `src/data/sito.json` → `guide`, oggi "Caffè Lungo"): guide sempreverdi
in `src/content/guide/`, pubblicate su `/guide/<nome-file>/`. Istruzioni di scrittura e piano editoriale
in `redazione/GUIDE.md`.

## Glossario (spiegazioni al passaggio del mouse)

Nei testi `[cedola](/glossario/cedola/)` diventa una parola sottolineata a puntini che mostra la spiegazione
al passaggio del mouse o al tocco (plugin `src/plugins/rehype-glossario.mjs`, fumetto in `src/components/Spiegazioni.astro`).
Le spiegazioni stanno in `src/data/glossario.json`, modificabili dal pannello; la pagina `/glossario/` le elenca tutte.

## Cloudflare Pages

- Comando di build: `npm run build`
- Cartella di output: `dist`
- Variabile facoltativa `SITE_URL` quando ci sarà il dominio (es. `https://caffecorrettomercati.com`)

## Raccolta notizie

`raccolta/raccogli.py` gira ogni 30 minuti con GitHub Actions (`.github/workflows/raccolta.yml`).
Prende titoli e link da fonti gratuite (RSS e file GKG di GDELT, filtrati per testate e temi economici) (`raccolta/fonti.json`), toglie i doppioni, raggruppa le notizie
uguali, assegna un punteggio e salva tutto nel branch **`dati`**:

- `notizie/AAAA-MM-GG.json`: tutte le notizie del giorno (ora italiana)
- `selezione.json`: le notizie delle ultime 26 ore ordinate per rilevanza; `verificata` = fonte ufficiale o almeno due fonti indipendenti
- `mercati/ultimo.json`: cambi BCE e prezzi cripto (Powered by CoinGecko)
- `stato.json`: esito dell'ultima raccolta fonte per fonte

Serve il secret `COINGECKO_API_KEY` (Settings → Secrets and variables → Actions).

## Pannello di modifica (Pages CMS)

Il file `.pages.yml` configura il pannello gratuito [Pages CMS](https://app.pagescms.org):
si entra con l'account GitHub e si modificano articoli, pagine (chi siamo, contatti, legali)
e i dati del sito (`src/data/sito.json`: nome, descrizione, email, social). Ogni salvataggio
è un commit su `main` e Cloudflare Pages ripubblica il sito in un paio di minuti.

## Canale Telegram

`telegram/invia.py` (workflow `.github/workflows/telegram.yml`) manda sul canale Telegram:

- alle 06:30 il caffè del mattino (attacco, punti "In 30 secondi" e link alle notizie brevi del giorno);
- le notizie brevi uscite da sole, in un unico messaggio;
- ogni nuova guida, appena è online.

Parte quando un contenuto arriva su `main` (se la data è nel futuro aspetta fino a 90 minuti per uscire puntuale)
e ogni ora come rete di sicurezza. Controlla che la pagina sia online prima di inviare, non manda contenuti più
vecchi di 20 ore e ricorda cosa ha inviato in `telegram/inviati.json` del branch `dati`.
Campo facoltativo `telegram:` nel frontmatter (max 600 caratteri) per scegliere il testo del messaggio.

Serve il secret `TELEGRAM_BOT_TOKEN` (il bot deve essere amministratore del canale) e l'indirizzo del canale in
`src/data/sito.json` → `social.telegram` (es. `https://t.me/nomecanale`), che fa comparire anche il riquadro
"Seguici su Telegram" sul sito. Per un canale privato si può usare la variabile `TELEGRAM_CHAT_ID`.
Anteprima senza inviare: Actions → Telegram → Run workflow → "Solo anteprima".
