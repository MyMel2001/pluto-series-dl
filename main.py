#!/usr/bin/env python3
"""
Pluto TV Full Series Downloader (Fixed for Multi-Season Dropdown/Tabs)
- Input series URL
- Handles dropdown toggle, <select>, or tabs
- Scrapes & downloads all episodes with Streamlink
"""

import asyncio
import os
import subprocess
import time
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright

# === CONFIG ===
DOWNLOAD_DIR = "pluto_downloads"
DELAY_BETWEEN = 2  # seconds
MAX_PER_SEASON = None  # None = all
HEADLESS = True
# ===============

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

async def get_episodes_from_series_url(series_url: str):
    print(f"Loading series page: {series_url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.goto(series_url, wait_until="networkidle", timeout=60000)

        # Extract series slug for filenames
        slug = urlparse(series_url).path.split('/')[-1]
        title = await page.title()
        series_name = title.split(" | ")[0].strip() if ' | ' in title else slug.replace('-', ' ').title()
        print(f"Found series: {series_name}")

        episodes = []

        # Wait for content
        await page.wait_for_selector('body', timeout=15000)

        # Find season toggle/select/tabs
        season_selectors = [
            'select:has(option:has-text("Season"))',  # True <select> dropdown
            'button:has-text("Season")',              # Dropdown toggle button
            '[data-testid="season-selector"]',        # React test ID
            '.jupiter__season-header a',              # Tabs/classes
            '.season-tab',                            # Common
            'a[href*="/season/"]'                     # Direct season links
        ]

        season_els = []
        is_select = False
        is_dropdown_toggle = False
        for sel in season_selectors:
            els = await page.query_selector_all(sel)
            if els:
                season_els = els
                tag = await season_els[0].evaluate("el => el.tagName")
                is_select = tag == 'SELECT'
                is_dropdown_toggle = len(els) == 1 and 'button' in sel.lower()
                print(f"Found {len(els)} season element(s) with selector '{sel}' (Type: {tag})")
                break

        if not season_els:
            print("No season selectors found — scraping all visible episodes as Season 1")
            season_num = "01"
            ep_links = await get_episode_links(page)
            for ep_idx, link in enumerate(ep_links):
                episodes.append(await parse_episode_link(link, season_num, str(ep_idx + 1).zfill(2), slug))
            return episodes, series_name

        # Handle different types
        if is_select:
            # <select> dropdown
            options = await season_els[0].query_selector_all('option')
            for option in options:
                value = await option.get_attribute("value")
                if value:
                    await season_els[0].select_option(value=value)
                    await wait_for_episodes_load(page)
                    season_text = await option.inner_text()
                    season_num = ''.join(filter(str.isdigit, season_text)) or str(options.index(option) + 1)
                    ep_links = await get_episode_links(page)
                    for ep_idx, link in enumerate(ep_links):
                        if MAX_PER_SEASON and ep_idx >= MAX_PER_SEASON:
                            break
                        episodes.append(await parse_episode_link(link, season_num.zfill(2), str(ep_idx + 1).zfill(2), slug))
        else:
            # Tabs/buttons or dropdown toggle
            if is_dropdown_toggle:
                # Open dropdown
                await season_els[0].click()
                await page.wait_for_selector('[role="menu"], .dropdown-menu, ul', timeout=10000)
                # Get options from dropdown
                option_selectors = '[role="option"], .dropdown-item, li a'
                season_els = await page.query_selector_all(option_selectors)
                print(f"Found {len(season_els)} dropdown option(s)")

            # Now loop over (possibly new) season_els
            for season_idx, season_el in enumerate(season_els):
                season_text = await season_el.text_content() or await season_el.get_attribute("data-season") or f"Season {season_idx + 1}"
                season_num = ''.join(filter(str.isdigit, season_text)) or str(season_idx + 1)
                season_num = season_num.zfill(2)
                print(f"\nProcessing Season {season_num} ({season_text})")

                # Click/select
                try:
                    await season_el.click(force=True)
                    await wait_for_episodes_load(page)
                except Exception as e:
                    print(f"Warning: Click failed for season {season_num}: {e}")
                    # Fallback: Construct URL like /season/{season_num}
                    season_url = urljoin(series_url, f"season/{season_num}")
                    await page.goto(season_url, wait_until="networkidle")
                    await page.wait_for_timeout(3000)

                # Scrape episodes
                ep_links = await get_episode_links(page)
                print(f"  Found {len(ep_links)} episode link(s)")
                for ep_idx, link in enumerate(ep_links):
                    if MAX_PER_SEASON and ep_idx >= MAX_PER_SEASON:
                        break
                    episodes.append(await parse_episode_link(link, season_num, str(ep_idx + 1).zfill(2), slug))

                # Re-open dropdown if needed for next
                if is_dropdown_toggle:
                    toggle = await page.query_selector('button:has-text("Season")')
                    if toggle:
                        await toggle.click()
                        await page.wait_for_timeout(1000)

        await browser.close()
        return episodes, series_name

async def get_episode_links(page):
    episode_selectors = [
        'a[href*="/episode/"]',
        '.episode-tile a',
        '.jupiter__tile a[href*="/episode/"]',
        '[data-testid="episode-card"] a'
    ]
    for sel in episode_selectors:
        links = await page.query_selector_all(sel)
        if links:
            return links
    return []

async def parse_episode_link(link, season_num, ep_num, slug):
    href = await link.get_attribute("href")
    full_url = urljoin("https://pluto.tv", href)
    title_el = await link.query_selector("h3, h4, .title, [data-testid*='title']")
    title = await title_el.inner_text() if title_el else f"Episode {ep_num}"
    return {
        "url": full_url,
        "title": title.strip()[:100],
        "season": season_num,
        "episode": ep_num,
        "filename": f"{slug}_S{season_num}E{ep_num}.ts"
    }

async def wait_for_episodes_load(page):
    await page.wait_for_function("""() => {
        return document.querySelectorAll('a[href*="/episode/"]').length > 0;
    }""", timeout=10000)
    await page.wait_for_timeout(2000)  # Extra buffer

def download_with_streamlink(ep):
    filepath = os.path.join(DOWNLOAD_DIR, ep["filename"])

    cmd = [
        "streamlink",
        ep["url"],
        "best",
        "-o", filepath,
        "--hls-live-edge", "1",
        "--retry-streams", "5",
        "--retry-max", "3",
        "--force"
    ]
    print(f"  Downloading S{ep['season']}E{ep['episode']:0>2} → {ep['title'][:50]}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"    ✓ Success → {ep['filename']}")
        return True
    else:
        print(f"    ✗ Failed: {result.stderr.strip()[:150]}")
        return False

async def main():
    print("Pluto TV Full Series Downloader (Streamlink) — Dropdown/Tabs Fix!")
    print("=" * 60)
    url = input("Paste a Pluto TV series URL (e.g. https://pluto.tv/on-demand/series/jeopardy):\n> ").strip()
    if not url.startswith("http"):
        print("Invalid URL!")
        return

    try:
        episodes, series_name = await get_episodes_from_series_url(url)
        if not episodes:
            print("No episodes found. Try HEADLESS=False or check URL.")
            return

        print(f"\nFound {len(episodes)} episode(s) from '{series_name}'")
        print(f"Downloading to: {os.path.abspath(DOWNLOAD_DIR)}\n")

        success = 0
        for i, ep in enumerate(episodes, 1):
            print(f"[{i}/{len(episodes)}] ", end="")
            if download_with_streamlink(ep):
                success += 1
            time.sleep(DELAY_BETWEEN)

        print(f"\nComplete! {success}/{len(episodes)} episodes downloaded.")
    except Exception as e:
        print(f"Error: {e}")
        print("Tip: Set HEADLESS = False to watch/debug.")

if __name__ == "__main__":
    asyncio.run(main())
