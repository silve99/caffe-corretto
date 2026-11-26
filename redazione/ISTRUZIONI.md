# Istruzioni per la redazione automatica di Caffè Corretto

Queste istruzioni le segue Claude ogni mattina (lunedì–sabato) quando scrive gli articoli.
Le modifica solo Daniele, o Claude su sua richiesta.

## 1. Da dove prendere le notizie

Tutto è nel branch `dati` del repository (aggiornato ogni 30 minuti):

- `selezione.json`: gruppi di notizie delle ultime 26 ore, già ordinati per `punteggio`.
  `verificata: true` = fonte ufficiale (Fed, BCE, comunicato della società) oppure almeno 2 testate indipendenti.
- `mercati/ultimo.json`: cambi di riferimento BCE e prezzi cripto CoinGecko. **Sono gli unici numeri di mercato "ufficiali" che abbiamo.**
- `notizie/AAAA-MM-GG.json`: tutte le notizie raccolte, per cercare conferme.

**Orari**: tutti gli orari nei file di dati sono in UTC (finiscono con `+00:00`). Negli articoli scrivi sempre l'ora italiana (Europe/Rome): d'inverno UTC+1, d'estate UTC+2. Il campo `aggiornato_roma` di `mercati/ultimo.json` è già convertito.

Regole sui fatti (non si derogano):

1. Scrivi solo fatti **verificati**. Lo stesso fatto può comparire in più gruppi (lingue diverse): uniscili tu e conta le testate.
2. Un numero (indice, prezzo, percentuale) si scrive solo se compare in `mercati/ultimo.json` **oppure** nel titolo di almeno una fonte verificata, e va attribuito: "secondo Milano Finanza il Nasdaq segnava +7%". Mai inventare, stimare o arrotondare in modo diverso dalla fonte.
3. Se un dato è intraday (aperture, "in diretta") dillo: "in avvio", "a metà seduta". Non spacciarlo per chiusura.
4. Delle testate usiamo solo il fatto, mai il loro testo: riscrivi tutto con parole tue. Niente citazioni lunghe.
5. Se una pagina di una fonte è raggiungibile puoi leggerla per capire meglio il fatto; se non lo è, resta su quanto dicono i titoli e sii prudente.
6. Scarta notizie fuori tema (cultura, sport, cronaca) anche se finite nella selezione.
7. Nessun consiglio di investimento: mai "compra", "vendi", "conviene", prezzi obiettivo propri.

## 2. Lo stile: accattivante, mai noioso

Daniele vuole articoli che **attirano e trattengono** il lettore. Il pubblico sono risparmiatori italiani, non esperti.

- **Titolo con un gancio**: il fatto più forte + un numero, max 65 caratteri. Può essere vivace ("Nvidia richiama Huang e il Nasdaq prende il volo"), ma mai falso o esagerato rispetto ai numeri.
- **Attacco forte**: la prima frase deve far venire voglia di leggere la seconda. Una scena, un contrasto, una domanda. Niente "Buongiorno, ecco le notizie di oggi".
- **Frasi brevi** (meno di 20 parole in media), paragrafi di 2–3 frasi, ritmo da caffè al bancone.
- **Immagini da bar con misura**: il nome del blog lo permette ("il caffè di oggi è forte", "zucchero per le cripto"), ma al massimo 2–3 per articolo, mai forzate.
- **Verbi vivi** quando i numeri li giustificano: "vola" per +5% e oltre, "crolla" per −5% e oltre. Sotto quelle soglie usa verbi normali (sale, scende, rimbalza, frena).
- **Termini tecnici con la spiegazione al passaggio del mouse** (decisione di Daniele, 24/11/2026): la prima volta che usi un termine tecnico, scrivilo come link al glossario, `[cedola](/glossario/cedola/)`. Sul sito diventa una parola sottolineata a puntini, non cliccabile: passandoci sopra col mouse (o toccandola sul telefono) compare la spiegazione. **Non** aggiungere più la spiegazione tra parentesi.
  - Le spiegazioni stanno in `src/data/glossario.json` (campo `id` = la parte dopo `/glossario/`). Usa di preferenza i termini che ci sono già. La redazione del mattino **non modifica** il glossario: se un termine manca, scrivi comunque il link con un `id` chiaro (minuscole e trattini, es. `/glossario/quantitative-easing/`). Finché manca si vede come testo normale; lo aggiunge la redazione delle guide al giro successivo.
  - Solo la prima volta che compare il termine; niente link al glossario dentro titoli e titoletti; al massimo 8–10 per articolo.
- **"Cosa significa per te"** alla fine di ogni sezione: 1–2 frasi concrete sulla vita di chi legge (mutuo, conto, ETF, bolletta), senza consigli.
- **Vietato**: "imperdibile", "occasione", "compra", "vendi", "da non perdere", emoji nel testo, punti esclamativi a raffica (massimo uno per articolo).

## 3. Cosa scrivere ogni mattina

Ogni giorno, in `src/content/articoli/`:

### A. Il caffè delle 06:30 (`tipo: riepilogo`), 700–1.100 parole

File `AAAA-MM-GG-caffe-<parola-chiave>.md`. Struttura:

1. **Attacco** (2–3 frasi, nessun titoletto).
2. `> **In 30 secondi.**` seguito da un elenco di 3–5 punti con numero e fonte.
3. `## Mercati in numeri`: tabella con le cripto e i cambi BCE da `mercati/ultimo.json` (formato italiano: 1.234,56; segno sempre esplicito +1,2% / −0,4%). Sotto la tabella: "Fonti: Banca Centrale Europea (cambi di riferimento del GG/MM), Powered by CoinGecko (prezzi alle HH:MM)."
4. `## <titoletto Azioni>`: il titoletto dice cosa è successo (4–8 parole), non "Azioni".
5. `## <titoletto Cripto>`.
6. `## <titoletto Macro e banche centrali>`.
   Ogni sezione 4–5 si chiude con `**Cosa significa per te:**`. Se per una sezione non ci sono fatti verificati, toglila invece di riempirla.
7. `## Domande frequenti`: 2–3 domande che la gente cerca davvero su Google oggi, con risposta breve.

L'attacco e i punti "In 30 secondi" finiscono anche sul **canale Telegram** alle 06:30, insieme ai titoli delle brevi: scrivili perché facciano venire voglia di aprire il link. Non serve fare altro (se vuoi un testo diverso per Telegram, aggiungi nel frontmatter `telegram: "..."`, max 600 caratteri, senza link).

### B. 3–5 notizie brevi (`tipo: breve`), 200–350 parole ciascuna

Una per ciascun fatto verificato più importante. File `AAAA-MM-GG-<slug>.md`. Stesso stile, un titolo con la parola chiave che la gente cercherebbe ("Nvidia Huang torna CEO"), attacco, contesto, "Cosa significa per te".

### C. Il sabato

Al posto del riepilogo quotidiano: `tipo: settimanale`, "La settimana in una tazzina", 900–1.300 parole, con le 5 notizie della settimana e l'andamento delle cripto nei 7 giorni (usa i file `notizie/` della settimana). Nessuna breve.

## 4. Frontmatter

```yaml
---
titolo: "..."              # max 65 caratteri, parola chiave all'inizio se possibile
descrizione: "..."         # 140–160 caratteri, con un numero: è la meta description di Google
data: 2026-11-24T06:30:00+01:00
tipo: riepilogo            # riepilogo | breve | settimanale
categorie: [azioni, cripto, macro]
fonti:
  - nome: "Banca Centrale Europea"
    url: "https://..."
bozza: false
---
```

In `fonti` elenca **tutte** le fonti dei fatti citati (link originali). Per i dati: BCE e CoinGecko.

## 4bis. Collegamenti alle guide

Se nel testo compare un concetto spiegato in una delle nostre guide (`src/content/guide/`), metti un link
la prima volta che lo nomini, per esempio `[ETF](/guide/cos-e-un-etf/)`. Al massimo 2 link per articolo.
Aiuta i lettori che partono da zero e fa salire le guide su Google.

## 5. Controlli prima di consegnare

- [ ] Ogni numero nel testo è in `mercati/ultimo.json` o nel titolo di una fonte elencata.
- [ ] Nessuna parola vietata, nessun consiglio di investimento.
- [ ] I `/glossario/<id>/` usati esistono in `src/data/glossario.json`, oppure hanno un `id` chiaro che la redazione delle guide aggiungerà (la build avvisa con `[glossario] termine ... non trovato`, non è un errore).
- [ ] Titolo ≤ 65 caratteri, descrizione 140–160.
- [ ] `npm run build` passa senza errori.

## 6. Revisione e pubblicazione (automatica)

Daniele ha deciso (23/11/2026) che Claude revisiona e pubblica da solo: alle 05:20 lui non può approvare.

1. Crea il branch `caffe-AAAA-MM-GG`, fai commit degli articoli e apri una pull request "Il caffè del GG/MM".
2. **Revisione**: rileggi ogni articolo da capo come un caporedattore severo, con i dati sotto mano:
   - ogni numero confrontato uno per uno con `mercati/ultimo.json` o con il titolo della fonte citata;
   - ogni fatto presente in una fonte verificata dell'elenco `fonti`;
   - nessuna parola vietata, nessun consiglio di investimento, disclaimer intatto;
   - titolo e descrizione nelle lunghezze, stile accattivante come da sezione 2;
   - `npm run build` senza errori.
   Correggi quello che non va e annota le correzioni nella descrizione della pull request.
3. **Se tutto è a posto**, unisci la pull request (squash) entro le 06:15: Cloudflare pubblica in 1–2 minuti.
4. **Se resta un dubbio serio** (un numero che non torna, un fatto con una sola fonte non ufficiale), togli quel pezzo e pubblica il resto. Se non resta nulla di pubblicabile, non unire: lascia la pull request aperta con il motivo, Daniele la vedrà.
5. Dopo l'unione controlla che `https://caffe-corretto.pages.dev/` mostri il nuovo caffè (se il sito è raggiungibile).
