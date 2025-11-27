import sys
import asyncio
import os
import uuid
# MAJOR FIX: Enforce ProactorEventLoop on Windows for Playwright compatibility
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, List
import main_scraper
import cache_manager
from cache_manager import query_processor as nqp

app = FastAPI(
    title="Product Scraper API",
    description="""
    ## Welcome to the Product Scraper API
    
    This API allows you to search for products across multiple e-commerce platforms (Amazon, Flipkart, Myntra, Meesho) and retrieve their details.
    
    ### Features
    * **Search**: Unified search across platforms.
    * **Caching**: Intelligent caching with TTL to ensure fresh data.
    * **Admin**: Management endpoints for cache control.
    * **Multi-Device**: Session management and request prioritization.
    """,
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Concurrency Control
# Limit concurrent scraping operations to ensure responsiveness for cached queries
MAX_CONCURRENT_SCRAPES = 3
scrape_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCRAPES)

# Middleware for Session Management
@app.middleware("http")
async def session_middleware(request: Request, call_next):
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
        response = await call_next(request)
        response.set_cookie(key="session_id", value=session_id, httponly=True)
        return response
    return await call_next(request)

# Mount static files
# We will create a 'static' directory for frontend and admin
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount images directory to serve local images
os.makedirs("Amazon", exist_ok=True)
os.makedirs("Flipkart", exist_ok=True)
os.makedirs("Myntra", exist_ok=True)
os.makedirs("Meesho", exist_ok=True)

app.mount("/images/Amazon", StaticFiles(directory="Amazon"), name="amazon_images")
app.mount("/images/Flipkart", StaticFiles(directory="Flipkart"), name="flipkart_images")
app.mount("/images/Myntra", StaticFiles(directory="Myntra"), name="myntra_images")
app.mount("/images/Meesho", StaticFiles(directory="Meesho"), name="meesho_images")


class SearchQuery(BaseModel):
    q: str

class AdminTTL(BaseModel):
    ttl_minutes: int

@app.get("/")
async def read_root():
    return FileResponse("static/index.html")

@app.get("/admin")
async def read_admin():
    return FileResponse("static/admin.html")

@app.get("/api/search")
async def search(q: str, request: Request):
    """
    Search for products.
    1. Check cache (handled by main_scraper logic or direct cache access).
    2. If not in cache or expired, scrape.
    3. Return results.
    """
    if not q:
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")

    session_id = request.cookies.get("session_id")
    print(f"Search request from session: {session_id} for query: {q}")

    # Initialize DB if needed (main_scraper does this, but good to ensure)
    await cache_manager.init_table()

    # Check cache first - HIGH PRIORITY
    # Cached requests bypass the semaphore
    cached_data = await cache_manager.retrieve_query_data(q)
    if cached_data:
        print(f"Cache HIT for '{q}'. Serving immediately.")
        return {"status": "cached", "data": cached_data}

    # If not in cache, scrape - LOWER PRIORITY (Throttled)
    print(f"Cache MISS for '{q}'. Waiting for scrape slot...")
    
    try:
        async with scrape_semaphore:
            print(f"Scrape slot acquired for '{q}'. Starting scrape...")
            results = await main_scraper.search_products(q)
            cached_data = await cache_manager.retrieve_query_data(q)
            return {"status": "scraped", "data": cached_data if cached_data else results}
    except Exception as e:
        print(f"Scraping error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/stats")
async def get_stats():
    stats = await cache_manager.get_all_products_stats()
    return stats

@app.get("/api/admin/products")
async def get_products(limit: int = 100):
    products = await cache_manager.get_all_products(limit)
    return products

@app.post("/api/admin/clear")
async def clear_cache():
    await cache_manager.clear_cache()
    # Clear NLP Index
    nqp.engine.rebuild_index([])
    return {"status": "success", "message": "Cache cleared"}

@app.delete("/api/admin/query")
async def delete_query(q: str):
    if not q:
         raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
    
    await cache_manager.delete_history(q)
    
    # Rebuild NLP Index to ensure sync
    # We fetch all remaining products and rebuild
    all_names = await cache_manager.get_all_product_names()
    
    # Run in executor to avoid blocking
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, nqp.engine.rebuild_index, all_names)
    
    return {"status": "success", "message": f"History for '{q}' deleted and NLP index updated"}

@app.delete("/api/admin/item/{id}")
async def delete_item(id: int):
    await cache_manager.delete_product(id)
    # We should also rebuild here to be safe, though it's expensive for single item delete.
    # Given the user's preference for "batch" or "all", maybe we skip auto-rebuild for single item 
    # or just do it because correctness > performance for now.
    
    all_names = await cache_manager.get_all_product_names()
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, nqp.engine.rebuild_index, all_names)
    
    return {"status": "success", "message": f"Item {id} deleted"}

@app.post("/api/admin/ttl")
async def set_ttl(ttl: AdminTTL, background_tasks: BackgroundTasks):
    background_tasks.add_task(cache_manager.clean_expired_entries, ttl.ttl_minutes)
    return {"status": "success", "message": f"TTL cleanup started for {ttl.ttl_minutes} minutes"}

if __name__ == "__main__":
    import uvicorn
    # Add loop="asyncio" to prevent uvicorn from using incompatible loops
    # Host 0.0.0.0 allows access from other devices on the network
    uvicorn.run("api:app", host="0.0.0.0", port=8000, loop="asyncio")
