import os
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.constants import ParseMode

# --- CONFIG ---
TG_TOKEN = os.getenv("TG_TOKEN")
CH_ID = os.getenv("CH_ID")
FILE_NAME = "posted_sikar_news.txt"

# Secondary CTA
SECONDARY_LINK = "https://t.me/tedsxh" 
SECONDARY_NAME = "Join Teds Mordare Official"

def load_history():
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return []

def save_history(urls):
    # Keeps only the last 1000 entries to maintain performance
    content = "\n".join(list(dict.fromkeys(urls))[-1000:])
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        f.write(content)

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

async def main():
    history = load_history()
    history_set = set(history)
    
    SCRAPE_TARGETS = [
        {"url": "https://www.bhaskar.com/local/rajasthan/sikar/", "tag": "h2", "name": "Dainik Bhaskar", "domain": "www.bhaskar.com"},
        {"url": "https://www.rajasthanpatrika.com/sikar-news/", "tag": "h3", "name": "Rajasthan Patrika", "domain": "www.rajasthanpatrika.com"},
        {"url": "https://zeenews.india.com/hindi/india/rajasthan/sikar-local", "tag": "h3", "name": "Zee Rajasthan", "domain": "zeenews.india.com"},
        {"url": "https://firstindianews.com/districts/Sikar", "tag": "h2", "name": "First India News", "domain": "firstindianews.com"}
    ]

    bot = Bot(token=TG_TOKEN)
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[scrape(session, t, history_set) for t in SCRAPE_TARGETS])
        fresh = [r for r in results if r]
        
        if not fresh:
            print("💤 No new updates.")
            return

        for art in fresh:
            # Clean message without Linkvertise
            msg = (
                f"📍 **सीकर ताजा खबर (SIKAR NEWS)**\n\n"
                f"📰 **{art['title'].upper()}**\n\n"
                f"🏛️ Source: {art['source']}\n"
                f"🔗 [READ FULL STORY]({art['url']})\n\n"
                f"📢 **Join for More:** [{SECONDARY_NAME}]({SECONDARY_LINK})\n"
                f"#Sikar #Rajasthan #सीकर #LocalNews"
            )
            
            try:
                if art['image']:
                    await bot.send_photo(CH_ID, art['image'], caption=msg[:1024], parse_mode=ParseMode.MARKDOWN)
                else:
                    await bot.send_message(CH_ID, msg, parse_mode=ParseMode.MARKDOWN)
                
                history.append(art['url'])
                print(f"✅ Posted: {art['source']}")
                await asyncio.sleep(5) 
            except Exception as e:
                print(f"❌ Telegram Error: {e}")
        
        save_history(history)

if __name__ == "__main__":
    asyncio.run(main())
