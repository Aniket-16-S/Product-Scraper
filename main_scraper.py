import asyncio, time
import scrapeHub.Myntra as m
import scrapeHub.Amazon as a
import scrapeHub.Flipcart as f
import cache_manager as cache
from cache_manager import query_processor as nqp


import scrapeHub.Meesho as meesho

async def collect_to_queue(source_name, gen, queue):
    async for item in gen:
        if item:
            await queue.put((source_name, item))

    await queue.put((source_name, None))

async def collect_results(sources, query):
    queue = asyncio.Queue()
    total_done = 0
    total_sources = len(sources)
    products = []

    tasks = [asyncio.create_task(collect_to_queue(name, gen, queue)) for name, gen in sources]

    while total_done < total_sources:
        source, item = await queue.get()
        if item is None:
            total_done += 1
            continue

        # Add source to item if not present
        if isinstance(item, dict):
            item['source'] = source
            products.append(item)
            await cache.store_query_data(query, source, item)

    await asyncio.gather(*tasks)
    await cache.cache_images(query)
    return products

async def search_products(query: str):
    """
    Main entry point for searching products.
    Returns a dictionary with status and data.
    """
    await cache.init_table()
    
    # NLP Check
    # Use the engine instance from the module
    q, is_present = nqp.engine.search(query)
    
    # Fallback if NLP returns None (should not happen with latest fix, but safe to have)
    if not q:
        q = query
        
    if is_present:
        # For API, we might want to return cached data automatically
        # For now, let's just return the cached data if it's a "good" match
        # We need a way to get data from cache without printing
        # cache.retrieve_query_data prints. We might need to refactor cache_manager too or just scrape if not strict.
        # Let's assume we scrape for now if not exact match, or we can implement a fetch_from_cache later.
        # For this refactor, I'll focus on the scraping part.
        pass

    # No Playwright context needed anymore
    
    sources = [
        ("Myntra", m.fetch(Query=q)),
        ("Amazon", a.fetch(Query=q)),
        ("Flipkart", f.fetch(Query=q)),
        ("Meesho", meesho.fetch(Query=q)),
    ]

    results = await collect_results(sources, query=query)
    
    # Update NLP Engine with new products
    if results:
        product_names = [p.get('name') for p in results if p.get('name')]
        # Run in executor to avoid blocking async loop with heavy CPU work
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, nqp.engine.add_products, product_names)
    
    return results

async def main():
    query = input("Search for : ").strip()
    t0 = time.time()
    
    # We can use the new function, but for CLI we might want the old printing behavior.
    # For now, let's just print the results from the new function.
    results = await search_products(query)
    
    for p in results:
        print(f"\n===== Product -- {p.get('source')} =====")
        for k, v in p.items():
            print(f"    {k} : {v}")
    
    dt = time.time() - t0
    print(f"\nDone in {dt:.4f}s — Total products scraped: {len(results)}")

if __name__ == "__main__":
    asyncio.run(main())
