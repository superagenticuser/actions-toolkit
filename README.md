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

## Code health

| Workflow | File | What it does | Inputs |
|---|---|---|---|
| 🔎 JS syntax check | `js-syntax-check.yml` | `node --check` on every JS file | path |
| 🧹 Prettier check / fix | `prettier.yml` | Check formatting, or fix + open a PR | mode, path |
| 🐍 Python lint | `ruff.yml` | ruff check + format check | path |
| 🔤 Spell check | `codespell.yml` | Typos in code and docs | path |
| 🕵️ Secret scan | `gitleaks.yml` | Hunt leaked secrets in git history | — |
| 📝 TODO reporter | `todo-report.yml` | Lists every TODO/FIXME/HACK marker | path |

## Dependencies & security

| Workflow | File | What it does | Inputs |
|---|---|---|---|
| 📦 Outdated packages | `outdated.yml` | npm + pip outdated report | — |
| 🛡️ Dependency audit | `audit.yml` | npm audit + pip-audit summary | — |
| 🔍 ZAP security scan | `zap-scan.yml` | OWASP ZAP baseline scan of a URL | url |
| 🔄 Dependency update PR | `dep-update-pr.yml` | Bumps npm deps, opens a PR | — |
| 🧾 SBOM generator | `sbom.yml` | Software bill of materials (SPDX) | path |
| 📜 License audit | `license-audit.yml` | Lists dependency licenses | — |

## Repo maintenance

| Workflow | File | What it does | Inputs |
|---|---|---|---|
| 🌿 Stale branches | `stale-branches.yml` | Lists branches vs default; optional delete of merged | delete_merged |
| 🐘 Repo bloat finder | `bloat-finder.yml` | Biggest files in tree and in git history | — |
| 📊 Contributor stats | `contributor-stats.yml` | Commits per author, history span | — |
| 🗓️ Release from tag | `release.yml` | Changelog + published GitHub release | tag, prerelease |
| 🧪 Test runner | `test-runner.yml` | Auto-detects and runs npm/pytest/go tests | — |
| 📉 Build size report | `build-size.yml` | Builds the project, reports bundle weights | build_command, output_dir |
| 🐳 Docker build + scan | `docker-scan.yml` | Builds image, Trivy HIGH/CRITICAL scan | dockerfile, context |
| 🔀 Branch conflict detector | `conflict-detector.yml` | Flags branches conflicting with default | — |
| 🗑️ Workflow run cleanup | `run-cleanup.yml` | Deletes old completed runs (dry-run default) | older_than_days, dry_run |
| 🖼️ Image compressor | `image-compress.yml` | Shrinks PNG/JPG, opens a PR | quality |

## Small utilities

| Workflow | File | What it does | Inputs |
|---|---|---|---|
| ✅ JSON / YAML validator | `json-validator.yml` | Validates a pasted document | format, text |
| ⏰ Cron explainer | `cron-explainer.yml` | `0 9 * * 1` → plain English | expression |
| 🔓 JWT decoder | `jwt-decoder.yml` | Decodes header/payload (no verification) | token |
| 🌐 Uptime check | `uptime-check.yml` | Status + response time for URL list | urls |
| 📣 ntfy notifier | `ntfy.yml` | Push notification to your phone | topic, message, title |

## Create & look up

| Workflow | File | What it does | Inputs |
|---|---|---|---|
| 🖼️ OG image generator | `og-image.yml` | Social title-card PNG (1200×630) | title, subtitle, theme |
| 🗺️ Geocoder | `geocode.yml` | Address → coordinates (no key) | address |
| 💱 Currency converter | `currency.yml` | Keyless FX conversion | amount, from, to |
| 📝 Markdown to HTML | `md-convert.yml` | pandoc conversion to HTML | markdown, title |
| 📊 CSV to chart | `csv-chart.yml` | Renders a line/bar chart PNG | csv, chart_type, title |
| 🔄 Data format converter | `data-convert.yml` | JSON ↔ YAML ↔ CSV | from, to, text |
| 🕸️ Sitemap generator | `sitemap.yml` | Crawls same-domain links → sitemap.xml | start_url, max_pages |
| 📡 DNS propagation check | `dns-propagation.yml` | Compares Google/Cloudflare/Quad9/OpenDNS | domain |
| 🔎 Tech stack detector | `tech-stack.yml` | Guesses what a site is built with | url |
| 📋 Issue exporter | `issue-exporter.yml` | Issues → CSV artifact | state |
| 📥 Artifact downloader | `artifact-download.yml` | Grabs artifacts from any past run | run_id |
| 🎰 Random repo discoverer | `random-repo.yml` | GitHub serendipity machine | — |
| ⏱️ Pomodoro timer | `pomodoro.yml` | Focus timer + optional ntfy ping | minutes, ntfy_topic |
| 📚 Wikipedia summary | `wikipedia.yml` | Clean one-pager on any topic | topic |

Results show up in the run summary and/or as downloadable **artifacts**.

## Notes

- Workflows that hit public APIs (weather, CoinGecko, CelesTrak, Hacker News, Open-Meteo) need **no API keys**.
- `repo-backup` works on public repos as-is; for private repos add a PAT secret named `BACKUP_PAT` (see the comment in the file).
- The ISS predictor reports radio-visible passes (above 10° elevation); seeing it with your eyes also needs a dark sky.
- Treat `passphrase` run logs as secret — delete the run after copying your phrase.
