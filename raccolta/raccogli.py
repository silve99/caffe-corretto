#!/usr/bin/env python3
"""Raccolta notizie di Caffè Corretto.

Gira ogni 30 minuti su GitHub Actions. Scarica titoli e link da fonti gratuite
(RSS istituzionali e comunicati, GDELT) e alcuni dati di mercato (BCE, CoinGecko),
toglie i doppioni, raggruppa le notizie uguali, assegna un punteggio di rilevanza
e scrive tutto in una cartella di dati (il branch `dati` del repository).

Usa solo la libreria standard di Python.

Uso:  python raccolta/raccogli.py --out ../dati
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROMA = ZoneInfo("Europe/Rome")
QUI = Path(__file__).resolve().parent
UA = "CaffeCorrettoBot/0.1 (+https://caffe-corretto.pages.dev/come-lavoriamo/)"
FINESTRA_ORE = 26  # la selezione guarda le ultime 26 ore (copre 06:30 di ieri -> 06:00 di oggi)

# --------------------------------------------------------------------------- rete

def scarica(url: str, headers: dict | None = None, timeout: int = 25) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def scarica_json(url: str, headers: dict | None = None):
    return json.loads(scarica(url, headers).decode("utf-8"))

# --------------------------------------------------------------------------- testo

STOP = set("""
a ad al alla alle allo agli ai anche che chi con da dal dalla dei del della delle dello di e ed gli i il in la le lo
ma ne nei nel nella non o per piu più se si su sua suo sul sulla tra un una uno ecco come oggi dopo verso
the a an and or of to in on for at by with from as is are was were be its it this that into after over amid new
says say said will has have had than more about up down
""".split())


def normalizza(testo: str) -> str:
    t = unicodedata.normalize("NFKD", testo or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9%$€ ]+", " ", t)


def parole(titolo: str) -> set[str]:
    return {p for p in normalizza(titolo).split() if len(p) > 2 and p not in STOP}


def url_canonico(url: str) -> str:
    p = urllib.parse.urlsplit(url.strip())
    q = [(k, v) for k, v in urllib.parse.parse_qsl(p.query) if not k.lower().startswith(("utm_", "fbclid", "gclid"))]
    return urllib.parse.urlunsplit((p.scheme.lower(), p.netloc.lower().removeprefix("www."), p.path.rstrip("/"), urllib.parse.urlencode(q), ""))


def dominio(url: str) -> str:
    return urllib.parse.urlsplit(url).netloc.lower().removeprefix("www.")


def id_notizia(url: str) -> str:
    return hashlib.sha1(url_canonico(url).encode()).hexdigest()[:16]

# --------------------------------------------------------------------------- fonti

def leggi_rss(fonte: dict) -> list[dict]:
    radice = ET.fromstring(scarica(fonte["url"]))
    ns_atom = "{http://www.w3.org/2005/Atom}"
    voci = radice.findall(".//item") or radice.findall(f".//{ns_atom}entry")
    out = []
    for v in voci:
        titolo = (v.findtext("title") or v.findtext(f"{ns_atom}title") or "").strip()
        link = (v.findtext("link") or "").strip()
        if not link:
            el = v.find(f"{ns_atom}link")
            link = el.get("href", "") if el is not None else ""
        data_txt = v.findtext("pubDate") or v.findtext(f"{ns_atom}updated") or v.findtext(f"{ns_atom}published") or ""
        try:
            data = parsedate_to_datetime(data_txt) if "," in data_txt else datetime.fromisoformat(data_txt.replace("Z", "+00:00"))
            if data.tzinfo is None:
                data = data.replace(tzinfo=timezone.utc)
        except Exception:
            data = None
        if titolo and link:
            out.append({
                "titolo": titolo,
                "url": link,
                "pubblicato": data.astimezone(timezone.utc).isoformat() if data else None,
                "fonte": fonte["id"],
                "fonte_nome": fonte["nome"],
                "ufficiale": bool(fonte.get("ufficiale")),
                "istituzionale": bool(fonte.get("istituzionale")),
                "solo_verifica": bool(fonte.get("solo_verifica")),
                "lingua": fonte.get("lingua"),
                "categoria": fonte.get("categoria"),
            })
    return out


def leggi_gdelt(q: dict) -> list[dict]:
    parametri = urllib.parse.urlencode({
        "query": q["query"], "mode": "artlist", "format": "json",
        "maxrecords": "75", "timespan": "2h", "sort": "datedesc",
    })
    url = "https://api.gdeltproject.org/api/v2/doc/doc?" + parametri
    for tentativo in range(3):
        try:
            dati = scarica_json(url)
            break
        except urllib.error.HTTPError as e:
            if e.code != 429 or tentativo == 2:
                raise
            time.sleep(20 * (tentativo + 1))  # GDELT limita le richieste: aspetta e riprova
    out = []
    for a in dati.get("articles", []):
        try:
            data = datetime.strptime(a["seendate"], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).isoformat()
        except Exception:
            data = None
        out.append({
            "titolo": (a.get("title") or "").strip(),
            "url": a["url"],
            "pubblicato": data,
            "fonte": "gdelt:" + a.get("domain", dominio(a["url"])),
            "fonte_nome": a.get("domain", dominio(a["url"])),
            "ufficiale": False,
            "istituzionale": False,
            "solo_verifica": False,
            "lingua": {"English": "en", "Italian": "it"}.get(a.get("language", ""), a.get("language")),
            "categoria": q["categoria"],
            "via": "GDELT",
        })
    return out


def mercati(config: dict) -> dict:
    """Dati numerici: cambi di riferimento BCE e prezzi cripto CoinGecko."""
    risultato: dict = {"aggiornato": datetime.now(timezone.utc).isoformat(), "errori": []}

    # Cambi BCE (fonte: BCE, riutilizzo consentito citando la fonte)
    try:
        valute = "+".join(config["valute_bce"])
        d = scarica_json(f"https://data-api.ecb.europa.eu/service/data/EXR/D.{valute}.EUR.SP00.A?lastNObservations=2&format=jsondata",
                         {"Accept": "application/json"})
        dim_serie = d["structure"]["dimensions"]["series"]
        dim_valuta = next(i for i, x in enumerate(dim_serie) if x["id"] == "CURRENCY")
        date_oss = [v["id"] for v in d["structure"]["dimensions"]["observation"][0]["values"]]
        cambi = {}
        for chiave, serie in d["dataSets"][0]["series"].items():
            valuta = dim_serie[dim_valuta]["values"][int(chiave.split(":")[dim_valuta])]["id"]
            oss = {date_oss[int(k)]: v[0] for k, v in serie["observations"].items() if v and v[0] is not None}
            giorni = sorted(oss)
            ultimo = oss[giorni[-1]]
            prec = oss[giorni[-2]] if len(giorni) > 1 else None
            cambi[f"EUR/{valuta}"] = {
                "valore": ultimo, "data": giorni[-1],
                "variazione_pct": round((ultimo / prec - 1) * 100, 2) if prec else None,
            }
        risultato["cambi_bce"] = {"fonte": "Banca Centrale Europea", "dati": cambi}
    except Exception as e:  # noqa: BLE001
        risultato["errori"].append(f"bce: {e}")

    # CoinGecko (piano Demo: obbligo di citare "Powered by CoinGecko")
    chiave = os.environ.get("COINGECKO_API_KEY", "").strip()
    if not chiave:
        risultato["errori"].append("coingecko: manca il secret COINGECKO_API_KEY")
    else:
        h = {"x-cg-demo-api-key": chiave, "Accept": "application/json"}
        try:
            ids = ",".join(config["crypto_ids"])
            lista = scarica_json(f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=eur&ids={ids}&price_change_percentage=24h", h)
            risultato["cripto"] = {
                "fonte": "Powered by CoinGecko",
                "dati": {c["symbol"].upper(): {
                    "nome": c["name"], "prezzo_eur": c["current_price"],
                    "variazione_24h_pct": round(c.get("price_change_percentage_24h") or 0, 2),
                    "capitalizzazione_eur": c.get("market_cap"),
                } for c in lista},
            }
            g = scarica_json("https://api.coingecko.com/api/v3/global", h)["data"]
            risultato["cripto_globale"] = {
                "capitalizzazione_totale_eur": g["total_market_cap"].get("eur"),
                "variazione_24h_pct": round(g.get("market_cap_change_percentage_24h_usd") or 0, 2),
                "dominanza_btc_pct": round(g["market_cap_percentage"].get("btc", 0), 1),
            }
        except Exception as e:  # noqa: BLE001
            risultato["errori"].append(f"coingecko: {e}")
    return risultato

# --------------------------------------------------------------------------- punteggio

PESI = {
    # banche centrali e tassi
    "federal reserve": 5, "jerome powell": 4, "fed chair": 4, "fomc": 5, "bce": 5, "ecb": 5, "lagarde": 4,
    "tassi": 3, "rates": 3, "rate cut": 4, "rate hike": 4, "taglio dei tassi": 4,
    # macro
    "inflazione": 3, "inflation": 3, "cpi": 3, "pil": 3, "gdp": 3, "recession": 3, "recessione": 3,
    "disoccupazione": 2, "payrolls": 3, "jobs report": 3, "spread": 3, "btp": 3, "dazi": 3, "tariffs": 3,
    # mercati
    "wall street": 2, "s&p 500": 2, "nasdaq": 2, "piazza affari": 3, "ftse mib": 3, "borsa": 1,
    "record": 2, "crollo": 3, "crash": 3, "sell off": 3, "rally": 2,
    "utili": 2, "earnings": 2, "trimestrale": 2, "guidance": 2, "acquisizione": 2, "acquisition": 2, "merger": 2,
    "petrolio": 2, "oil": 1, "oro": 2, "gold": 1, "opec": 3,
    # cripto
    "bitcoin": 3, "ethereum": 2, "etf": 2, "stablecoin": 2, "sec": 2, "halving": 3,
    # grandi nomi
    "nvidia": 2, "apple": 2, "microsoft": 2, "tesla": 2, "amazon": 2, "alphabet": 2, "meta": 1,
    "eni": 2, "enel": 2, "intesa": 2, "unicredit": 2, "stellantis": 2, "ferrari": 2, "generali": 2,
}


def punteggio_parole(titoli: list[str]) -> int:
    testo = " " + " ".join(normalizza(t) for t in titoli) + " "
    return min(12, sum(p for k, p in PESI.items() if f" {normalizza(k).strip()} " in testo))


def raggruppa(notizie: list[dict], soglia: float = 0.5) -> list[dict]:
    """Unisce le notizie con titoli molto simili (stesso fatto raccontato da fonti diverse)."""
    gruppi: list[dict] = []
    for n in sorted(notizie, key=lambda x: x.get("pubblicato") or "", reverse=True):
        p = parole(n["titolo"])
        if len(p) < 3:
            continue
        migliore, sim_max = None, 0.0
        for g in gruppi:
            inter = len(p & g["_parole"])
            sim = inter / len(p | g["_parole"]) if inter else 0.0
            if sim > sim_max:
                migliore, sim_max = g, sim
        if migliore and sim_max >= soglia:
            migliore["notizie"].append(n)
            migliore["_parole"] |= p
        else:
            gruppi.append({"_parole": set(p), "notizie": [n]})
    return gruppi


def valuta(gruppo: dict, adesso: datetime) -> dict:
    notizie = gruppo["notizie"]
    domini = {dominio(n["url"]) for n in notizie}
    ufficiale = any(n["ufficiale"] for n in notizie)
    istituzionale = any(n.get("istituzionale") for n in notizie)
    italiano = any(n.get("lingua") == "it" for n in notizie)
    date = [datetime.fromisoformat(n["pubblicato"]) for n in notizie if n.get("pubblicato")]
    ultima = max(date) if date else adesso
    ore = max(0.0, (adesso - ultima).total_seconds() / 3600)
    p_parole = punteggio_parole([n["titolo"] for n in notizie])
    punti = (
        min(10, 2 * (len(domini) - 1))   # più fonti indipendenti = più importante
        + (6 if istituzionale else 0)       # banche centrali: sempre rilevanti
        + (1 if ufficiale and not istituzionale else 0)  # comunicato aziendale: verificato ma non per forza importante
        + p_parole
        + (2 if italiano else 0)
        - 0.2 * ore
    )
    rappresentante = next((n for n in notizie if n["ufficiale"]), None) or \
        next((n for n in notizie if not n["solo_verifica"]), notizie[0])
    categorie = sorted({n["categoria"] for n in notizie if n.get("categoria")})
    return {
        "id": id_notizia(rappresentante["url"]),
        "titolo": rappresentante["titolo"],
        "punteggio": round(punti, 1),
        "verificata": ufficiale or len(domini) >= 2,
        "ufficiale": ufficiale,
        "fonti_distinte": len(domini),
        "categorie": categorie,
        "ultima_ora": ultima.isoformat(),
        "link": [{"titolo": n["titolo"], "url": n["url"], "fonte": n["fonte_nome"],
                  "solo_verifica": n["solo_verifica"], "via": n.get("via")} for n in notizie[:12]],
    }

# --------------------------------------------------------------------------- file

def leggi(path: Path, default):
    try:
        return json.loads(path.read_text("utf-8"))
    except FileNotFoundError:
        return default


def scrivi(path: Path, dati) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(dati, ensure_ascii=False, indent=1), "utf-8")
    tmp.replace(path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="cartella dei dati (checkout del branch dati)")
    args = ap.parse_args()
    out = Path(args.out)
    config = json.loads((QUI / "fonti.json").read_text("utf-8"))
    adesso = datetime.now(timezone.utc)
    oggi = adesso.astimezone(ROMA).date()

    nuove: list[dict] = []
    stato: dict = {"eseguito": adesso.isoformat(), "fonti": {}}
    for f in config["rss"]:
        try:
            voci = leggi_rss(f)
            nuove += voci
            stato["fonti"][f["id"]] = {"ok": True, "voci": len(voci)}
        except Exception as e:  # noqa: BLE001
            stato["fonti"][f["id"]] = {"ok": False, "errore": str(e)[:200]}
    for q in config["gdelt"]:
        try:
            voci = leggi_gdelt(q)
            nuove += voci
            stato["fonti"][q["id"]] = {"ok": True, "voci": len(voci)}
        except Exception as e:  # noqa: BLE001
            stato["fonti"][q["id"]] = {"ok": False, "errore": str(e)[:200]}
        time.sleep(10)  # GDELT chiede al massimo una richiesta ogni 5 secondi (teniamo margine)

    # archivio del giorno (ora italiana), senza doppioni per URL
    file_oggi = out / "notizie" / f"{oggi.isoformat()}.json"
    archivio = {n["id"]: n for n in leggi(file_oggi, [])}
    nuovi = 0
    for n in nuove:
        n["id"] = id_notizia(n["url"])
        if n["id"] in archivio:
            continue
        n["raccolto"] = adesso.isoformat()
        if not n.get("pubblicato"):
            n["pubblicato"] = n["raccolto"]
        archivio[n["id"]] = n
        nuovi += 1
    scrivi(file_oggi, sorted(archivio.values(), key=lambda x: x["pubblicato"], reverse=True))
    stato["nuove_notizie"] = nuovi

    # selezione: gruppi delle ultime FINESTRA_ORE ore, ordinati per punteggio
    limite = adesso - timedelta(hours=FINESTRA_ORE)
    recenti: dict[str, dict] = {}
    for giorno in (oggi - timedelta(days=1), oggi):
        for n in leggi(out / "notizie" / f"{giorno.isoformat()}.json", []):
            if datetime.fromisoformat(n["pubblicato"]) >= limite:
                recenti[n["id"]] = n
    gruppi = [valuta(g, adesso) for g in raggruppa(list(recenti.values()))]
    # una notizia trovata solo su testate "solo_verifica" non può essere la base di un articolo
    gruppi = [g for g in gruppi if not all(l["solo_verifica"] for l in g["link"])]
    gruppi.sort(key=lambda g: g["punteggio"], reverse=True)
    scrivi(out / "selezione.json", {
        "aggiornato": adesso.isoformat(),
        "finestra_ore": FINESTRA_ORE,
        "notizie_considerate": len(recenti),
        "gruppi": gruppi[:60],
    })

    # dati di mercato
    m = mercati(config)
    scrivi(out / "mercati" / "ultimo.json", m)
    stato["errori_mercati"] = m["errori"]

    scrivi(out / "stato.json", stato)
    ok = sum(1 for s in stato["fonti"].values() if s["ok"])
    print(f"Fonti ok: {ok}/{len(stato['fonti'])} · nuove notizie: {nuovi} · gruppi: {len(gruppi)}")
    for k, s in stato["fonti"].items():
        print(f"  {'✓' if s['ok'] else '✗'} {k}: {s.get('voci', s.get('errore'))}")
    for e in m["errori"]:
        print(f"  ✗ mercati: {e}")
    if gruppi:
        print("Prime 5 notizie:")
        for g in gruppi[:5]:
            print(f"  {g['punteggio']:>5} {'V' if g['verificata'] else ' '} {g['titolo'][:100]}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
