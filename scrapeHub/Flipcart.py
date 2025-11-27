import asyncio
import aiohttp
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import json
from utils.network_manager import network_manager
from utils.browser_manager import get_driver
import logging

logger = logging.getLogger(__name__)

queue = None  
folder = None
url_name = {}

def get_url(Qur=None):
    global folder
    if Qur is None:
        query = input("Enter what you wanna Search on Flipkart: ").strip()
    else:
        query = Qur
    folder = query
    query = query.replace(' ', '+')
    return f'https://www.flipkart.com/search?q={query}'

def safe_eval(func):
    try:
        return func()
    except Exception:
        return "N/A"

async def download_image(session, img_url):
    if img_url == "N/A":
        return
    try:
        headers = network_manager.get_headers()
        async with session.get(img_url, headers=headers) as response:
            if response.status == 200:
                os.makedirs(f"Flipkart/{folder}", exist_ok=True)
                name = url_name[img_url]
                filename = f"Flipkart/{folder}/{name}"
                with open(filename, "wb") as f:
                    f.write(await response.read())
    except Exception as e:
        logger.error(f"Failed to download image {img_url}: {e}")

def scrape_flipkart_sync(url):
    driver = get_driver(headless=True)
    products_data = []
    try:
        driver.get(url)
        # Scroll to load more
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        import time
        import time
        time.sleep(1.5)
        
        content = driver.page_source
        soup = BeautifulSoup(content, 'html.parser')
        
        # Selectors for product container
        product_list = soup.find_all('div', {'class': "slAVV4"})
        if not product_list:
             product_list = soup.find_all('div', {'class': "_1sdMkc LFEi7Z"}) # Fallback

        for i, product in enumerate(product_list):
            try:
                # Try multiple selectors for the link
                p_link = "N/A"
                
                # 1. Try the main container anchor (common in grid view)
                if p_link == "N/A":
                    p_link = safe_eval(lambda: product.find('a', {'class': 'rPDeLR'})['href'])
                
                # 2. Try the title anchor
                if p_link == "N/A":
                    p_link = safe_eval(lambda: product.find('a', {'class': 'WKTcLC'})['href'])
                
                # 3. Try the old class
                if p_link == "N/A":
                    p_link = safe_eval(lambda: product.find('a', {'class': 'VJA3rP'})['href'])

                if p_link == "N/A":
                     # Fallback: find any 'a' tag with href
                     p_link = safe_eval(lambda: product.find('a')['href'])

                img_link = safe_eval(lambda: product.find('img', {'class': 'DByuf4'})['src'])
                if img_link == "N/A":
                     img_link = safe_eval(lambda: product.find('img', {'class': '_53J4C-'})['src'])

                p_company = safe_eval(lambda: product.find('div', {'class': 'syl9yP'}).text)
                p_name = safe_eval(lambda: product.find('a', {'class': 'WKTcLC'}).get_text())
                
                rating = safe_eval(lambda: product.find('div', {'class': 'XQDdHH'}).get_text())
                rating_count = safe_eval(lambda: product.find('span', {'class': 'Wphh3N'}).get_text())

                price = safe_eval(lambda: product.find('div', {'class': 'Nx9bqj'}).get_text())
                o_price = safe_eval(lambda: product.find('div', {'class': 'yRaY8j'}).get_text())
                dcount = safe_eval(lambda: product.find('div', {'class': 'UkUFwK'}).get_text())

                delv = "N/A"
                
                stock_status = "In Stock"
                if price == "N/A":
                    stock_status = "Out of Stock"

                full_link = f"https://www.flipkart.com{p_link}" if p_link != "N/A" else None

                info = {
                    "Name": f"{p_company} {p_name}",
                    "product_link": full_link,
                    "review" : f"Rating: {rating}, Count: {rating_count}",
                    "price": f"{price} ( {o_price} with {dcount})",
                    "delivery" : f"{delv}",
                    "stock": stock_status,
                    "specs": "N/A",
                    "index" : i,
                    "img_link": img_link
                }
                products_data.append(info)
            except Exception:
                continue
    except Exception as e:
        print(f"Error processing Flipkart content: {e}")
    finally:
        driver.quit()
        
    return products_data

async def process_content(Qur=None, context=None):
    global queue
    url = get_url(Qur)
    
    products = await asyncio.to_thread(scrape_flipkart_sync, url)

    async with aiohttp.ClientSession() as session:
        for product in products:
            img_link = product.pop("img_link", None)
            if img_link and img_link != "N/A":
                url_name[img_link] = f"product_{product['index']}.jpg"
                await download_image(session, img_link)
            
            await queue.put(product)

    await queue.put(None)

async def fetch(Query=None, context=None):
    global queue
    queue = asyncio.Queue()
    producer_task = asyncio.create_task(process_content(Qur=Query, context=context))
    while True:
        item = await queue.get()
        if item is None:
            break
        yield item
    await producer_task

if __name__ == '__main__':
    async def main():
        async for item in fetch("iphone"):
            print(item)

    asyncio.run(main())
