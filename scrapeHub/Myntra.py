import os
import asyncio
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import aiohttp
from utils.network_manager import network_manager
from utils.browser_manager import get_driver
import logging
from bs4 import BeautifulSoup
import time

logger = logging.getLogger(__name__)

queue = None  
folder = None
url_name = {}

def get_url(Query) -> str:
    global folder
    if Query:
        query = Query
    else:
        query = input("Enter what you wanna Search on Myntra : ").strip()
    folder = query
    query = query.replace(' ', '+')
    return f'https://www.myntra.com/{query}?rawQuery={query}'

async def download_image(session, url):
    try:
        headers = network_manager.get_headers()
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                os.makedirs(f"Myntra/{folder}", exist_ok=True)
                name = url_name[url]
                filename = f"Myntra/{folder}/{name}"
                with open(filename, "wb") as f:
                    f.write(await response.read())
    except Exception as e:
        logger.error(f"Failed to download image {url}: {e}")

def fix_myntra_url(raw_url):
    if not raw_url:
        return None
    
    # Clean up whitespace
    clean_url = raw_url.strip()
    
    # If it's already a full valid URL, return it
    if clean_url.startswith("http"):
        return clean_url
        
    # The missing prefix based on your error description
    # This matches the Myntra standard format
    base_prefix = "https://assets.myntassets.com/f_webp,dpr_2.8,q_60,w_210,c_limit,"
    
    # If the scraped URL starts with 'fl_progressive', join it with base
    if clean_url.startswith("fl_progressive") or clean_url.startswith("assets"):
        # Ensure we don't have double slashes if the raw_url starts with /
        if clean_url.startswith("/"):
            clean_url = clean_url[1:]
        return base_prefix + clean_url
        
    return clean_url


def scrape_myntra_sync(url):
    driver = get_driver(headless=True)
    products_data = []
    try:
        driver.get(url)
        # Scroll to load more products
        viewport_height = driver.execute_script("return window.innerHeight;")

        # Get total scroll height
        last_height = driver.execute_script("return document.body.scrollHeight")
        current_scroll = 0
        while True:
            # Scroll down by one viewport height
            driver.execute_script(f"window.scrollBy(0, {viewport_height});")
            
            # Wait for images to load (lazy load trigger)
            # 0.5s is fast, but usually enough for the request to fire
            time.sleep(0.5) 
            
            # Update current scroll position
            current_scroll += viewport_height
            
            # Check if we have reached the bottom
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            # Break if we are past the bottom or height hasn't changed (end of page)
            if current_scroll >= new_height:
                # One final check to see if content grew (infinite scroll)
                if new_height == last_height:
                    break
                last_height = new_height

        # Give one final second for the last batch to render
        time.sleep(1)
            
        # Get static HTML
        content = driver.page_source
        soup = BeautifulSoup(content, 'html.parser')
        
        product_list = soup.find_all("li", class_="product-base")
        #print(f"Myntra: Found {len(product_list)} products via BeautifulSoup")
          
        for i, product in enumerate(product_list):
            try:
                # Link
                p_link = None
                a_tag = product.find("a", href=True)
                if a_tag:
                    p_link = a_tag['href']
                    if p_link and not p_link.startswith("http"):
                         p_link = "https://www.myntra.com/" + p_link

                # Image
                img_link = None
                try:
                    # 1. Try picture > source (srcset) - Primary method based on user snippet
                    picture = product.find("picture")
                    if picture:
                        # Try to find source with srcset
                        sources = picture.find_all("source")
                        for source in sources:
                            srcset = source.get("srcset")
                            if srcset:
                                # User snippet shows: url1, \n url2 1.5x, ...
                                # We want to split by comma, then clean up each part
                                parts = [p.strip() for p in srcset.split(',') if p.strip()]
                                if parts:
                                    # Get the last one (highest res)
                                    best_candidate = parts[-1]
                                    # Remove the size descriptor (e.g., " 2.8x")
                                    raw_img_url = best_candidate.split(' ')[0]
                                    img_link = fix_myntra_url(raw_img_url)
                                    if img_link:
                                        break
                        
                        # 2. Try picture > img (src) if source failed
                        if not img_link:
                            img = picture.find("img")
                            if img:
                                img_link = img.get("src")

                    # 3. Fallback to any img tag in the product card
                    if not img_link:
                        img_tag = product.find("img")
                        if img_tag:
                            raw_src = img_tag.get("src") or img_tag.get("data-src")
                            img_link = fix_myntra_url(raw_src)
                except:
                    pass

                # Info
                title = ""
                rating = "N/A"
                rating_count = ""
                price_unformatted = ""
                
                try:
                    p_info = product.select_one("div.product-productMetaInfo")
                    if p_info:
                        h3 = p_info.find("h3")
                        h4 = p_info.find("h4")
                        brand = h3.text.strip() if h3 else ""
                        name = h4.text.strip() if h4 else ""
                        title = f"{brand} {name}".strip()
                        
                        ratings_container = p_info.select_one("div.product-ratingsContainer")
                        if ratings_container:
                            rating_span = ratings_container.find("span")
                            if rating_span: rating = rating_span.text.strip()
                            count_div = ratings_container.select_one("div.product-ratingsCount")
                            if count_div: rating_count = count_div.text.strip()
                        
                        price_tag = p_info.select_one("div.product-price")
                        if price_tag:
                            price_unformatted = price_tag.text.strip()
                except:
                    pass

                stock_status = "In Stock"

                info = {
                    "Name": f"title : {title}",
                    "product_link": p_link,
                    "review" : f"Rating: {rating}, Count: {rating_count}",
                    "price": f"price : {price_unformatted}",
                    "delivery" : None,
                    "stock": stock_status,
                    "specs": "N/A",
                    "index" : i,
                    "img_link": img_link
                }
                products_data.append(info)
            except Exception as e:
                # print(f"Error parsing product: {e}")
                continue
                
    except Exception as e:
        print(f"Error processing Myntra content: {e}")
    finally:
        driver.quit()
        
    return products_data

async def process_content(url=None, Query=None, context=None):
    # Context is ignored in Selenium refactor as we manage driver internally or pass it differently.
    # For compatibility with main_scraper, we keep the signature but don't use context.
    if url is None:
        url = get_url(Query)

    # Run blocking Selenium code in a thread
    products = await asyncio.to_thread(scrape_myntra_sync, url)

    async with aiohttp.ClientSession() as session:
        for product in products:
            img_link = product.pop("img_link", None)
            if img_link:
                url_name[img_link] = f"product_{product['index']}.jpg"
                # Fire and forget download or await it? 
                # Original awaited it inside the loop.
                await download_image(session, img_link)
            
            await queue.put(product)

    await queue.put(None)


async def fetch(Query=None, context=None):
    global queue
    queue = asyncio.Queue()
    producer_task = asyncio.create_task(process_content(Query=Query, context=context))
    while True:
        item = await queue.get()
        if item is None:
            break
        yield item
    await producer_task

if __name__ == "__main__":
    async def main():
        async for item in fetch("shoes"):
            print(item)

    asyncio.run(main())
