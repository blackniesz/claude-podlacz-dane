# podlacz-dane — skill Claude Code

Skill, z którym Claude Code prowadzi Cię krok po kroku przez podłączenie Twoich danych marketingowych: **GA4, Google Search Console, Google Tag Manager, Microsoft Clarity i konwersji** (zdarzenia kluczowe GA4, akcje konwersji Google Ads, tagi konwersji w GTM).

Logujesz się swoim kontem Google i klikasz „Zezwól”. Nie trzeba zakładać kont technicznych ani dopisywać maili roboczych u klientów. Claude widzi to samo, co Ty widzisz w panelach, tylko do odczytu.

## Instalacja

Potrzebujesz [Claude Code](https://claude.com/claude-code) i Pythona 3 z pakietem `requests` (`pip install requests`).

```bash
git clone https://github.com/blackniesz/claude-podlacz-dane ~/.claude/skills/podlacz-dane
```

Na Windowsie w PowerShellu zamiast `~` wpisz `$HOME`. Uruchom ponownie Claude Code i napisz: **„podłącz GA4”** (albo „podepnij dane pod Claude”). Dalej poprowadzi Cię agent.

Aktualizacja: `git -C ~/.claude/skills/podlacz-dane pull`.

## Co jest w środku

| Plik | Do czego |
|---|---|
| `SKILL.md` | instrukcja dla agenta: kroki, komunikaty dla użytkownika, rozwiązywanie problemów |
| `logowanie.py` | logowanie OAuth przez przeglądarkę, zapis tokenu w `~/.secrets` |
| `sprawdz.py` | lista property GA4, stron GSC i kontenerów GTM, do których masz dostęp |

## Bezpieczeństwo

- Tokeny trafiają tylko do pliku `~/.secrets` na Twoim komputerze. Skrypty nigdy ich nie wypisują i nigdzie nie wysyłają, poza API Google i Clarity.
- Google Analytics, Search Console i Tag Manager dostają zakresy tylko do odczytu. Google Ads nie ma takiego zakresu, dlatego jest opcjonalny (`--ads`).
- Dostęp odbierasz w każdej chwili na https://myaccount.google.com/permissions.
- Nie wrzucaj `~/.secrets` ani pliku `client_secret_*.json` do żadnego repozytorium.

Skill działa tylko w Claude Code na własnym komputerze. W claude.ai logowanie przez `localhost` się nie uda.
