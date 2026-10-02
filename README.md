# 🧰 Actions Toolkit

On-demand GitHub Actions you can run whenever you want — no schedules, no triggers on push. Every workflow is a **single self-contained file**, so you can copy any `.github/workflows/*.yml` into another repo and it just works.

Open the repo's **Actions tab**, pick a workflow, hit **Run workflow**, fill in the inputs.

## The toolkit

| Workflow | File | What it does | Inputs |
|---|---|---|---|
| 📸 Website screenshots | `screenshot.yml` | Headless-Chrome screenshots of any URL, desktop + mobile | url, fullPage |
| 📄 Webpage to PDF | `webpage-pdf.yml` | Renders any URL to an A4 PDF | url |
| 📊 Lighthouse audit | `lighthouse.yml` | Performance/accessibility audit with public report link | url |
| 🔗 Link check | `link-check.yml` | Crawls a URL for broken links | url |
| 🔳 QR code generator | `qr-code.yml` | QR PNG for any text/URL | text |
| 🔍 Domain checkup | `domain-checkup.yml` | DNS, TLS cert dates, HTTP headers | domain |
| 🎲 Dice / coin / picker | `dice.yml` | Coin flip, dice roll, or random pick from your list | mode, sides, choices |
| 🌤️ Weather snapshot | `weather.yml` | Current + 3-day forecast, no API key (Open-Meteo) | city |
| 📰 Tech news briefing | `news-briefing.yml` | Top Hacker News stories as markdown | limit |
| 🛰 ISS flyover predictor | `iss-flyover.yml` | Real pass predictions over your location (CelesTrak TLE + SGP4) | latitude, longitude, days |
| 🔐 Passphrase generator | `passphrase.yml` | EFF-wordlist passphrase (hex fallback) | words, separator |
| 💰 Crypto price check | `price-check.yml` | Price, 24h change, market cap (CoinGecko) | coin, vs |
| 💾 Repo backup | `repo-backup.yml` | Zips any public repo into a downloadable artifact | repo |
| 🛰 TLE snapshot | `tle-snapshot.yml` | Downloads CelesTrak TLE sets as an offline cache | — |

Results show up in the run summary and/or as downloadable **artifacts**.

## Notes

- Workflows that hit public APIs (weather, CoinGecko, CelesTrak, Hacker News, Open-Meteo) need **no API keys**.
- `repo-backup` works on public repos as-is; for private repos add a PAT secret named `BACKUP_PAT` (see the comment in the file).
- The ISS predictor reports radio-visible passes (above 10° elevation); seeing it with your eyes also needs a dark sky.
- Treat `passphrase` run logs as secret — delete the run after copying your phrase.
