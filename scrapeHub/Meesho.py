import asyncio
import aiohttp
import os
import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils.network_manager import network_manager
from utils.browser_manager import get_driver
import logging

logger = logging.getLogger(__name__)

queue = None
name_url = {}

async def get_url(Qur=None):
    if Qur is None:
        query = input("Enter what you wanna Search on Meesho : ").strip()
    else:
        query = Qur
    
    folder = query
    query = query.replace(' ', '+')
    url = f'https://www.meesho.com/search?q={query}'
    return url, folder

async def download_image(session, url, folder):
    try:
        headers = network_manager.get_headers()
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                content = await resp.read()
                os.makedirs(f"Meesho/{folder}", exist_ok=True)
                name = name_url[url]
                filename = f"Meesho/{folder}/{name}"
                with open(filename, "wb") as f:
                    f.write(content)
    except Exception as e:
        logger.error(f"Failed to download image {url}: {e}")

def scrape_meesho_sync(url):
    driver = get_driver(headless=True)
    products_data = []
    try:
        driver.get(url)
        time.sleep(2)
        
        # More aggressive scrolling to load all products
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scrolls = 8  # Increase scroll iterations
        
        while scroll_attempts < max_scrolls:
            # Scroll down
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
            
            # Calculate new height
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            # Break if no new content loaded
            if new_height == last_height:
                break
                
            last_height = new_height
            scroll_attempts += 1

        # Try multiple selectors for product cards
        products = []
        selectors = [
            "div[class*='ProductListItem']",
            "div[class*='ProductCard']",
            "div[class*='NewProductCard']", 
            "div[class*='ProductList'] > div",
            "a[href*='/p/']"
        ]
        
        for sel in selectors:
            products = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(products) > 5:
                break
        
        # If still no products, try generic grid items
        if not products:
             products = driver.find_elements(By.XPATH, "//div[contains(@class, 'Card')]")

        print(f"Found {len(products)} potential products on Meesho")

        for i, product in enumerate(products):
            # Removed limit - process all products found
            try:
                # Extract Data
                img_url = None
                try:
                    # Image - try multiple approaches
                    img_url = None
                    
                    # 1. Try finding picture tag first (as per user snippet)
                    try:
                        picture = product.find_element(By.TAG_NAME, "picture")
                        # Try source srcset
                        try:
                            source = picture.find_element(By.TAG_NAME, "source")
                            srcset = source.get_attribute("srcset")
                            if srcset:
                                img_url = srcset.split(',')[0].strip().split(' ')[0]
                        except:
                            pass
                        
                        # Try img src inside picture
                        if not img_url:
                            img = picture.find_element(By.TAG_NAME, "img")
                            img_url = img.get_attribute("src")
                    except:
                        pass

                    # 2. Fallback to finding any img tag
                    if not img_url:
                        imgs = product.find_elements(By.TAG_NAME, "img")
                        for img in imgs:
                            # Check various attributes
                            candidates = [
                                img.get_attribute('src'),
                                img.get_attribute('data-src'),
                                img.get_attribute('data-lazy-src'),
                                img.get_attribute('srcset')
                            ]
                            
                            for cand in candidates:
                                if cand and not cand.startswith('data:') and len(cand) > 20:
                                    if 'srcset' in str(cand) or ',' in str(cand):
                                         img_url = cand.split(',')[0].strip().split(' ')[0]
                                    else:
                                         img_url = cand
                                    break
                            if img_url:
                                break
                except:
                    pass

                # Name
                name = "N/A"
                try:
                    # Try finding p tags or h tags
                    texts = [x.text for x in product.find_elements(By.TAG_NAME, "p") if len(x.text) > 5]
                    if not texts:
                         texts = [x.text for x in product.find_elements(By.TAG_NAME, "span") if len(x.text) > 10]
                    
                    if texts:
                        name = texts[0]  # Assume first long text is name
                    else:
                        name = product.text.split('\n')[0]
                except:
                    pass

                # Price
                price = "N/A"
                mrp = ""
                discount = ""
                try:
                    # Look for ₹ symbol
                    all_text = product.text
                    lines = all_text.split('\n')
                    for line in lines:
                        if '₹' in line:
                            # Check if it's the main price (usually first or largest)
                            if price == "N/A":
                                price = line.strip()
                            else:
                                # Could be MRP
                                mrp = line.strip()
                    
                    # Try to find discount
                    for line in lines:
                        if '% off' in line.lower():
                            discount = line.strip()
                except:
                    pass
                
                # Rating
                rating = "N/A"
                try:
                    # Look for star or number with star
                    rating_el = product.find_element(By.XPATH, ".//*[contains(text(), '★') or contains(@class, 'star')]")
                    rating = rating_el.text.strip()
                except:
                    pass

                # Link
                link = "N/A"
                try:
                    # Check if product itself is an anchor
                    if product.tag_name == 'a':
                        link = product.get_attribute('href')
                    else:
                        # Try to find parent anchor if we are inside one (using XPath)
                        try:
                            parent_a = product.find_element(By.XPATH, "./ancestor-or-self::a")
                            link = parent_a.get_attribute('href')
                        except:
                            # Try finding child anchor
                            try:
                                link_el = product.find_element(By.TAG_NAME, "a")
                                link = link_el.get_attribute('href')
                            except:
                                pass
                            
                    # Ensure absolute URL
                    if link and link != "N/A" and not link.startswith('http'):
                        link = "https://www.meesho.com" + link
                    
                    # If link is still N/A or empty, try to construct it from ID or other attributes if possible
                    # (Meesho usually has links, so this might not be needed if selectors are good)
                except:
                    pass

                info = {
                    "Name": name,
                    "product_link": link,
                    "review": f"Rating: {rating}",
                    "price": f"{price} (MRP: {mrp}, Off: {discount})",
                    "delivery": "Free Delivery",  # Meesho usually free
                    "stock": "In Stock",
                    "specs": "N/A", 
                    "index" : i,
                    "img_url": img_url
                }
                
                if name != "N/A" and price != "N/A":
                    products_data.append(info)

            except Exception as e:
                # print(f"Error parsing product: {e}")
                continue
                
    except Exception as e:
        print(f"Error processing Meesho content: {e}")
    finally:
        driver.quit()
        
    return products_data

async def process_content(Qur=None, context=None):
    global queue
    url, folder = await get_url(Qur=Qur)

    products = await asyncio.to_thread(scrape_meesho_sync, url)

    async with aiohttp.ClientSession() as session:
        for product in products:
            img_url = product.pop("img_url", None)
            if img_url:
                name_url[img_url] = f"product_{product['index']}.jpg" 
                await download_image(session, img_url, folder)
            
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
