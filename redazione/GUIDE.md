# Istruzioni per le guide di Caffè Corretto

Le guide sono la seconda sezione del blog, accanto alle notizie del giorno. Il nome della sezione
(oggi "Caffè Lungo") sta in `src/data/sito.json` → `guide` e si cambia dal pannello: nei testi
delle guide non scriverlo mai, scrivi "le nostre guide" se serve.

Le guide sono **sempreverdi**: devono restare vere e utili per anni e portare lettori da Google
nel tempo. Le modifica solo Daniele, o Claude su sua richiesta.

## 1. Scegliere il tema

1. Prendi il primo argomento non ancora scritto dal **piano editoriale** (sezione 6). Controlla in
   `src/content/guide/` che non esista già una guida sullo stesso argomento.
2. Se nelle notizie della settimana (`src/content/articoli/`) c'è un tema caldo che manca nel piano
   (es. "cos'è lo spread" quando lo spread è in prima pagina), puoi anticiparlo.
3. Pensa a cosa scrive la gente su Google: "cos'è…", "come funziona…", "come si compra…",
   "conviene…?" (senza mai rispondere con un consiglio).

## 2. Regole sui fatti (non si derogano)

1. Solo fatti stabili e verificabili su **fonti ufficiali** (MEF, Banca d'Italia, BCE, Consob,
   Agenzia delle Entrate, Borsa Italiana, documenti originali). Elencale in `fonti`.
2. Aliquote, soglie e regole fiscali: verifica che siano ancora in vigore cercando sul web
   notizie recenti; indica l'anno ("dal 2026…") e ricorda di controllare le regole aggiornate.
3. Niente prezzi o quotazioni del giorno: invecchiano subito. Per i dati di oggi rimanda
   alle notizie con un link a `/articoli/`.
4. Gli esempi numerici sono ipotetici e lo dicono ("un esempio di pura matematica, non una previsione").
5. Nessun consiglio di investimento: mai "compra", "vendi", "conviene", "il migliore ETF".
   Si spiega come funziona, non cosa fare.

## 3. Stile

Lo stesso delle notizie (vedi `ISTRUZIONI.md`, sezione 2), con più calma: è un caffè lungo.

- **Titolo** con la parola chiave all'inizio, max 65 caratteri: "Cos'è un ETF: la guida semplice per chi parte da zero".
- **Attacco** con una scena o un'immagine quotidiana, mai "In questa guida vedremo…".
- Frasi brevi, termini tecnici spiegati tra parentesi la prima volta, esempi con cifre tonde.
- Lettore immaginario: un risparmiatore di 45 anni che non ha mai aperto un conto titoli.

## 4. Struttura (1.000–1.600 parole)

1. Attacco (2–4 frasi, nessun titoletto).
2. `> **In 30 secondi.**` con 3–4 punti.
3. 4–7 sezioni `##` con titoletti che rispondono a domande ("Come si compra", "Quanto costa", "Le tasse, in breve").
   Una tabella quando aiuta (sigle, confronti).
4. Una sezione sui **rischi**, sempre.
5. `**Cosa significa per te:**` 2–3 frasi concrete, senza consigli.
6. `## Domande frequenti`: 3 domande che la gente cerca davvero, risposte di 2–3 frasi.
7. Chiusura con un link interno: alle notizie (`/articoli/`) o a un'altra guida (`/guide/<nome-file>/`).

## 5. Frontmatter e file

File `src/content/guide/<parola-chiave-con-trattini>.md` (es. `cos-e-lo-spread.md`): il nome del file
diventa l'indirizzo `/guide/cos-e-lo-spread/`, quindi **non cambiarlo mai dopo la pubblicazione**.

```yaml
---
titolo: "..."              # max 65 caratteri
descrizione: "..."         # 140–160 caratteri: la meta description di Google
data: 2026-11-24T10:00:00+01:00
tema: basi                 # basi | risparmio | azioni | obbligazioni | etf-fondi | cripto | tasse
livello: principiante      # principiante | intermedio
fonti:
  - nome: "Ministero dell'Economia e delle Finanze"
    url: "https://..."
bozza: false
---
```

Se aggiorni una guida esistente (es. cambia un'aliquota), correggi il testo e aggiungi
`aggiornato: <data>`: Google apprezza le guide tenute aggiornate.

## 6. Piano editoriale (in ordine)

Già pubblicate: Cos'è un ETF · Come si comprano i BTP · Bitcoin spiegato semplice.

1. Cos'è lo spread BTP-Bund e perché ti riguarda (basi)
2. Inflazione: cos'è e come mangia i tuoi risparmi (basi)
3. Come funziona la Borsa: azioni, indici e dividendi (azioni)
4. PAC: cos'è il piano di accumulo e come funziona (etf-fondi)
5. Conto deposito o BTP: le differenze (risparmio)
6. Tassi della BCE: cosa sono e cosa cambiano per mutuo e conto (basi)
7. Cos'è un'obbligazione e come si legge il rendimento (obbligazioni)
8. Interesse composto spiegato con il caffè (risparmio)
9. Fondo d'emergenza: quanti soldi tenere da parte (risparmio)
10. Ethereum spiegato semplice (cripto)
11. Stablecoin: cosa sono e a cosa servono (cripto)
12. Tasse sugli investimenti in Italia: 12,5%, 26% e bollo (tasse)
13. Come leggere il KID di un fondo o di un ETF (etf-fondi)
14. Fondo pensione: come funziona e i vantaggi fiscali (risparmio)
15. Oro: come si investe e cosa sapere (basi)
16. Recessione: cos'è e come si riconosce (basi)
17. Cos'è il FTSE MIB e come si muove Piazza Affari (azioni)
18. Truffe finanziarie online: come riconoscerle (basi)

Quando pubblichi una guida, spostala da questo elenco alla riga "Già pubblicate".

## 7. Revisione e pubblicazione

Come per le notizie: branch `guida-AAAA-MM-GG`, pull request "Guida: <titolo>", rilettura severa
(fatti sulle fonti ufficiali, nessun consiglio, lunghezze di titolo e descrizione, link interni funzionanti),
`npm run build` senza errori, poi unione (squash). Se resta un dubbio serio su un fatto, toglilo;
se la guida non regge, non unire e lascia la pull request aperta con il motivo.
