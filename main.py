import os
import asyncio
import random
import base64
import json
import io
import aiohttp
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.constants import ParseMode

# --- CONFIG & SECRETS ---
TG_TOKEN = os.getenv("TG_TOKEN")
CH_ID = os.getenv("CH_ID")
LINKVERTISE_ID = os.getenv("LINKVERTISE_ID")
FILE_NAME = "posted_sikar_news.txt" # Local file in your repo

# CTA for your Telegram channel
SECONDARY_LINK = "https://t.me/tedsxh" 
SECONDARY_NAME = "Join Teds Mordare Official"

# --- LOCAL HISTORY LOGIC ---
def load_history():
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return []

def save_history(urls):
    # Keep last 1000 URLs to prevent the file from getting too large
    content = "\n".join(list(dict.fromkeys(urls))[-1000:])
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        f.write(content)

# --- SCRAPER & MONETIZATION ---
def monetize(url):
    b64 = base64.b64encode(url.encode()).decode()
    return f"https://link-to.net/{LINKVERTISE_ID}/{random.random()}/dynamic?r={b64}"

async def scrape(session, target, history_set):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        async with session.get(target["url"], timeout=15, headers=headers) as r:
            soup = BeautifulSoup(await r.text(), 'html.parser')
            headlines = soup.find_all(target["tag"], limit=10)
            for h in headlines:
                link_tag = h.find_parent('a') or h.find('a')
                if not link_tag or not link_tag.get('href'): continue
                
                link = link_tag['href']
                if not link.startswith('http'):
                    link = f"https://{target['domain']}/{link.lstrip('/')}"
                
                if link in history_set: continue
                
                title = h.get_text().strip()
                if len(title) < 25: continue 
                
                img = None
                try:
                    async with session.get(link, timeout=5, headers=headers) as ar:
                        asoup = BeautifulSoup(await ar.text(), 'html.parser')
                        m = asoup.find("meta", property="og:image") or asoup.find("meta", attrs={"name": "twitter:image"})
                        if m: img = m.get('content')
                except: pass
                
                return {"title": title, "url": link, "source": target['name'], "image": img}
    except: return None

# --- MAIN ENGINE ---
async def main():
    history = load_history()
    history_set = set(history)
    
    SCRAPE_TARGETS = [
        {"url": "https://www.patrika.com/en/sikar-news", "tag": "h2", "name": "Patrika Sikar", "domain": "www.patrika.com"},
        {"url": "https://zeenews.india.com/hindi/india/rajasthan/sikar-local", "tag": "h3", "name": "Zee News Sikar", "domain": "zeenews.india.com"},
        {"url": "https://www.bhaskar.com/local/rajasthan/sikar/", "tag": "h2", "name": "Dainik Bhaskar Sikar", "domain": "www.bhaskar.com"},
        {"url": "https://firstindianews.com/districts/Sikar", "tag": "h2", "name": "First India News", "domain": "firstindianews.com"}
    ]

    bot = Bot(token=TG_TOKEN)
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[scrape(session, t, history_set) for t in SCRAPE_TARGETS])
        fresh = [r for r in results if r]
        
        if not fresh:
            print("💤 No new news.")
            return

        for art in fresh:
            if art['url'] in history_set: continue
            
            msg = (
                f"📍 **SIKAR LOCAL UPDATES**\n\n"
                f"📰 **{art['title'].upper()}**\n\n"
                f"🏛️ Source: {art['source']}\n"
                f"🔗 [READ FULL STORY]({monetize(art['url'])})\n\n"
                f"📢 **STAY UPDATED:** [{SECONDARY_NAME}]({SECONDARY_LINK})\n"
                f"#Sikar #Rajasthan #SikarNews"
            )
            
            try:
                if art['image']:
                    await bot.send_photo(CH_ID, art['image'], caption=msg[:1024], parse_mode=ParseMode.MARKDOWN)
                else:
                    await bot.send_message(CH_ID, msg, parse_mode=ParseMode.MARKDOWN)
                
                history.append(art['url'])
                history_set.add(art['url'])
                print(f"✅ Posted: {art['source']}")
                await asyncio.sleep(5) 
            except Exception as e:
                print(f"❌ Telegram Error: {e}")
        
        # Save updated history back to the local file
        save_history(history)

if __name__ == "__main__":
    asyncio.run(main())
