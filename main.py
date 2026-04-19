import os
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.constants import ParseMode

# --- CONFIGURATION ---
# These must be set in your GitHub Repository Secrets
TG_TOKEN = os.getenv("TG_TOKEN")
CH_ID = os.getenv("CH_ID")
FILE_NAME = "posted_sikar_news.txt"

# Branding & Call to Action
SECONDARY_LINK = "https://t.me/tedsxh" 
SECONDARY_NAME = "Join Teds Mordare Official"

def load_history():
    """Reads the history file from the local repository."""
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return []

def save_history(urls):
    """Saves the last 1000 unique URLs to keep the file lightweight."""
    content = "\n".join(list(dict.fromkeys(urls))[-1000:])
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        f.write(content)

async def scrape(session, target, history_set):
    """Scrapes individual news sources with error handling."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        async with session.get(target["url"], timeout=15, headers=headers) as r:
            if r.status != 200: return None
            
            soup = BeautifulSoup(await r.text(), 'html.parser')
            # Look for headlines based on the defined tag
            headlines = soup.find_all(target["tag"], limit=12)
            
            for h in headlines:
                link_tag = h.find_parent('a') or h.find('a')
                if not link_tag or not link_tag.get('href'): continue
                
                link = link_tag['href']
                # Handle relative URLs
                if not link.startswith('http'):
                    link = f"https://{target['domain']}/{link.lstrip('/')}"
                
                # DUPLICATE PROTECTION
                if link in history_set: continue
                
                title = h.get_text().strip()
                if len(title) < 25: continue 
                
                # Fetch Meta Image for the post
                img = None
                try:
                    async with session.get(link, timeout=5, headers=headers) as ar:
                        asoup = BeautifulSoup(await ar.text(), 'html.parser')
                        m = asoup.find("meta", property="og:image") or asoup.find("meta", attrs={"name": "twitter:image"})
                        if m: img = m.get('content')
                except: pass
                
                return {"title": title, "url": link, "source": target['name'], "image": img}
    except Exception as e:
        print(f"⚠️ Scrape error for {target['name']}: {e}")
        return None

async def main():
    # 1. Sync local history
    history = load_history()
    history_set = set(history)
    
    # 2. Define Sikar-specific targets
    SCRAPE_TARGETS = [
        {"url": "https://www.bhaskar.com/local/rajasthan/sikar/", "tag": "h2", "name": "Dainik Bhaskar", "domain": "www.bhaskar.com"},
        {"url": "https://www.rajasthanpatrika.com/sikar-news/", "tag": "h3", "name": "Rajasthan Patrika", "domain": "www.rajasthanpatrika.com"},
        {"url": "https://zeenews.india.com/hindi/india/rajasthan/sikar-local", "tag": "h3", "name": "Zee Rajasthan", "domain": "zeenews.india.com"},
        {"url": "https://firstindianews.com/districts/Sikar", "tag": "h2", "name": "First India News", "domain": "firstindianews.com"}
    ]

    bot = Bot(token=TG_TOKEN)
    
    async with aiohttp.ClientSession() as session:
        # Run all scrapers in parallel for speed
        results = await asyncio.gather(*[scrape(session, t, history_set) for t in SCRAPE_TARGETS])
        fresh_news = [r for r in results if r]
        
        if not fresh_news:
            print("💤 No new updates found for Sikar.")
            return

        for art in fresh_news:
            # Re-check history set to handle identical news across different sources
            if art['url'] in history_set: continue
            
            # Clean Bilingual Template
            msg = (
                f"📍 **सीकर ताजा खबर (SIKAR NEWS)**\n\n"
                f"📰 **{art['title'].upper()}**\n\n"
                f"🏛️ Source: {art['source']}\n"
                f"🔗 [READ FULL STORY]({art['url']})\n\n"
                f"📢 **Join for More:** [{SECONDARY_NAME}]({SECONDARY_LINK})\n"
                f"#Sikar #Rajasthan #सीकर #BreakingNews"
            )
            
            try:
                if art['image']:
                    await bot.send_photo(CH_ID, art['image'], caption=msg[:1024], parse_mode=ParseMode.MARKDOWN)
                else:
                    await bot.send_message(CH_ID, msg, parse_mode=ParseMode.MARKDOWN)
                
                # Update history after successful post
                history.append(art['url'])
                history_set.add(art['url'])
                print(f"✅ Posted news from: {art['source']}")
                await asyncio.sleep(5) # Anti-flood delay
            except Exception as e:
                print(f"❌ Telegram Error: {e}")
        
        # 3. Final save to local file
        save_history(history)

if __name__ == "__main__":
    if not TG_TOKEN or not CH_ID:
        print("❌ ERROR: Missing TG_TOKEN or CH_ID secrets!")
    else:
        asyncio.run(main())
