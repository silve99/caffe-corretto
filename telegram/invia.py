#!/usr/bin/env python3
"""Invio automatico su Telegram di Caffè Corretto.

Gira con GitHub Actions (.github/workflows/telegram.yml). Guarda gli articoli e le guide del sito,
e per ogni contenuto appena uscito (data di pubblicazione passata, già online, non ancora inviato)
manda un messaggio sul canale Telegram:

- il caffè del mattino (tipo riepilogo o settimanale) con l'attacco, i punti "In 30 secondi"
  e i link alle notizie brevi dello stesso giorno;
- le notizie brevi uscite da sole, in un messaggio unico;
- ogni nuova guida di Caffè Lungo (se ne escono più di due insieme, un solo messaggio con l'elenco).

Ricorda cosa ha già inviato nel file `telegram/inviati.json` del branch `dati`.
Usa solo la libreria standard di Python.

Uso:
  python telegram/invia.py --stato ../dati/telegram/inviati.json            # invia davvero
  python telegram/invia.py --stato /tmp/x.json --prova                      # mostra i messaggi senza inviarli
Variabili d'ambiente: TELEGRAM_BOT_TOKEN (obbligatoria per inviare), TELEGRAM_CHAT_ID (facoltativa:
se manca si usa il canale scritto in src/data/sito.json → social.telegram, es. https://t.me/nome → @nome).
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

RADICE = Path(__file__).resolve().parent.parent
ROMA = ZoneInfo("Europe/Rome")
SITO_PREDEFINITO = "https://caffecorrettomercati.com"
# Contenuti più vecchi di così non si inviano più (evita raffiche dopo un guasto o alla prima accensione).
FINESTRA = timedelta(hours=20)
# Se un contenuto esce entro questo tempo, il lavoro aspetta e lo invia puntuale (es. unito alle 05:25, esce alle 06:30).
ATTESA_MASSIMA = timedelta(minutes=90)
GIORNI = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
        "settembre", "ottobre", "novembre", "dicembre"]


# ---------- lettura dei contenuti ----------

def leggi_testata(testo: str) -> tuple[dict, str]:
    """Legge il frontmatter (solo i campi semplici che servono qui) e restituisce (campi, corpo)."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", testo, re.S)
    if not m:
        return {}, testo
    campi = {}
    for riga in m.group(1).splitlines():
        r = re.match(r"^([a-zA-Z_]+):\s*(.*?)\s*$", riga)
        if not r or not r.group(2):
            continue
        chiave, valore = r.groups()
        if valore.startswith('"'):
            try:
                valore = json.loads(valore)
            except json.JSONDecodeError:
                valore = valore.strip('"')
        elif valore.startswith("'") and valore.endswith("'"):
            valore = valore[1:-1].replace("''", "'")
        campi[chiave] = valore
    return campi, m.group(2)


def data_di(valore: str) -> datetime | None:
    try:
        d = datetime.fromisoformat(str(valore).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=ROMA)


def contenuti() -> list[dict]:
    elenco = []
    for sezione, cartella in (("articoli", "articoli"), ("guide", "guide")):
        for file in sorted((RADICE / "src/content" / cartella).glob("*.md")):
            campi, corpo = leggi_testata(file.read_text(encoding="utf-8"))
            quando = data_di(campi.get("data", ""))
            if not quando or str(campi.get("bozza", "false")).lower() == "true":
                continue
            tipo = campi.get("tipo", "breve") if sezione == "articoli" else "guida"
            if tipo == "pagina":
                continue
            elenco.append({
                "chiave": f"{sezione}/{file.stem}",
                "percorso": f"/{sezione}/{file.stem}/",
                "tipo": tipo,
                "titolo": campi.get("titolo", file.stem),
                "descrizione": campi.get("descrizione", ""),
                "telegram": campi.get("telegram", ""),
                "data": quando,
                "corpo": corpo,
            })
    return elenco


# ---------- testo per Telegram (HTML semplice) ----------

def in_linea(testo: str) -> str:
    """Markdown di una riga → HTML di Telegram: tiene il grassetto, toglie link e altri segni."""
    testo = re.sub(r"<[^>]+>", "", testo)                      # tag HTML (es. <span class="su">)
    testo = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", testo)          # immagini
    testo = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", testo)      # [parola](link) → parola
    testo = html.escape(testo, quote=False)
    testo = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", testo)
    testo = re.sub(r"(?<![\w*])[*_](\S.*?\S|\S)[*_](?![\w*])", r"<i>\1</i>", testo)
    return testo.replace("*", "").strip()


def attacco(corpo: str) -> str:
    """Il primo paragrafo di testo (prima del riquadro "In 30 secondi" o del primo titoletto)."""
    for blocco in re.split(r"\n\s*\n", corpo.strip()):
        b = blocco.strip()
        if b and not b.startswith((">", "#", "|", "-", "*", "<", "!")):
            return in_linea(" ".join(b.splitlines()))
    return ""


def punti_30_secondi(corpo: str) -> list[str]:
    m = re.search(r"^>\s*\*\*In 30 secondi\.?\*\*.*?\n((?:>.*\n?)+)", corpo, re.M)
    if not m:
        return []
    punti = []
    for riga in m.group(1).splitlines():
        r = re.match(r"^>\s*[-*]\s+(.*)$", riga)
        if r:
            punti.append(in_linea(r.group(1)))
    return punti


def giorno_esteso(d: datetime) -> str:
    d = d.astimezone(ROMA)
    return f"{GIORNI[d.weekday()]} {d.day} {MESI[d.month - 1]}"


def taglia(testo: str, massimo: int) -> str:
    return testo if len(testo) <= massimo else testo[: massimo - 1].rsplit(" ", 1)[0] + "…"


def link(sito: str, c: dict) -> str:
    return sito.rstrip("/") + c["percorso"]


def messaggio_caffe(sito: str, caffe: dict, brevi: list[dict]) -> tuple[str, str]:
    settimanale = caffe["tipo"] == "settimanale"
    testa = "📅 <b>La settimana in un caffè</b>" if settimanale else "☕ <b>Il caffè delle 06:30</b>"
    righe = [f"{testa} · {giorno_esteso(caffe['data'])}", "", f"<b>{in_linea(caffe['titolo'])}</b>"]
    apertura = in_linea(caffe["telegram"]) if caffe["telegram"] else attacco(caffe["corpo"])
    if apertura:
        righe += ["", taglia(apertura, 600)]
    punti = punti_30_secondi(caffe["corpo"])
    if punti:
        righe += ["", "⏱ <b>In 30 secondi</b>"] + [f"• {p}" for p in punti[:5]]
    elif not apertura:
        righe += ["", in_linea(caffe["descrizione"])]
    if brevi:
        righe += ["", "📌 <b>Anche oggi</b>"]
        righe += [f'• <a href="{html.escape(link(sito, b))}">{in_linea(b["titolo"])}</a>' for b in brevi[:6]]
    righe += ["", "<i>Solo informazione, non consulenza finanziaria.</i>"]
    return "\n".join(righe), ("📅 Leggi la settimana" if settimanale else "☕ Leggi il caffè di oggi")


def messaggio_brevi(sito: str, brevi: list[dict]) -> tuple[str, str]:
    if len(brevi) == 1:
        b = brevi[0]
        testo = "\n".join(["⚡ <b>In breve</b>", "", f"<b>{in_linea(b['titolo'])}</b>", "",
                           in_linea(b["telegram"] or b["descrizione"])])
        return testo, "Leggi la notizia"
    righe = ["⚡ <b>In breve</b>", ""]
    righe += [f'• <a href="{html.escape(link(sito, b))}">{in_linea(b["titolo"])}</a>' for b in brevi[:8]]
    return "\n".join(righe), "Tutte le notizie"


def messaggio_guida(sito: str, guida: dict, nome_sezione: str) -> tuple[str, str]:
    parole = len(guida["corpo"].split())
    minuti = max(1, round(parole / 200))
    righe = [f"📘 <b>Nuova guida di {html.escape(nome_sezione)}</b>", "", f"<b>{in_linea(guida['titolo'])}</b>", "",
             in_linea(guida["telegram"] or guida["descrizione"]), "", f"🕐 {minuti} minuti di lettura, spiegata semplice."]
    return "\n".join(righe), "📘 Leggi la guida"


def messaggio_guide(sito: str, guide: list[dict], nome_sezione: str) -> tuple[str, str]:
    righe = [f"📘 <b>Nuove guide di {html.escape(nome_sezione)}</b>", "",
             "Da leggere con calma, spiegate semplici:", ""]
    righe += [f'• <a href="{html.escape(link(sito, g))}">{in_linea(g["titolo"])}</a>' for g in guide[:10]]
    return "\n".join(righe), "📘 Tutte le guide"


# ---------- rete ----------

def scarica(url: str, timeout: int = 20) -> int:
    richiesta = urllib.request.Request(url, headers={"User-Agent": "caffe-corretto-telegram/1.0"})
    try:
        with urllib.request.urlopen(richiesta, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def e_online(url: str, attesa_massima: int = 600) -> bool:
    """Aspetta (fino a 10 minuti) che Cloudflare abbia pubblicato la pagina."""
    fine = time.time() + attesa_massima
    while True:
        if scarica(url) == 200:
            return True
        if time.time() > fine:
            return False
        time.sleep(30)


def invia(token: str, chat: str, testo: str, url: str, bottone: str) -> None:
    corpo = {
        "chat_id": chat,
        "text": testo,
        "parse_mode": "HTML",
        "link_preview_options": {"url": url, "prefer_large_media": True},
        "reply_markup": {"inline_keyboard": [[{"text": bottone, "url": url}]]},
    }
    richiesta = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(corpo).encode(), headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(richiesta, timeout=30) as r:
            risposta = json.load(r)
    except urllib.error.HTTPError as e:
        risposta = json.loads(e.read() or b"{}")
    if not risposta.get("ok"):
        raise RuntimeError(f"Telegram ha rifiutato il messaggio: {risposta.get('description', risposta)}")


# ---------- programma ----------

def canale_da_sito(dati: dict) -> str:
    url = str((dati.get("social") or {}).get("telegram") or "").strip()
    m = re.match(r"^https?://(?:t\.me|telegram\.me)/(?:s/)?([A-Za-z0-9_]{5,})/?$", url)
    return f"@{m.group(1)}" if m else ""


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--stato", required=True, help="file JSON con i contenuti già inviati")
    p.add_argument("--prova", action="store_true", help="mostra i messaggi senza inviarli")
    p.add_argument("--adesso", help="finge che sia quest'ora (ISO), per le prove")
    a = p.parse_args()

    dati_sito = json.loads((RADICE / "src/data/sito.json").read_text(encoding="utf-8"))
    nome_guide = (dati_sito.get("guide") or {}).get("nome", "Guide")
    sito = os.environ.get("SITE_URL") or SITO_PREDEFINITO
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip() or canale_da_sito(dati_sito)
    if not a.prova and (not token or not chat):
        manca = "il secret TELEGRAM_BOT_TOKEN" if not token else "l'indirizzo del canale (sito.json → social.telegram)"
        print(f"::notice::Telegram non ancora configurato: manca {manca}. Non invio nulla.")
        return 0

    file_stato = Path(a.stato)
    stato = json.loads(file_stato.read_text(encoding="utf-8")) if file_stato.exists() else {}
    inviati: dict = stato.get("inviati", {})
    adesso = data_di(a.adesso) if a.adesso else datetime.now(timezone.utc)

    tutti = [c for c in contenuti() if c["chiave"] not in inviati and adesso - c["data"] <= FINESTRA]
    # Contenuti in uscita a breve: aspetta e inviali puntuali.
    in_arrivo = [c["data"] for c in tutti if c["data"] > adesso]
    if in_arrivo and not a.prova and min(in_arrivo) - adesso <= ATTESA_MASSIMA:
        attesa = (min(in_arrivo) - adesso).total_seconds() + 20
        print(f"Aspetto {round(attesa / 60)} minuti: alle {min(in_arrivo).astimezone(ROMA):%H:%M} esce un contenuto.")
        time.sleep(attesa)
        adesso = datetime.now(timezone.utc)
    pronti = sorted((c for c in tutti if c["data"] <= adesso), key=lambda c: c["data"])

    # Raggruppa: un messaggio per il caffè (con le brevi dello stesso giorno), uno per le brevi sole, uno per guida.
    messaggi = []  # (contenuti coperti, testo, url, bottone)
    caffe = [c for c in pronti if c["tipo"] in ("riepilogo", "settimanale")]
    brevi = [c for c in pronti if c["tipo"] == "breve"]
    for c in caffe:
        giorno = c["data"].astimezone(ROMA).date()
        sue = [b for b in brevi if b["data"].astimezone(ROMA).date() == giorno]
        brevi = [b for b in brevi if b not in sue]
        testo, bottone = messaggio_caffe(sito, c, sue)
        messaggi.append(([c] + sue, testo, link(sito, c), bottone))
    if brevi:
        testo, bottone = messaggio_brevi(sito, brevi)
        url = link(sito, brevi[0]) if len(brevi) == 1 else sito.rstrip("/") + "/articoli/"
        messaggi.append((brevi, testo, url, bottone))
    guide = [c for c in pronti if c["tipo"] == "guida"]
    if len(guide) > 2:  # tante guide insieme (es. un lotto): un solo messaggio con l'elenco
        testo, bottone = messaggio_guide(sito, guide, nome_guide)
        messaggi.append((guide, testo, sito.rstrip("/") + "/guide/", bottone))
    else:
        for g in guide:
            testo, bottone = messaggio_guida(sito, g, nome_guide)
            messaggi.append(([g], testo, link(sito, g), bottone))

    if not messaggi:
        print("Niente di nuovo da inviare.")
        return 0

    errori = 0
    for coperti, testo, url, bottone in messaggi:
        if a.prova:
            print(f"----- {url} [{bottone}]\n{testo}\n")
            continue
        if not all(e_online(link(sito, c)) for c in coperti):
            print(f"::warning::{url} non è ancora online: riprovo al prossimo giro.")
            continue
        try:
            invia(token, chat, testo, url, bottone)
        except Exception as e:  # noqa: BLE001
            print(f"::error::{e}")
            errori += 1
            continue
        for c in coperti:
            inviati[c["chiave"]] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        print(f"Inviato: {url}")
        time.sleep(3)

    if not a.prova:
        # Tiene solo gli ultimi 60 giorni.
        limite = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        stato["inviati"] = {k: v for k, v in sorted(inviati.items()) if v >= limite}
        file_stato.parent.mkdir(parents=True, exist_ok=True)
        file_stato.write_text(json.dumps(stato, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 1 if errori else 0


if __name__ == "__main__":
    sys.exit(main())
