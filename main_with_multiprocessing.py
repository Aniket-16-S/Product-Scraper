import asyncio
import time
import multiprocessing as mp
import Myntra as m
import Amazon as a
import Flipcart as f
from playwright.async_api import async_playwright

## Using Multiprocessing so each scraping library has its own instance & dedicated core
## ON testing though did not show any improvements in performance. infact lags by 4 to 5 secs.
## might be due to overhead of creating new instace of py compiler. 
## if you are on unix / linux please try fork / forkserver instead of spawn in main to check for any improvements in performance.

def create_browser_info():
    return {
        "Myntra": ("webkit", []),
        "Amazon": ("chromium", []),
        "Flipkart": ("chromium", []),
    }

def scraper_process(source_name, fetch_func, query, result_queue, browser_info):
    async def run_scraper():
        async with async_playwright() as p:
            browser_type, args = browser_info[source_name]
            browser = await getattr(p, browser_type).launch(headless=True, args=args)
            context = await browser.new_context()

            gen = fetch_func(Query=query, context=context)

            async for item in gen:
                if item:
                    result_queue.put((source_name, item))

            result_queue.put((source_name, None))
            await browser.close()

    asyncio.run(run_scraper())

def collector_process(result_queue, print_lock, total_sources):
    total_done = 0
    product_count = 0

    while total_done < total_sources:
        source, item = result_queue.get()
        if item is None:
            total_done += 1
            continue

        product_count += 1
        with print_lock:
            print(f"\n===== Product {product_count} -- {source} =====")
            for k, v in item.items():
                print(f"{k} : {v}")
            print("\n")

    return product_count

def main():
    browser_info = create_browser_info()

    query = input("Search for : ").strip()
    t0 = time.time()

    result_queue = mp.Queue()
    print_lock = mp.Lock()

    sources = [
        ("Myntra", m.fetch),
        ("Amazon", a.fetch),
        ("Flipkart", f.fetch),
    ]

    processes = []
    for name, fetch_func in sources:
        p = mp.Process(target=scraper_process, args=(name, fetch_func, query, result_queue, browser_info))
        p.start()
        processes.append(p)

    total_products = collector_process(result_queue, print_lock, total_sources=len(sources))

    for p in processes:
        p.join()

    dt = time.time() - t0
    print(f"\nDone in {dt:.4f}s — Total products scraped: {total_products}")

if __name__ == "__main__":
    mp.set_start_method("spawn")
    main()
