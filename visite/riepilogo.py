#!/usr/bin/env python3
"""Riepilogo delle visite di Caffè Corretto, mandato in privato su Telegram.

Gira con GitHub Actions (.github/workflows/visite.yml) ogni mattina alle 08:00 ora di Roma:
- ogni giorno: le visite di ieri, confrontate con il giorno prima e con la media della settimana;
- il lunedì in più: la settimana appena finita (lunedì-domenica), il mese in corso e il confronto
  con le tappe del "Piano 100k visite" (visualizzazioni al mese, iscritti Telegram, guide).

I numeri vengono da Cloudflare Web Analytics (solo browser veri: il contatore è uno script nella
pagina, quindi i robot che non eseguono JavaScript non vengono contati).

Il destinatario: chi scrive al bot un messaggio con la parola "visite". La prima volta il programma
lo trova tra i messaggi ricevuti dal bot e ricorda la chat, cifrata, in `visite/stato.json` (branch `dati`).

Variabili d'ambiente:
  CLOUDFLARE_API_TOKEN   chiave Cloudflare di sola lettura (permesso Account Analytics: Read)
  CLOUDFLARE_ACCOUNT_ID  facoltativa: se manca si usa l'unico account che la chiave vede
  TELEGRAM_BOT_TOKEN     il bot del canale (lo stesso del workflow Telegram)

Uso:
  python visite/riepilogo.py --stato ../dati/visite/stato.json            # invia se è l'ora
  python visite/riepilogo.py --stato /tmp/x.json --prova --tipo entrambi  # mostra senza inviare
Usa solo la libreria standard di Python.
"""
from __future__ import annotations

import argparse
import calendar
import hashlib
import html
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

RADICE = Path(__file__).resolve().parent.parent
ROMA = ZoneInfo("Europe/Rome")
DOMINIO = "caffecorrettofinanza.com"
ORA_INVIO = 8  # ore 08:00 di Roma
PAROLA_CHIAVE = "visite"
GIORNI = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
        "settembre", "ottobre", "novembre", "dicembre"]

# Tappe del "Piano 100k visite" (https://claude.ai/artifact/65VrWZgRPWdpFDAK9Qm7av):
# visualizzazioni al mese (obiettivo, probabile), iscritti Telegram, guide totali.
TAPPE = {
    "2026-12": (1500, 1000, 30, 40),
    "2027-01": (3000, 2000, 80, 53),
    "2027-02": (5000, 3500, 150, 66),
    "2027-03": (8000, 5000, 250, 79),
    "2027-04": (12000, 7000, 400, 92),
    "2027-05": (18000, 10000, 600, 105),
    "2027-06": (25000, 13000, 800, 118),
    "2027-07": (32000, 16000, 1000, 131),
    "2027-08": (38000, 17000, 1200, 144),
    "2027-09": (55000, 22000, 1600, 157),
    "2027-10": (75000, 28000, 2000, 170),
    "2027-11": (100000, 35000, 2500, 183),
}


def n(v: float) -> str:
    """Numero all'italiana: 12.345"""
    return f"{round(v):,}".replace(",", ".")


def variazione(oggi: float, prima: float) -> str:
    if not prima:
        return ""
    p = (oggi - prima) / prima * 100
    if abs(p) < 1:
        return " (uguale)"
    freccia = "▲" if p > 0 else "▼"
    return f" ({freccia} {abs(p):.0f}%)"


def titoli() -> dict[str, str]:
    """Percorso della pagina → titolo, letto dagli articoli e dalle guide del sito."""
    out = {}
    for cartella in ("articoli", "guide"):
        for f in (RADICE / "src/content" / cartella).glob("*.md*"):
            for riga in f.read_text(encoding="utf-8").splitlines()[1:15]:
                if riga.startswith("titolo:"):
                    t = riga.split(":", 1)[1].strip()
                    try:
                        t = json.loads(t) if t.startswith('"') else t.strip("'")
                    except ValueError:
                        t = t.strip('"')
                    out[f"/{cartella}/{f.stem}"] = ("Guida: " if cartella == "guide" else "") + t
                    break
    return out


TITOLI: dict[str, str] = {}
FISSE = {"": "Home", "/guide": "Elenco guide", "/articoli": "Elenco articoli", "/glossario": "Glossario",
         "/chi-siamo": "Chi siamo", "/contatti": "Contatti", "/privacy": "Privacy"}


def nome_pagina(percorso: str) -> str:
    percorso = (percorso or "/").split("?")[0].split("#")[0].rstrip("/")
    if percorso in FISSE:
        return FISSE[percorso]
    if not TITOLI:
        TITOLI.update(titoli())
    if percorso in TITOLI:
        return TITOLI[percorso]
    pezzi = percorso.strip("/").split("/")
    ultimo = pezzi[-1].replace("-", " ")
    prefisso = "Guida: " if pezzi[0] == "guide" and len(pezzi) > 1 else ""
    return prefisso + (ultimo[:1].upper() + ultimo[1:])


def nome_fonte(host: str) -> str:
    host = (host or "").lower().removeprefix("www.")
    if not host or DOMINIO in host or host.endswith("pages.dev"):
        return "Diretto o link salvato"
    for chiave, nome in [("google", "Google"), ("bing", "Bing"), ("duckduckgo", "DuckDuckGo"),
                         ("t.me", "Telegram"), ("telegram", "Telegram"), ("facebook", "Facebook"),
                         ("instagram", "Instagram"), ("linkedin", "LinkedIn"), ("reddit", "Reddit"),
                         ("x.com", "X"), ("t.co", "X"), ("whatsapp", "WhatsApp"), ("yahoo", "Yahoo"),
                         ("ecosia", "Ecosia"), ("chatgpt", "ChatGPT"), ("perplexity", "Perplexity")]:
        if chiave in host:
            return nome
    return host


def nome_dispositivo(d: str) -> str:
    return {"desktop": "computer", "mobile": "telefono", "tablet": "tablet"}.get((d or "").lower(), d or "altro")


# ---------- Cloudflare ----------

def chiama(url: str, token: str, corpo: dict | None = None) -> dict:
    dati = json.dumps(corpo).encode() if corpo is not None else None
    richiesta = urllib.request.Request(url, data=dati, headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json",
        "User-Agent": "caffe-corretto-visite"})
    try:
        with urllib.request.urlopen(richiesta, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Cloudflare ha risposto {e.code}: {e.read().decode(errors='replace')[:500]}")


def trova_account(token: str) -> str:
    risposta = chiama("https://api.cloudflare.com/client/v4/accounts?per_page=50", token)
    account = risposta.get("result") or []
    if not account:
        raise SystemExit("La chiave Cloudflare non vede nessun account: serve CLOUDFLARE_ACCOUNT_ID.")
    return account[0]["id"]


GRUPPI = {
    "totale": "",
    "giorni": "datetimeHour",
    "pagine": "requestPath",
    "fonti": "refererHost",
    "paesi": "countryName",
    "dispositivi": "deviceType",
}


def interroga(token: str, account: str, inizio: datetime, fine: datetime) -> dict:
    """Pagine viste e visite tra inizio e fine (fine esclusa), divise in vari modi."""
    pezzi = []
    for alias, dimensione in GRUPPI.items():
        dim = f" dimensions {{ {dimensione} }}" if dimensione else ""
        ordine = "orderBy: [count_DESC], " if dimensione and dimensione != "datetimeHour" else ""
        limite = 1 if not dimensione else (1000 if dimensione == "datetimeHour" else 40)
        pezzi.append(f"{alias}: rumPageloadEventsAdaptiveGroups(limit: {limite}, {ordine}filter: $f) "
                     f"{{ count sum {{ visits }}{dim} }}")
    query = ("query ($acc: String!, $f: AccountRumPageloadEventsAdaptiveGroupsFilter_InputObject) "
             "{ viewer { accounts(filter: {accountTag: $acc}) { " + " ".join(pezzi) + " } } }")
    filtro = {"datetime_geq": inizio.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "datetime_lt": fine.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "requestHost": DOMINIO}
    risposta = chiama("https://api.cloudflare.com/client/v4/graphql", token,
                      {"query": query, "variables": {"acc": account, "f": filtro}})
    if risposta.get("errors"):
        raise SystemExit(f"Errore nella lettura delle visite: {json.dumps(risposta['errors'])[:800]}")
    conti = risposta["data"]["viewer"]["accounts"]
    if not conti:
        raise SystemExit("Account Cloudflare non trovato o non leggibile con questa chiave.")
    grezzo = conti[0]
    risultato = {}
    for alias, dimensione in GRUPPI.items():
        righe = [{"chiave": (r.get("dimensions") or {}).get(dimensione, ""),
                  "viste": r["count"], "visite": r["sum"]["visits"]} for r in grezzo[alias]]
        risultato[alias] = righe
    # Le ore (in UTC) diventano giorni di calendario italiani.
    giorni: dict[str, dict] = {}
    for r in risultato["giorni"]:
        g = datetime.fromisoformat(r["chiave"].replace("Z", "+00:00")).astimezone(ROMA).date().isoformat()
        s = giorni.setdefault(g, {"chiave": g, "viste": 0, "visite": 0})
        s["viste"] += r["viste"]
        s["visite"] += r["visite"]
    risultato["giorni"] = list(giorni.values())
    tot = risultato["totale"][0] if risultato["totale"] else {"viste": 0, "visite": 0}
    risultato["viste"], risultato["visite"] = tot["viste"], tot["visite"]
    return risultato


def raggruppa(righe: list[dict], nome) -> list[tuple[str, int, int]]:
    somme: dict[str, list[int]] = {}
    for r in righe:
        k = nome(r["chiave"])
        s = somme.setdefault(k, [0, 0])
        s[0] += r["viste"]
        s[1] += r["visite"]
    return sorted(((k, v[0], v[1]) for k, v in somme.items()), key=lambda x: -x[1])


def mezzanotte(g: date) -> datetime:
    return datetime.combine(g, time(0), ROMA)


# ---------- Telegram ----------

def telegram(token: str, metodo: str, parametri: dict) -> dict:
    richiesta = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{metodo}",
        data=json.dumps(parametri).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(richiesta, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"ok": False, "description": e.read().decode(errors="replace")[:300]}


def trova_chat(token: str) -> str | None:
    risposta = telegram(token, "getUpdates", {"allowed_updates": ["message"]})
    for agg in reversed(risposta.get("result") or []):
        m = agg.get("message") or {}
        if m.get("chat", {}).get("type") == "private" and PAROLA_CHIAVE in (m.get("text") or "").lower():
            return str(m["chat"]["id"])
    return None


def nascondi(chat: str, segreto: str) -> str:
    """Il repository è pubblico: la chat si salva cifrata con una chiave ricavata dal token del bot."""
    dati = chat.encode()
    chiave = hashlib.sha256(("visite:" + segreto).encode()).digest()
    return bytes(b ^ chiave[i % len(chiave)] for i, b in enumerate(dati)).hex()


def scopri(cifrata: str, segreto: str) -> str:
    dati = bytes.fromhex(cifrata)
    chiave = hashlib.sha256(("visite:" + segreto).encode()).digest()
    return bytes(b ^ chiave[i % len(chiave)] for i, b in enumerate(dati)).decode()


def iscritti_canale(token: str) -> int | None:
    try:
        sito = json.loads((RADICE / "src/data/sito.json").read_text())
        nome = "@" + sito["social"]["telegram"].rstrip("/").rsplit("/", 1)[-1]
    except (OSError, KeyError, ValueError):
        return None
    r = telegram(token, "getChatMemberCount", {"chat_id": nome})
    return r.get("result") if r.get("ok") else None


# ---------- i messaggi ----------

def elenco(righe, quante=5, con_visite=False) -> list[str]:
    out = []
    for nome, viste, visite in righe[:quante]:
        valore = f"{n(visite)} visite" if con_visite else n(viste)
        out.append(f"• {html.escape(nome)}: {valore}")
    return out


def messaggio_giorno(token: str, account: str, ieri: date) -> str:
    dati = interroga(token, account, mezzanotte(ieri - timedelta(days=7)), mezzanotte(ieri + timedelta(days=1)))
    per_giorno = {r["chiave"]: r for r in dati["giorni"]}
    oggi = per_giorno.get(ieri.isoformat(), {"viste": 0, "visite": 0})
    prima = per_giorno.get((ieri - timedelta(days=1)).isoformat(), {"viste": 0, "visite": 0})
    settimana = [per_giorno.get((ieri - timedelta(days=i)).isoformat(), {"viste": 0})["viste"] for i in range(1, 8)]
    media = sum(settimana) / 7
    solo_ieri = interroga(token, account, mezzanotte(ieri), mezzanotte(ieri + timedelta(days=1)))

    righe = [f"☕ <b>Visite di ieri, {GIORNI[ieri.weekday()]} {ieri.day} {MESI[ieri.month - 1]}</b>", "",
             f"👀 Pagine lette: <b>{n(oggi['viste'])}</b>{variazione(oggi['viste'], prima['viste'])}",
             f"🚪 Visite (persone arrivate sul sito): <b>{n(oggi['visite'])}</b>{variazione(oggi['visite'], prima['visite'])}",
             f"📊 Media dei 7 giorni prima: {n(media)} pagine al giorno"]
    if oggi["viste"] == 0:
        righe += ["", "Nessuna visita registrata ieri."]
        return "\n".join(righe)
    righe += ["", "<b>Le più lette</b>"] + elenco(raggruppa(solo_ieri["pagine"], nome_pagina))
    righe += ["", "<b>Da dove arrivano</b>"] + elenco(raggruppa(solo_ieri["fonti"], nome_fonte), 4, True)
    paesi = raggruppa(solo_ieri["paesi"], lambda x: x or "sconosciuto")[:3]
    disp = raggruppa(solo_ieri["dispositivi"], nome_dispositivo)
    tot = sum(d[1] for d in disp) or 1
    righe += ["", "🌍 " + ", ".join(f"{html.escape(p)} {n(v)}" for p, v, _ in paesi),
              "📱 " + ", ".join(f"{d} {round(v / tot * 100)}%" for d, v, _ in disp[:3])]
    return "\n".join(righe)


def messaggio_settimana(token: str, account: str, bot: str | None, lunedi: date) -> str:
    inizio, fine = lunedi - timedelta(days=7), lunedi  # la settimana appena finita, lunedì-domenica
    sett = interroga(token, account, mezzanotte(inizio), mezzanotte(fine))
    prec = interroga(token, account, mezzanotte(inizio - timedelta(days=7)), mezzanotte(inizio))
    domenica = fine - timedelta(days=1)

    righe = [f"🗓 <b>La settimana dal {inizio.day} {MESI[inizio.month - 1]} al {domenica.day} {MESI[domenica.month - 1]}</b>", "",
             f"👀 Pagine lette: <b>{n(sett['viste'])}</b>{variazione(sett['viste'], prec['viste'])}",
             f"🚪 Visite: <b>{n(sett['visite'])}</b>{variazione(sett['visite'], prec['visite'])}"]
    giorni = {r["chiave"]: r["viste"] for r in sett["giorni"]}
    if giorni:
        migliore = max(giorni, key=giorni.get)
        g = date.fromisoformat(migliore)
        righe.append(f"🏆 Giorno migliore: {GIORNI[g.weekday()]} {g.day} ({n(giorni[migliore])} pagine)")
    righe += ["", "<b>Le 5 più lette della settimana</b>"] + elenco(raggruppa(sett["pagine"], nome_pagina))
    righe += ["", "<b>Da dove arrivano</b>"] + elenco(raggruppa(sett["fonti"], nome_fonte), 5, True)

    # Il mese di domenica (quello a cui appartiene la settimana appena finita), fino a ieri compreso.
    primo = domenica.replace(day=1)
    mese = interroga(token, account, mezzanotte(primo), mezzanotte(fine))
    giorni_mese = calendar.monthrange(primo.year, primo.month)[1]
    passati = (fine - primo).days
    stima = mese["viste"] / passati * giorni_mese if passati else 0
    chiave = primo.strftime("%Y-%m")
    righe += ["", f"<b>{MESI[primo.month - 1].capitalize()} finora</b> ({passati} giorni su {giorni_mese})",
              f"Pagine lette: {n(mese['viste'])}. A questo ritmo il mese chiude a circa <b>{n(stima)}</b>."]
    tappa = TAPPE.get(chiave)
    if tappa:
        obiettivo, probabile, tg, guide = tappa
        if stima >= obiettivo:
            esito = "✅ sopra la tappa del piano"
        elif stima >= probabile:
            esito = "🟡 sotto l'obiettivo ma in linea con lo scenario probabile"
        else:
            esito = "🔴 sotto anche lo scenario probabile"
        righe.append(f"Tappa del piano: {n(obiettivo)} (probabile {n(probabile)}): {esito}.")
    else:
        prossima = min((k for k in TAPPE if k > chiave), default=None)
        if prossima:
            a, m = prossima.split("-")
            righe.append(f"Prima tappa del piano: {MESI[int(m) - 1]} {a}, {n(TAPPE[prossima][0])} pagine nel mese.")
            tappa = TAPPE[prossima]
    if tappa:
        _, _, tg, guide = tappa
        extra = []
        iscritti = iscritti_canale(bot) if bot else None
        if iscritti is not None:
            extra.append(f"Telegram {n(iscritti)} iscritti (tappa {n(tg)})")
        try:
            quante = len([p for p in (RADICE / "src/content/guide").iterdir() if p.suffix in (".md", ".mdx")])
            extra.append(f"guide online {quante} (tappa {guide})")
        except OSError:
            pass
        if extra:
            righe.append("📌 " + ", ".join(extra) + ".")
    return "\n".join(righe)


# ---------- main ----------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stato", required=True, help="file JSON dove ricordare chat e invii")
    ap.add_argument("--prova", action="store_true", help="mostra i messaggi senza inviarli")
    ap.add_argument("--tipo", choices=["auto", "giorno", "settimana", "entrambi"], default="auto")
    ap.add_argument("--adesso", help="data e ora finta (ISO), per le prove")
    a = ap.parse_args()

    adesso = datetime.fromisoformat(a.adesso).astimezone(ROMA) if a.adesso else datetime.now(ROMA)
    oggi = adesso.date()
    cf = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    bot = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not cf:
        print("Manca CLOUDFLARE_API_TOKEN: niente riepilogo (nessun errore).")
        return 0

    percorso = Path(a.stato)
    stato = json.loads(percorso.read_text()) if percorso.exists() else {}
    stato.setdefault("inviati", [])

    if a.tipo == "auto":
        if adesso.hour < ORA_INVIO:
            print(f"Sono le {adesso:%H:%M} a Roma: il riepilogo parte dalle {ORA_INVIO:02d}:00.")
            return 0
        tipi = ["giorno"] + (["settimana"] if oggi.weekday() == 0 else [])
    else:
        tipi = ["giorno", "settimana"] if a.tipo == "entrambi" else [a.tipo]
    lunedi = oggi - timedelta(days=oggi.weekday())
    etichette = {"giorno": f"giorno:{oggi - timedelta(days=1)}", "settimana": f"settimana:{lunedi}"}
    if not a.prova and a.tipo == "auto":
        tipi = [t for t in tipi if etichette[t] not in stato["inviati"]]
        if not tipi:
            print("Riepilogo di oggi già inviato.")
            return 0

    chat = os.environ.get("VISITE_CHAT_ID", "").strip()
    if not chat and bot and stato.get("chat"):
        chat = scopri(stato["chat"], bot)
    if not chat and bot and not a.prova:
        chat = trova_chat(bot)
        if chat:
            stato["chat"] = nascondi(chat, bot)
            print("Trovata la chat a cui mandare il riepilogo.")
    if not chat and not a.prova:
        print(f'Nessun destinatario: scrivi al bot un messaggio con la parola "{PAROLA_CHIAVE}".')
        return 0

    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip() or trova_account(cf)
    for tipo in tipi:
        testo = (messaggio_giorno(cf, account, oggi - timedelta(days=1)) if tipo == "giorno"
                 else messaggio_settimana(cf, account, bot, lunedi))
        if a.prova:
            print(f"----- {tipo} -----\n{testo}\n")
            continue
        r = telegram(bot, "sendMessage", {"chat_id": chat, "text": testo, "parse_mode": "HTML",
                                          "disable_web_page_preview": True})
        if not r.get("ok"):
            raise SystemExit(f"Telegram non ha accettato il messaggio: {r.get('description')}")
        if a.tipo == "auto":
            stato["inviati"] = (stato["inviati"] + [etichette[tipo]])[-60:]
        print(f"Inviato il riepilogo: {tipo}.")

    percorso.parent.mkdir(parents=True, exist_ok=True)
    percorso.write_text(json.dumps(stato, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
