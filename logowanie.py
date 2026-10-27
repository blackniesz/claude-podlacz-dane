"""Logowanie OAuth do Google (GA4, Search Console, Tag Manager, opcjonalnie Google Ads) i zapis tokenu w ~/.secrets.

Użytkownik klika link, loguje się swoim kontem Google i klika „Zezwól”. Skrypt łapie odpowiedź na loopbacku
(http://localhost:<port>), wymienia kod na refresh token i dopisuje go do ~/.secrets. Wartości kluczy nigdy nie wypisuje.

Klient OAuth (typ „Aplikacja komputerowa”) bierze z pliku JSON pobranego z Google Cloud (--client-json), a gdy go nie ma,
z ~/.secrets (<PREFIX>_CLIENT_ID / <PREFIX>_CLIENT_SECRET). Po pierwszym użyciu JSON-a zapisuje klienta w ~/.secrets,
więc plik można potem skasować.

Użycie:
  python logowanie.py --link link.txt --client-json ~/Downloads/client_secret_xxx.json
  python logowanie.py --link link.txt --ads                # dorzuca zakres Google Ads
  python logowanie.py --link link.txt --klient MOJ_KLIENT --token DANE_REFRESH_TOKEN
"""
import argparse
import http.server
import json
import os
import sys
import urllib.parse

import requests

sys.stdout.reconfigure(encoding="utf-8")  # konsola Windows domyślnie cp1250

ZAKRESY = [
    "https://www.googleapis.com/auth/analytics.readonly",    # GA4: raporty, lista property, zdarzenia kluczowe
    "https://www.googleapis.com/auth/webmasters.readonly",   # Search Console
    "https://www.googleapis.com/auth/tagmanager.readonly",   # GTM: kontenery, tagi, wyzwalacze
]
ZAKRES_ADS = "https://www.googleapis.com/auth/adwords"     # Ads nie ma zakresu tylko do odczytu
SECRETS = os.path.expanduser("~/.secrets")

p = argparse.ArgumentParser()
p.add_argument("--link", required=True, help="plik, do którego trafi link do zgody")
p.add_argument("--client-json", help="plik JSON klienta OAuth pobrany z Google Cloud")
p.add_argument("--klient", default="DANE_OAUTH", help="prefiks nazw klienta w ~/.secrets")
p.add_argument("--token", default="DANE_REFRESH_TOKEN", help="nazwa, pod którą zapisać refresh token")
p.add_argument("--ads", action="store_true", help="dodaj zakres Google Ads")
a = p.parse_args()


def sekrety():
    s = {}
    if os.path.exists(SECRETS):
        for line in open(SECRETS, encoding="utf-8-sig"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                s[k.strip()] = v.strip()
    return s


def zapisz(pary):
    # zapis w miejscu (tryb "w" na istniejącym pliku), żeby nie zmienić uprawnień NTFS pliku z sekretami
    linie = open(SECRETS, encoding="utf-8-sig").read().splitlines() if os.path.exists(SECRETS) else []
    linie = [l for l in linie if l.split("=", 1)[0].strip() not in pary]
    linie += [f"{k}={v}" for k, v in pary.items()]
    with open(SECRETS, "w", encoding="utf-8") as f:
        f.write("\n".join(linie) + "\n")


S = sekrety()
if a.client_json:
    dane = json.load(open(os.path.expanduser(a.client_json), encoding="utf-8"))
    if "installed" not in dane:
        sys.exit("To nie jest klient typu „Aplikacja komputerowa” (brak klucza 'installed' w JSON). Utwórz nowy klient tego typu.")
    cid, csec = dane["installed"]["client_id"], dane["installed"]["client_secret"]
    zapisz({f"{a.klient}_CLIENT_ID": cid, f"{a.klient}_CLIENT_SECRET": csec})
else:
    cid, csec = S.get(f"{a.klient}_CLIENT_ID"), S.get(f"{a.klient}_CLIENT_SECRET")
    if not cid or not csec:
        sys.exit(f"Brak klienta OAuth: podaj --client-json albo dopisz {a.klient}_CLIENT_ID/_CLIENT_SECRET do ~/.secrets.")

wynik = {}


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if "code" in q or "error" in q:
            wynik.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            msg = "Gotowe, możesz zamknąć tę kartę i wrócić do Claude Code." if "code" in q else "Odmowa lub błąd: " + q.get("error", ["?"])[0]
            self.wfile.write(f"<p style='font:18px sans-serif'>{msg}</p>".encode())
        else:
            self.send_response(204)
            self.end_headers()

    def log_message(self, *args):
        pass


srv = http.server.HTTPServer(("localhost", 0), H)
redirect = f"http://localhost:{srv.server_address[1]}"
zakresy = ZAKRESY + ([ZAKRES_ADS] if a.ads else [])
url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
    "client_id": cid, "redirect_uri": redirect, "response_type": "code", "scope": " ".join(zakresy),
    "access_type": "offline", "prompt": "consent select_account", "include_granted_scopes": "true"})
open(a.link, "w", encoding="utf-8").write(url)
print("Link zapisany, czekam na zgodę (do 15 minut)…", flush=True)
srv.timeout = 900
srv.handle_timeout = lambda: wynik.setdefault("timeout", "1")
while not wynik:
    srv.handle_request()
if "timeout" in wynik:
    sys.exit("Nikt nie kliknął zgody w 15 minut. Odpal skrypt jeszcze raz.")
if "error" in wynik:
    sys.exit("Błąd zgody: " + wynik["error"])

tok = requests.post("https://oauth2.googleapis.com/token", data={
    "code": wynik["code"], "client_id": cid, "client_secret": csec,
    "redirect_uri": redirect, "grant_type": "authorization_code"}, timeout=30).json()
if "refresh_token" not in tok:
    sys.exit("Brak refresh_token w odpowiedzi: " + str({k: v for k, v in tok.items() if "token" not in k}))
zapisz({a.token: tok["refresh_token"]})
dostane = tok.get("scope", "").split()
brak = [z.rsplit("/", 1)[-1] for z in zakresy if z not in dostane]
print(f"Zapisano {a.token} w ~/.secrets.")
if brak:
    print("UWAGA, nie odhaczono zakresów:", ", ".join(brak), "— przy zgodzie trzeba zaznaczyć wszystkie pola.")
