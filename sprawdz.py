"""Sprawdza, do czego token z logowanie.py daje dostęp: property GA4, strony GSC, kontenery GTM, opcjonalnie Clarity i Ads.

Wypisuje same nazwy i identyfikatory, nigdy wartości kluczy. Każde źródło sprawdza osobno, więc błąd jednego nie blokuje reszty.
Użycie: python sprawdz.py [--klient DANE_OAUTH] [--token DANE_REFRESH_TOKEN]
"""
import argparse
import os
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8")  # konsola Windows domyślnie cp1250

p = argparse.ArgumentParser()
p.add_argument("--klient", default="DANE_OAUTH")
p.add_argument("--token", default="DANE_REFRESH_TOKEN")
a = p.parse_args()

S = {}
for line in open(os.path.expanduser("~/.secrets"), encoding="utf-8-sig"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        S[k.strip()] = v.strip()

odp = requests.post("https://oauth2.googleapis.com/token", data={
    "client_id": S[f"{a.klient}_CLIENT_ID"], "client_secret": S[f"{a.klient}_CLIENT_SECRET"],
    "refresh_token": S[a.token], "grant_type": "refresh_token"}, timeout=30).json()
if "access_token" not in odp:
    raise SystemExit(f"Token nie działa ({odp.get('error')}: {odp.get('error_description')}). Zaloguj się ponownie: logowanie.py")
H = {"Authorization": "Bearer " + odp["access_token"]}
print("Token działa.\n")


def get(url, **kw):
    r = requests.get(url, headers=H, timeout=30, **kw)
    if r.status_code != 200:
        msg = r.json().get("error", {}).get("message", r.text[:200]) if r.headers.get("content-type", "").startswith("application/json") else r.text[:200]
        raise RuntimeError(f"HTTP {r.status_code}: {msg}")
    return r.json()


print("== GA4 ==")
try:
    for konto in get("https://analyticsadmin.googleapis.com/v1beta/accountSummaries", params={"pageSize": 200}).get("accountSummaries", []):
        for prop in konto.get("propertySummaries", []):
            print(f"  {prop['property'].split('/')[1]:>12}  {prop['displayName']}  (konto: {konto['displayName']})")
except Exception as e:
    print("  BŁĄD:", e)

print("\n== Search Console ==")
try:
    for site in get("https://www.googleapis.com/webmasters/v3/sites").get("siteEntry", []):
        print(f"  {site['siteUrl']}  ({site['permissionLevel']})")
except Exception as e:
    print("  BŁĄD:", e)

print("\n== Tag Manager ==")
try:
    for konto in get("https://tagmanager.googleapis.com/tagmanager/v2/accounts").get("account", []):
        for k in get(f"https://tagmanager.googleapis.com/tagmanager/v2/{konto['path']}/containers").get("container", []):
            print(f"  {k['publicId']}  {k['name']}  (konto: {konto['name']}, ścieżka API: {k['path']})")
except Exception as e:
    print("  BŁĄD:", e)

if "ADS_DEVELOPER_TOKEN" in S:
    print("\n== Google Ads ==")
    try:
        # wersje API Ads wygasają co około roku; 404 znaczy, że trzeba podbić v23 (developers.google.com/google-ads/api/docs/sunset-dates)
        h = dict(H, **{"developer-token": S["ADS_DEVELOPER_TOKEN"]})
        r = requests.get("https://googleads.googleapis.com/v23/customers:listAccessibleCustomers", headers=h, timeout=30)
        r.raise_for_status()
        for c in r.json().get("resourceNames", []):
            print("  ", c.split("/")[1])
    except Exception as e:
        print("  BŁĄD:", e)

for nazwa in [k for k in S if k.startswith("CLARITY_TOKEN")]:
    print(f"\n== Clarity ({nazwa}) ==")
    try:
        # zużywa 1 z 10 dziennych zapytań projektu
        r = requests.get("https://www.clarity.ms/export-data/api/v1/project-live-insights", params={"numOfDays": 1},
                         headers={"Authorization": "Bearer " + S[nazwa]}, timeout=30)
        r.raise_for_status()
        print("  Działa, metryki:", ", ".join(m["metricName"] for m in r.json()))
    except Exception as e:
        print("  BŁĄD:", e)
