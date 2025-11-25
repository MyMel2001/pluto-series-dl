# Pluto TV Full Series Downloader

**A simple Python script to download entire TV series from Pluto TV using Streamlink.**

## Disclaimer
For personal archiving only. Respect Pluto TV's TOS — content is ad-supported and not for redistribution.

## About

This script lets you input any Pluto TV on-demand series URL (e.g., `https://pluto.tv/on-demand/series/the-twilight-zone`), scrapes all seasons and episodes using Playwright (handles dropdowns, tabs, and lazy loading), and downloads each episode with Streamlink. No tokens, no APIs — just pure scraping and streaming.

Works as of November 2025 for multi-season shows like *The Twilight Zone* (156 episodes across 5 seasons), *Jeopardy!*, *South Park*, *Star Trek*, etc. Episodes are saved as `.ts` files (MPEG-TS with embedded ads; post-process with FFmpeg if needed).

## Features
- **User-Friendly**: Just paste a series URL when prompted — no manual config.
- **Multi-Season Support**: Automatically detects and loops through season dropdowns, tabs, or elements with the "select" tag.
- **Robust Scraping**: Uses Playwright to handle JavaScript-heavy pages, lazy loading, and dynamic content.
- **Streamlink Integration**: Downloads high-quality HLS streams (best quality, retries on failure).
- **Customizable**: Limits per season, headless mode, delay between downloads.

## Prerequisites
1. Python 3.8+ (tested on 3.12).
2. Install dependencies:
```bash
pip install -r requirements.txt
playwright install deps
```
(See `requirements.txt` for exact versions: Playwright 1.48.0, Streamlink 6.11.0).
3. Install Playwright browsers (one-time):
```bash
playwright install chromium
```

## Installation
1. Clone or download this repo/script.
2. Install requirements (above).
3. Make the script executable (optional): `chmod +x download_pluto_series.py`.

## Usage
Run the script:
```bash
python download_pluto_series.py
```
- Prompt: Paste a Pluto TV series URL (e.g., `https://pluto.tv/on-demand/series/the-twilight-zone`).
- It scrapes seasons/episodes (shows progress).
- Downloads to `./pluto_downloads/` (creates if needed).
- Example output filenames: `the-twilight-zone_S01E01.ts`, etc.

### Customization
Edit these in the script:
- `DOWNLOAD_DIR`: Change output folder.
- `DELAY_BETWEEN`: Seconds between downloads (default: 2 to avoid bans).
- `MAX_PER_SEASON`: Limit episodes per season (default: None = all; set to 5 for testing).
- `HEADLESS = False`: Watch the browser scrape (debug mode).

### Post-Processing (Optional)
- **Remove Ads/Convert**: Use FFmpeg to skip silent ad segments and convert to MP4:
```bash
for f in pluto_downloads/*.ts; do
ffmpeg -i "$f" -vf blackframe=amount=99:threshold=0.1 -af silencedetect=noise=-30dB:d=0.5 -c:v copy -c:a aac "${f%.ts}.mp4"
done
```
- This detects and cuts ads based on black frames/silence (tune parameters for Pluto's ads).

## Troubleshooting
- **No Episodes Found?**: Set `HEADLESS=False` to watch; check for geo-blocks (use VPN for US content).
- **Streamlink Fails**: Ensure installed (`pip show streamlink`); test single episode: `streamlink [URL] best -o test.ts`.
- **Selectors Changed?**: Pluto updates rarely—inspect page (DevTools) and update `season_selectors` or `episode_selectors` arrays.
- **Rate Limits**: If banned, increase `DELAY_BETWEEN` or use proxies (add to Playwright context: `proxy={'server': 'http://your-proxy'}`).
- **Debug HTML**: If error, uncomment `print(await page.content())` in script.

## Examples
- The Twilight Zone: `https://pluto.tv/on-demand/series/the-twilight-zone` (156 episodes, 5 seasons).
- Jeopardy!: `https://pluto.tv/on-demand/series/jeopardy` (242+ episodes, 40 seasons—test with `MAX_PER_SEASON=5`).
- South Park: `https://pluto.tv/on-demand/series/south-park` (multiple seasons).


## License
MIT License — free to use/modify for personal use.

## Credits
- Built with Playwright for scraping & Streamlink for downloads.
- Inspired by community tools.
- Vibe coded with Grok.
