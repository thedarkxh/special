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
POST_LIMIT = 10  # Increased to 10 posts per run

SECONDARY_LINK = "https://t.me/tedsxh" 
SECONDARY_NAME = "Join Teds Mordare Official"

def load_history():
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return []

def save_history(urls):
    content = "\n".join(list(dict.fromkeys(urls))[-2000:]) # Increased history buffer
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        f.write(content)

async def scrape(session, target, history_set):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    found_articles = []
    try:
        async with session.get(target["url"], timeout=20, headers=headers) as r:
            if r.status != 200: return []
            soup = BeautifulSoup(await r.text(), 'html.parser')
            headlines = soup.find_all(target["tag"], limit=15)
            
            for h in headlines:
                link_tag = h.find_parent('a') or h.find('a')
                if not link_tag or not link_tag.get('href'): continue
                link = link_tag['href']
                if not link.startswith('http'):
                    link = f"https://{target['domain']}/{link.lstrip('/')}"
                
                if link in history_set: continue
                
                title = h.get_text().strip()
                if len(title) < 25: continue 

                # Get Image
                img = None
                try:
                    async with session.get(link, timeout=5, headers=headers) as ar:
                        asoup = BeautifulSoup(await ar.text(), 'html.parser')
                        m = asoup.find("meta", property="og:image") or asoup.find("meta", attrs={"name": "twitter:image"})
                        if m: img = m.get('content')
                except: pass
                
                found_articles.append({"title": title, "url": link, "source": target['name'], "image": img})
    except: pass
    return found_articles

async def main():
    history = load_history()
    history_set = set(history)
    
    # INCREASED SOURCES
    SCRAPE_TARGETS = [
        {"url": "https://www.bhaskar.com/local/rajasthan/sikar/", "tag": "h2", "name": "Dainik Bhaskar", "domain": "www.bhaskar.com"},
        {"url": "https://www.rajasthanpatrika.com/sikar-news/", "tag": "h3", "name": "Rajasthan Patrika", "domain": "www.rajasthanpatrika.com"},
        {"url": "https://zeenews.india.com/hindi/india/rajasthan/sikar-local", "tag": "h3", "name": "Zee Rajasthan", "domain": "zeenews.india.com"},
        {"url": "https://firstindianews.com/districts/Sikar", "tag": "h2", "name": "First India News", "domain": "firstindianews.com"},
        {"url": "https://hindi.news18.com/rajasthan/sikar/", "tag": "h2", "name": "News18 Sikar", "domain": "hindi.news18.com"},
        {"url": "https://www.amarujala.com/rajasthan/sikar", "tag": "h3", "name": "Amar Ujala", "domain": "www.amarujala.com"}
    ]

    bot = Bot(token=TG_TOKEN)
    all_fresh = []

    async with aiohttp.ClientSession() as session:
        tasks = [scrape(session, t, history_set) for t in SCRAPE_TARGETS]
        results = await asyncio.gather(*tasks)
        for res in results:
            all_fresh.extend(res)

        if not all_fresh:
            print("💤 No new news.")
            return

        # Randomize to mix sources and pick up to POST_LIMIT
        random_sample = all_fresh[:POST_LIMIT]
        
        posted_count = 0
        for art in random_sample:
            if art['url'] in history_set: continue
            
            msg = (
                f"📍 **सीकर ताजा खबर (SIKAR NEWS)**\n\n"
                f"📰 **{art['title'].upper()}**\n\n"
                f"🏛️ Source: {art['source']}\n"
                f"🔗 [READ FULL STORY]({art['url']})\n\n"
                f"📢 **Join:** [{SECONDARY_NAME}]({SECONDARY_LINK})\n"
                f"#Sikar #Rajasthan #सीकर"
            )
            
            try:
                if art['image']:
                    await bot.send_photo(CH_ID, art['image'], caption=msg[:1024], parse_mode=ParseMode.MARKDOWN)
                else:
                    await bot.send_message(CH_ID, msg, parse_mode=ParseMode.MARKDOWN)
                
                history.append(art['url'])
                history_set.add(art['url'])
                posted_count += 1
                await asyncio.sleep(5) 
            except Exception as e:
                print(f"❌ Error: {e}")

        print(f"✅ Successfully posted {posted_count} new updates.")
        save_history(history)

if __name__ == "__main__":
    asyncio.run(main())
