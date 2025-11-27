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

async def get_url(Qur=None, p_c=None):
    if Qur is None:
        query = input("Enter what you wanna Search on Amazon : ").strip()
    else:
        query = Qur
    if p_c is None:
        pc = None
    else:
        pc = p_c
    folder = query
    query = query.replace(' ', '+')
    url = f'https://www.amazon.in/s?k={query}'
    return url, pc, folder

async def download_image(session, url, folder):
    try:
        headers = network_manager.get_headers()
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                content = await resp.read()
                os.makedirs(f"Amazon/{folder}", exist_ok=True)
                name = name_url[url]
                filename = f"Amazon/{folder}/{name}"
                with open(filename, "wb") as f:
                    f.write(content)
    except Exception as e:
        logger.error(f"Failed to download image {url}: {e}")

def scrape_amazon_sync(url, pc):
    driver = get_driver(headless=True)
    products_data = []
    try:
        driver.get(url)
        # Reduced wait time
        time.sleep(1.5)

        if pc:
            try:
                # Try to set pincode
                try:
                    driver.find_element(By.ID, "nav-global-location-popover-link").click()
                    time.sleep(1.5)
                    try:
                        pincode_input = driver.find_element(By.ID, "GLUXZipUpdateInput")
                    except:
                        pincode_input = driver.find_element(By.XPATH, "//input[@aria-label='or enter an Indian pincode']")
                    
                    if pincode_input:
                        pincode_input.send_keys(pc)
                        driver.find_element(By.ID, "GLUXZipUpdate").click()
                        time.sleep(5)
                except:
                    pass
            except Exception:
                pass

        # Find products
        products = driver.find_elements(By.CSS_SELECTOR, "div[role='listitem']")
        
        for i, product in enumerate(products):
            try:
                # --- Image Extraction ---
                img_url = None
                try:
                    img = product.find_element(By.TAG_NAME, "img")
                    img_url = img.get_attribute('src')
                    if not img_url:
                        img_url = img.get_attribute('data-src')
                except:
                    pass

                # --- Title & Link Extraction ---
                product_title = []
                product_url = None
                
                try:
                    # Try finding the title recipe section first
                    title_section = product.find_element(By.CSS_SELECTOR, "[data-cy='title-recipe']")
                    h2s = title_section.find_elements(By.TAG_NAME, "h2")
                    product_title = [h2.text for h2 in h2s]
                    try:
                        a_tag = title_section.find_element(By.TAG_NAME, "a")
                        product_url = a_tag.get_attribute('href')
                    except:
                        pass
                except:
                    pass

                # Fallback for Link: Search in the whole product card
                if not product_url:
                    try:
                        # Look for any link with a title or just the first link
                        a_tags = product.find_elements(By.TAG_NAME, "a")
                        for a in a_tags:
                            href = a.get_attribute('href')
                            if href and ("/dp/" in href or "/gp/" in href): # Amazon product links usually contain /dp/ or /gp/
                                product_url = href
                                break
                        if not product_url and a_tags:
                             product_url = a_tags[0].get_attribute('href')
                    except:
                        pass
                
                # Ensure absolute URL
                if product_url and not product_url.startswith('http'):
                    product_url = "https://www.amazon.in" + product_url

                # --- Reviews & Sold ---
                stars = "N/A"
                no_of_reviews = "0"
                sold = ""
                
                try:
                    review_secn = product.find_element(By.CSS_SELECTOR, "[data-cy='reviews-block']")
                    try:
                        stars_el = review_secn.find_element(By.CSS_SELECTOR, ".a-icon-alt")
                        stars = stars_el.get_attribute("textContent").strip()
                    except:
                        pass
                    
                    try:
                        reviews_el = review_secn.find_element(By.CSS_SELECTOR, "[aria-hidden='true']")
                        no_of_reviews = reviews_el.text.strip()
                    except:
                        pass
                    
                    try:
                        sold_el = review_secn.find_element(By.CSS_SELECTOR, ".a-size-base.a-color-secondary")
                        sold = sold_el.text.strip()
                    except:
                        pass
                except:
                    pass

                # --- Price ---
                cp = mrp = discount = ""
                try:
                    price_secn = product.find_element(By.CSS_SELECTOR, "[data-cy='price-recipe']")
                    try:
                        a = price_secn.find_element(By.CSS_SELECTOR, "[aria-describedby='price-link']")
                        try:
                            cp_el = a.find_element(By.CSS_SELECTOR, ".a-price-whole")
                            cp = cp_el.text.strip()
                        except:
                            pass
                        mrp = a.get_attribute("aria-hidden") or ""
                    except:
                        pass
                    
                    try:
                        discount_el = price_secn.find_element(By.CSS_SELECTOR, "div.a-row > span:last-of-type")
                        discount = discount_el.text.strip()
                    except:
                        pass
                except:
                    pass

                # --- Delivery ---
                final_d = ""
                stock_status = "In Stock"
                try:
                    delivery_secn = product.find_element(By.CSS_SELECTOR, "[data-cy='delivery-recipe']")
                    final_d = delivery_secn.text.replace('Or', ' Or')
                    if "Currently unavailable" in final_d:
                        stock_status = "Out of Stock"
                except:
                    pass

                name = ' '.join(product_title) if product_title else "N/A"
                if name == "N/A":
                     # Fallback name
                     try:
                         name = product.find_element(By.TAG_NAME, "h2").text
                     except:
                         pass

                info = {
                    "Name": name,
                    "product_link": product_url,
                    "review": f"Rating: {stars}, Count: {no_of_reviews}, Sold: {sold}",
                    "price": f"{cp} (MRP: {mrp}, Off: {discount})",
                    "delivery": final_d,
                    "stock": stock_status,
                    "specs": "N/A", 
                    "index" : i,
                    "img_url": img_url
                }
                
                if name != "N/A" and name != "":
                    products_data.append(info)

            except Exception:
                continue
                
    except Exception as e:
        print(f"Error processing Amazon content: {e}")
    finally:
        driver.quit()
        
    return products_data

async def process_content(Qur=None, p_c=None, context=None):
    global queue
    url, pc, folder = await get_url(Qur=Qur, p_c=p_c)

    products = await asyncio.to_thread(scrape_amazon_sync, url, pc)

    async with aiohttp.ClientSession() as session:
        for product in products:
            img_url = product.pop("img_url", None)
            if img_url:
                name_url[img_url] = f"product_{product['index']}.jpg" 
                await download_image(session, img_url, folder)
            
            await queue.put(product)

    await queue.put(None)

async def fetch(Query=None, pincode=None, context=None):
    global queue
    queue = asyncio.Queue()
    producer_task = asyncio.create_task(process_content(Qur=Query, p_c=pincode, context=context))

    while True:
        item = await queue.get()
        if item is None:
            break
        yield item
    await producer_task