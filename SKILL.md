---
name: podlacz-dane
description: Prowadzi użytkownika krok po kroku przez podłączenie jego danych marketingowych do Claude Code — GA4, Search Console, Google Tag Manager (logowanie OAuth własnym kontem Google, token ląduje w ~/.secrets), Microsoft Clarity (token API) i konwersje (zdarzenia kluczowe GA4, akcje konwersji Google Ads, tagi konwersji w GTM). Bez kont technicznych i bez dodawania maili roboczych u klientów. Na końcu sprawdza, do jakich property, stron i kontenerów jest dostęp. Wyzwalacze: "podłącz GA4", "podłącz Search Console", "podepnij dane pod Claude", "jak dać Claude dostęp do analityki", "podłącz Clarity", "podłącz GTM", "podłącz konwersje", "token wygasł", "invalid_grant".
---

# Podłączenie danych marketingowych do Claude Code

## O co chodzi i dlaczego tak

Użytkownik loguje się **swoim** kontem Google, klika „Zezwól”, a skrypt zapisuje refresh token w `~/.secrets`. Od tej chwili każda sesja Claude Code widzi dokładnie to, co ten człowiek widzi w GA4, GSC i GTM — bez kont usługowych, bez dopisywania maili technicznych u każdego klienta, bez proszenia klientów o uprawnienia. Jeden token na wszystkie trzy usługi, bo wszystkie są pod tym samym kontem Google.

Zakresy są tylko do odczytu (`analytics.readonly`, `webmasters.readonly`, `tagmanager.readonly`). Wyjątkiem jest Google Ads, które nie ma zakresu tylko do odczytu, dlatego jest osobną, opcjonalną flagą (`--ads`), a z tym tokenem wolno wołać wyłącznie zapytania odczytu (`search`, `listAccessibleCustomers`), nigdy `mutate`.

Clarity nie obsługuje OAuth, tam jest token API wygenerowany w panelu projektu.

## Jak prowadzić użytkownika

Zakładaj, że użytkownik nigdy nie widział Google Cloud Console i nie wie, co to OAuth. Dlatego:

- **Jeden krok na raz.** Podaj krok, poczekaj na „zrobione” albo na zrzut ekranu, dopiero potem następny. Ściana dziesięciu kroków kończy się tym, że człowiek gubi się na trzecim i nie wie, gdzie.
- Mów, **co kliknąć i co ma zobaczyć**, nie co się dzieje pod spodem. Nazwy przycisków podawaj tak, jak są w interfejsie (Google pokazuje je po polsku albo angielsku zależnie od ustawień konta, więc podawaj oba warianty, gdy są różne).
- Gdy coś wygląda inaczej niż w opisie, poproś o zrzut ekranu. Interfejs Google Cloud zmienia się co kilka miesięcy, opis niżej może być w szczegółach nieaktualny.
- Wszystko, co da się zrobić z terminala, robisz sam. Użytkownik tylko klika w przeglądarce.
- Nigdy nie wypisuj wartości tokenów ani `client_secret`, nie każ ich wklejać do czatu. Pliki z kluczami czytają skrypty.

Zanim zaczniesz, sprawdź, co już jest (same nazwy, bez wartości):

```bash
python -c "import os;p=os.path.expanduser('~/.secrets');print([l.split('=',1)[0].strip() for l in open(p,encoding='utf-8-sig') if '=' in l and not l.lstrip().startswith('#')] if os.path.exists(p) else 'brak pliku ~/.secrets')"
```

- Jest `DANE_REFRESH_TOKEN` → od razu krok 5 (sprawdzenie). Może wszystko już działa.
- Jest już klient OAuth typu „Aplikacja komputerowa” pod inną nazwą (para `<PREFIX>_CLIENT_ID` / `<PREFIX>_CLIENT_SECRET`) → pomiń kroki 1–3, w kroku 4 użyj `--klient <PREFIX>`. Sprawdź tylko z użytkownikiem, czy w projekcie tego klienta są włączone API z kroku 2.
- Nic nie ma → od kroku 1. Potrzebny jest `python` z pakietem `requests` (`pip install requests`).

Skrypty leżą obok tego pliku: `~/.claude/skills/podlacz-dane/logowanie.py` i `sprawdz.py`.

## Część A: Google (GA4, Search Console, GTM) — jednorazowo ok. 10 minut

### Krok 1. Projekt w Google Cloud

Powiedz użytkownikowi:

> Wejdź na https://console.cloud.google.com i zaloguj się tym kontem Google, które ma dostęp do GA4 i Search Console. Pierwszy raz Google poprosi o akceptację regulaminu — zaakceptuj. U góry, obok logo, kliknij listę projektów → **Nowy projekt** (New project). Nazwa dowolna, np. `claude-dane`. Kliknij **Utwórz** i poczekaj, aż projekt się wybierze (jego nazwa pojawi się u góry).

Projekt jest darmowy, nie wymaga karty. Te API nie są płatne.

### Krok 2. Włączenie API

Podaj linki po kolei, przy każdym użytkownik klika **Włącz** (Enable). Upewnij się, że u góry jest wybrany projekt z kroku 1.

1. https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com — GA4 raporty
2. https://console.cloud.google.com/apis/library/analyticsadmin.googleapis.com — GA4 lista property, zdarzenia kluczowe
3. https://console.cloud.google.com/apis/library/searchconsole.googleapis.com — Search Console
4. https://console.cloud.google.com/apis/library/tagmanager.googleapis.com — Tag Manager
5. Tylko gdy chce Google Ads: https://console.cloud.google.com/apis/library/googleads.googleapis.com

### Krok 3. Ekran zgody i klient OAuth

To jedyny nudny krok. Prowadź bardzo powoli.

> Wejdź na https://console.cloud.google.com/auth/overview i kliknij **Rozpocznij** (Get started).
> - Nazwa aplikacji: `Claude dane`. E-mail pomocy: Twój mail. **Dalej.**
> - Odbiorcy (Audience): **Zewnętrzni** (External). **Dalej.**
> - Dane kontaktowe: Twój mail. **Dalej**, zaznacz zgodę na zasady, **Utwórz.**

Potem — **to jest ważne, nie pomijaj**:

> Wejdź w zakładkę **Odbiorcy** (Audience) i kliknij **Opublikuj aplikację** (Publish app) → **Potwierdź**. Status ma się zmienić na „W wersji produkcyjnej” (In production).

Dlaczego: w trybie „Testowanie” Google unieważnia token po 7 dniach i za tydzień nic nie działa. Publikacja nie wystawia niczego publicznie, aplikacja nadal jest tylko w tym projekcie. Weryfikacji przez Google nie trzeba przechodzić — przy logowaniu pojawi się tylko ostrzeżenie „aplikacja niezweryfikowana” (krok 4).

Na koniec klient:

> Wejdź na https://console.cloud.google.com/auth/clients → **Utwórz klienta** (Create client). Typ aplikacji: **Aplikacja komputerowa** (Desktop app). Nazwa: `claude-code`. **Utwórz.** W okienku, które się pojawi, kliknij **Pobierz JSON** (Download JSON). Plik wyląduje w Pobranych jako `client_secret_....json`. Napisz mi „pobrane”.

Znajdź plik sam (`ls ~/Downloads/client_secret_*.json`), nie każ użytkownikowi podawać ścieżki ani zawartości. Typ musi być „Aplikacja komputerowa” — „Aplikacja internetowa” nie zadziała z logowaniem przez localhost, skrypt to wykryje.

### Krok 4. Logowanie

Uruchom w tle (skrypt czeka na kliknięcie do 15 minut):

```bash
python ~/.claude/skills/podlacz-dane/logowanie.py --link "<scratchpad>/link.txt" --client-json ~/Downloads/client_secret_XXX.json
```

Dodaj `--ads`, jeśli użytkownik chce Google Ads. Gdy klient jest już w `~/.secrets`, zamiast `--client-json` daj `--klient PREFIX`.

Gdy w pliku pojawi się link, przeczytaj go i podaj użytkownikowi do kliknięcia, mówiąc:

> Kliknij link. Wybierz konto Google, które ma dostęp do danych. Zobaczysz ostrzeżenie „Google nie zweryfikował tej aplikacji” — to normalne, bo to Twoja własna aplikacja. Kliknij **Zaawansowane** (Advanced) → **Przejdź do Claude dane (niebezpieczne)**. Na ekranie z uprawnieniami **zaznacz wszystkie pola** i kliknij **Kontynuuj**. Gdy zobaczysz „Gotowe, możesz zamknąć tę kartę” — wróć tutaj.

Skrypt zapisuje w `~/.secrets`: `DANE_OAUTH_CLIENT_ID`, `DANE_OAUTH_CLIENT_SECRET`, `DANE_REFRESH_TOKEN`. Jeśli wypisze „nie odhaczono zakresów”, użytkownik nie zaznaczył któregoś pola — odpal logowanie jeszcze raz.

Po sukcesie zaproponuj usunięcie pliku `client_secret_*.json` z Pobranych, bo klient jest już w `~/.secrets`, a luźny plik z sekretem w Pobranych to niepotrzebne ryzyko.

### Krok 5. Sprawdzenie

```bash
python ~/.claude/skills/podlacz-dane/sprawdz.py
```

Wypisze property GA4, strony GSC i kontenery GTM, do których konto ma dostęp. Pokaż to użytkownikowi i zapytaj, czy czegoś nie brakuje. Brak property albo strony prawie zawsze znaczy, że zalogował się innym kontem Google niż to z dostępem — wtedy krok 4 jeszcze raz, przy wyborze konta uważnie.

Zaproponuj zapisanie listy (identyfikatory property, adresy stron, ID kontenerów) w pliku projektu, np. w `CLAUDE.md`, żeby kolejne sesje nie musiały jej odpytywać.

## Część B: Microsoft Clarity — 2 minuty

> Wejdź na https://clarity.microsoft.com, otwórz projekt strony → **Ustawienia** (Settings) → **Eksport danych** (Data Export) → **Wygeneruj nowy token API** (Generate new API token). Nazwa dowolna, np. `claude`. Token pokaże się tylko raz.

Musi to zrobić administrator projektu Clarity. Token nie może przejść przez czat. Poproś użytkownika, żeby sam dopisał go na końcu `~/.secrets` jako jedną linię `CLARITY_TOKEN_<NAZWA_STRONY>=...` (np. `CLARITY_TOKEN_SKLEP`), w Notatniku: `notepad %USERPROFILE%\.secrets` (Windows) albo `nano ~/.secrets` (Mac/Linux). Jeden token na projekt Clarity, więc przy kilku stronach kilka linii. Potem `sprawdz.py` sam je znajdzie.

Co trzeba wiedzieć o Clarity API, zanim obiecasz użytkownikowi analizy:
- Daje **tylko ostatnie 1–3 dni** (`numOfDays=1|2|3`) i **10 zapytań dziennie na projekt**. Do historii trzeba codziennie zrzucać dane do pliku albo bazy. Każdy wynik od razu zapisuj do JSON-a, nie odpytuj drugi raz o to samo.
- Endpoint: `GET https://www.clarity.ms/export-data/api/v1/project-live-insights?numOfDays=3&dimension1=URL`, nagłówek `Authorization: Bearer <token>`. Wymiary (do trzech: `dimension1..3`): `Browser`, `Device`, `Country`, `OS`, `Source`, `Medium`, `Campaign`, `Channel`, `URL`.
- Zwraca metryki zachowań: sesje, przewijanie, martwe i wściekłe kliknięcia (dead/rage clicks), szybkie powroty, błędy JS. Nagrań sesji ani map ciepła przez API nie ma — po to użytkownik wchodzi do panelu.

## Część C: Google Tag Manager

Działa od razu po części A (zakres `tagmanager.readonly`). Opublikowana wersja kontenera, czyli to, co faktycznie działa na stronie:

```
GET https://tagmanager.googleapis.com/tagmanager/v2/accounts/<accountId>/containers/<containerId>/versions:live
```

`<accountId>/<containerId>` to ścieżka API wypisana przez `sprawdz.py` (nie publiczny `GTM-XXXX`). Odpowiedź zawiera tagi, wyzwalacze i zmienne. Typy tagów, które Cię zwykle interesują: `awct` (konwersja Google Ads), `gclidw` (łącznik konwersji), `googtag` (tag Google / GA4), `gaawe` (zdarzenie GA4), `html` (własny HTML — tam często siedzą piksele innych systemów).

Ten token nie publikuje ani nie zmienia niczego w GTM i tak ma zostać. Zmiany w kontenerze robi człowiek w panelu.

## Część D: Konwersje

„Konwersje” to trzy różne rzeczy w trzech miejscach. Zapytaj użytkownika, o którą chodzi, albo pokaż wszystkie trzy obok siebie — **nigdy się nie zgadzają co do sztuki** (inne modele atrybucji, inne okna, Consent Mode) i to nie jest błąd do naprawiania.

1. **Zdarzenia kluczowe GA4** (dawniej „konwersje GA4”) — działa od razu po części A.
   - Lista: `GET https://analyticsadmin.googleapis.com/v1beta/properties/<id>/keyEvents`
   - Liczby: `POST https://analyticsdata.googleapis.com/v1beta/properties/<id>:runReport` z `{"dateRanges":[{"startDate":"28daysAgo","endDate":"yesterday"}],"dimensions":[{"name":"eventName"}],"metrics":[{"name":"keyEvents"}]}`

2. **Akcje konwersji Google Ads** — wymagają dodatkowo **tokenu dewelopera**, bez niego Ads API nie odpowiada. To najtrudniejszy element całego playbooka; jeśli użytkownikowi nie zależy, odpuść i zostań przy GA4.
   - Token dewelopera: konto menedżera (MCC) w Google Ads → **Administracja → Centrum API** (API Center). Wypełnić wniosek. Na starcie dostaje się dostęp „testowy”, który działa tylko na kontach testowych; do prawdziwych kont trzeba złożyć wniosek o **Basic access** i poczekać na akceptację (zwykle kilka dni). Bez konta MCC tokenu nie ma — MCC zakłada się za darmo.
   - Token dewelopera użytkownik dopisuje sam do `~/.secrets` jako `ADS_DEVELOPER_TOKEN=...`, a logowanie z kroku 4 trzeba powtórzyć z flagą `--ads`.
   - Zapytanie: `POST https://googleads.googleapis.com/v23/customers/<id_konta_bez_kresek>/googleAds:search`, nagłówki `Authorization`, `developer-token` i — gdy dostęp idzie przez MCC — `login-customer-id: <id_MCC_bez_kresek>`. Treść: `{"query": "SELECT conversion_action.name, conversion_action.category, conversion_action.status, conversion_action.primary_for_goal, metrics.all_conversions FROM conversion_action WHERE segments.date DURING LAST_30_DAYS"}`. Wersje API wygasają mniej więcej co rok; błąd 404 znaczy, że trzeba podbić `v23`.
   - Patrz na `primary_for_goal`: tylko akcje główne idą do kolumny „Konwersje” i uczą algorytm stawek. Pomocnicze (odsłona cennika, przewinięcie strony) wyglądają w raportach jak leady, a nimi nie są.

3. **Tagi konwersji w GTM** — czyli czy konwersja w ogóle jest wysyłana i na jakim wyzwalaczu. Część C, tagi typu `awct` i `gaawe`. Przydaje się, gdy liczby z punktów 1 i 2 wyglądają podejrzanie: zero albo nagły skok to najczęściej zepsuty albo zdublowany tag.

## Gdy coś nie działa

| Objaw | Przyczyna | Co zrobić |
|---|---|---|
| `invalid_grant` po tygodniu | aplikacja została w trybie „Testowanie” | krok 3, „Opublikuj aplikację”, potem krok 4 |
| `invalid_grant` po zmianie hasła albo po długim nieużywaniu | Google unieważnił token (też po 6 miesiącach bez użycia) | krok 4 jeszcze raz |
| `access_denied` / „Dostęp zablokowany” przy logowaniu | aplikacja w trybie testowym, a konto nie jest na liście testerów | opublikuj aplikację (krok 3) |
| `redirect_uri_mismatch` | klient typu „Aplikacja internetowa” | utwórz nowego klienta typu „Aplikacja komputerowa” |
| 403 `... API has not been used in project ...` | API niewłączone | krok 2, link do brakującego API |
| 403 `insufficient permissions` / `insufficientPermissions` | przy zgodzie nie zaznaczono wszystkich pól | krok 4, zaznaczyć wszystko |
| Pusta lista property albo stron | zalogowane inne konto Google | krok 4, przy wyborze konta wybrać właściwe |
| Clarity 401 | token zły albo z innego projektu | wygenerować nowy w danym projekcie |
| Clarity 429 | wyczerpane 10 zapytań na dziś | czekać do jutra, korzystać z zapisanego JSON-a |
| Ads `DEVELOPER_TOKEN_NOT_APPROVED` | token tylko z dostępem testowym | wniosek o Basic access w Centrum API |

## Bezpieczeństwo — powiedz o tym użytkownikowi na koniec

- `~/.secrets` daje odczyt **wszystkich** danych, do których ma dostęp to konto Google, u wszystkich klientów. Nie wrzucać do repo, nie wysyłać mailem, nie kopiować na serwer bez potrzeby.
- Odebranie dostępu w każdej chwili: https://myaccount.google.com/permissions → „Claude dane” → **Usuń dostęp**. Token przestaje działać natychmiast. Token Clarity usuwa się w tym samym miejscu, gdzie się go generowało.
- Podejrzenie wycieku pliku → odebrać dostęp jak wyżej, w Google Cloud usunąć i utworzyć klienta OAuth na nowo, wygenerować nowe tokeny Clarity.
