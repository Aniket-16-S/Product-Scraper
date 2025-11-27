import aiosqlite
import aiofiles
import os
from datetime import datetime

DB_NAME = "product_cache.db"


async def init_table():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS product_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT,
                source TEXT,
                name TEXT,
                link TEXT,
                price TEXT,
                delivery TEXT,
                rating TEXT,
                image BLOB,
                timestamp TEXT,
                p_index INT
            )
        ''')
        await db.commit()


async def store_query_data(query, source, item):
    timestamp = datetime.utcnow().isoformat()

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO product_cache (query, source, name, link, price, delivery, rating, image, timestamp, p_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            query,
            source,
            item.get("Name", "Unknown Product"),
            item.get("product_link", "N/A"),
            item.get("price", "N/A"),
            item.get("delivery", "N/A"),
            item.get("review", "N/A"),
            None,
            timestamp,
            item.get("index", -1)
        ))
        await db.commit()


async def cache_images(query):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT DISTINCT source FROM product_cache WHERE query = ?", (query,)) as cursor:
            srcs = [row[0] async for row in cursor]

        for src in srcs:
            async with db.execute("SELECT id, p_index FROM product_cache WHERE source = ? AND query = ?", (src, query)) as cursor:
                rows = [row async for row in cursor]

            for row_id, index in rows:
                img_path = os.path.join(src, query, f"product_{index}.jpg")
                if not os.path.exists(img_path):
                    print(f"Image not found at: {img_path}")
                    continue

                try:
                    async with aiofiles.open(img_path, "rb") as f:
                        img_blob = await f.read()
                    await db.execute("UPDATE product_cache SET image = ? WHERE id = ?", (img_blob, row_id))
                except Exception as e:
                    print(f"Failed to read/save image: {e}")

        await db.commit()


async def retrieve_query_data(query):
    """
    Retrieves cached data for a query.
    Returns a list of dictionaries if found, else None.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        # Check if we have any data for this query
        async with db.execute("SELECT DISTINCT source FROM product_cache WHERE query = ?", (query,)) as cursor:
            sources = [row[0] async for row in cursor]

        if not sources:
            return None

        all_products = []
        
        # Check age of the first entry found to determine if we should invalidate
        # (Assuming all entries for a query are inserted roughly at the same time)
        async with db.execute("SELECT timestamp FROM product_cache WHERE query = ? LIMIT 1", (query,)) as cursor:
            row = await cursor.fetchone()
            if row:
                timestamp = row[0]
                age = (datetime.utcnow() - datetime.fromisoformat(timestamp)).total_seconds() / 60
                # Default TTL check here, though we will also have a background cleaner
                # Let's say default 48 hours (2880 mins) as per original code
                if age > 2880:
                    await db.execute("DELETE FROM product_cache WHERE query = ?", (query,))
                    await db.commit()
                    return None

        for src in sources:
            async with db.execute('''
                SELECT id, name, link, price, delivery, rating, image, timestamp, p_index
                FROM product_cache
                WHERE query = ? AND source = ?
            ''', (query, src)) as cursor:
                rows = [row async for row in cursor]

            for row_id, name, link, price, delivery, rating, img_blob, timestamp, index in rows:
                product = {
                    "id": row_id,
                    "source": src,
                    "name": name,
                    "product_link": link,
                    "price": price,
                    "delivery": delivery,
                    "rating": rating,
                    "image_url": f"/images/{src}/{query}/product_{index}.jpg", # Constructing a path for the API to serve
                    "timestamp": timestamp
                }
                all_products.append(product)

    return all_products

async def clean_expired_entries(ttl_minutes: int):
    """
    Deletes entries older than ttl_minutes.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        cutoff_time = datetime.utcnow().timestamp() - (ttl_minutes * 60)
        
        async with db.execute("SELECT id, timestamp FROM product_cache") as cursor:
            rows = [row async for row in cursor]
            
        ids_to_delete = []
        for row_id, ts in rows:
            try:
                entry_time = datetime.fromisoformat(ts).timestamp()
                if entry_time < cutoff_time:
                    ids_to_delete.append(row_id)
            except:
                pass 
                
        if ids_to_delete:
            chunk_size = 900
            for i in range(0, len(ids_to_delete), chunk_size):
                chunk = ids_to_delete[i:i + chunk_size]
                placeholders = ','.join(['?'] * len(chunk))
                await db.execute(f"DELETE FROM product_cache WHERE id IN ({placeholders})", chunk)
            
            await db.commit()
            return len(ids_to_delete)
    return 0

async def get_all_products_stats():
    """
    Returns stats for admin panel.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*), COUNT(DISTINCT query) FROM product_cache") as cursor:
            row = await cursor.fetchone()
            total_items = row[0]
            total_queries = row[1]
            
        db_size = os.path.getsize(DB_NAME) if os.path.exists(DB_NAME) else 0
        
    return {
        "total_items": total_items,
        "total_queries": total_queries,
        "db_size_bytes": db_size
    }

async def get_all_products(limit=100):
    """
    Returns a list of products for admin view.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id, query, source, name, timestamp FROM product_cache ORDER BY id DESC LIMIT ?", (limit,)) as cursor:
            rows = [row async for row in cursor]
            
    return [
        {"id": r[0], "query": r[1], "source": r[2], "name": r[3], "timestamp": r[4]} 
        for r in rows
    ]

async def delete_product(product_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM product_cache WHERE id = ?", (product_id,))
        await db.commit()
import aiosqlite
import aiofiles
import os
from datetime import datetime

DB_NAME = "product_cache.db"


async def init_table():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS product_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT,
                source TEXT,
                name TEXT,
                link TEXT,
                price TEXT,
                delivery TEXT,
                rating TEXT,
                image BLOB,
                timestamp TEXT,
                p_index INT
            )
        ''')
        await db.commit()


async def store_query_data(query, source, item):
    timestamp = datetime.utcnow().isoformat()

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO product_cache (query, source, name, link, price, delivery, rating, image, timestamp, p_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            query,
            source,
            item.get("Name", "Unknown Product"),
            item.get("product_link", "N/A"),
            item.get("price", "N/A"),
            item.get("delivery", "N/A"),
            item.get("review", "N/A"),
            None,
            timestamp,
            item.get("index", -1)
        ))
        await db.commit()


async def cache_images(query):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT DISTINCT source FROM product_cache WHERE query = ?", (query,)) as cursor:
            srcs = [row[0] async for row in cursor]

        for src in srcs:
            async with db.execute("SELECT id, p_index FROM product_cache WHERE source = ? AND query = ?", (src, query)) as cursor:
                rows = [row async for row in cursor]

            for row_id, index in rows:
                img_path = os.path.join(src, query, f"product_{index}.jpg")
                if not os.path.exists(img_path):
                    print(f"Image not found at: {img_path}")
                    continue

                try:
                    async with aiofiles.open(img_path, "rb") as f:
                        img_blob = await f.read()
                    await db.execute("UPDATE product_cache SET image = ? WHERE id = ?", (img_blob, row_id))
                except Exception as e:
                    print(f"Failed to read/save image: {e}")

        await db.commit()


async def retrieve_query_data(query):
    """
    Retrieves cached data for a query.
    Returns a list of dictionaries if found, else None.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        # Check if we have any data for this query
        async with db.execute("SELECT DISTINCT source FROM product_cache WHERE query = ?", (query,)) as cursor:
            sources = [row[0] async for row in cursor]

        if not sources:
            return None

        all_products = []
        
        # Check age of the first entry found to determine if we should invalidate
        # (Assuming all entries for a query are inserted roughly at the same time)
        async with db.execute("SELECT timestamp FROM product_cache WHERE query = ? LIMIT 1", (query,)) as cursor:
            row = await cursor.fetchone()
            if row:
                timestamp = row[0]
                age = (datetime.utcnow() - datetime.fromisoformat(timestamp)).total_seconds() / 60
                # Default TTL check here, though we will also have a background cleaner
                # Let's say default 48 hours (2880 mins) as per original code
                if age > 2880:
                    await db.execute("DELETE FROM product_cache WHERE query = ?", (query,))
                    await db.commit()
                    return None

        for src in sources:
            async with db.execute('''
                SELECT id, name, link, price, delivery, rating, image, timestamp, p_index
                FROM product_cache
                WHERE query = ? AND source = ?
            ''', (query, src)) as cursor:
                rows = [row async for row in cursor]

            for row_id, name, link, price, delivery, rating, img_blob, timestamp, index in rows:
                product = {
                    "id": row_id,
                    "source": src,
                    "name": name,
                    "product_link": link,
                    "price": price,
                    "delivery": delivery,
                    "rating": rating,
                    "image_url": f"/images/{src}/{query}/product_{index}.jpg", # Constructing a path for the API to serve
                    "timestamp": timestamp
                }
                all_products.append(product)

    return all_products

async def clean_expired_entries(ttl_minutes: int):
    """
    Deletes entries older than ttl_minutes.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        cutoff_time = datetime.utcnow().timestamp() - (ttl_minutes * 60)
        
        async with db.execute("SELECT id, timestamp FROM product_cache") as cursor:
            rows = [row async for row in cursor]
            
        ids_to_delete = []
        for row_id, ts in rows:
            try:
                entry_time = datetime.fromisoformat(ts).timestamp()
                if entry_time < cutoff_time:
                    ids_to_delete.append(row_id)
            except:
                pass 
                
        if ids_to_delete:
            chunk_size = 900
            for i in range(0, len(ids_to_delete), chunk_size):
                chunk = ids_to_delete[i:i + chunk_size]
                placeholders = ','.join(['?'] * len(chunk))
                await db.execute(f"DELETE FROM product_cache WHERE id IN ({placeholders})", chunk)
            
            await db.commit()
            return len(ids_to_delete)
    return 0

async def get_all_products_stats():
    """
    Returns stats for admin panel.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*), COUNT(DISTINCT query) FROM product_cache") as cursor:
            row = await cursor.fetchone()
            total_items = row[0]
            total_queries = row[1]
            
        db_size = os.path.getsize(DB_NAME) if os.path.exists(DB_NAME) else 0
        
    return {
        "total_items": total_items,
        "total_queries": total_queries,
        "db_size_bytes": db_size
    }

async def get_all_products(limit=100):
    """
    Returns a list of products for admin view.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id, query, source, name, timestamp FROM product_cache ORDER BY id DESC LIMIT ?", (limit,)) as cursor:
            rows = [row async for row in cursor]
            
    return [
        {"id": r[0], "query": r[1], "source": r[2], "name": r[3], "timestamp": r[4]} 
        for r in rows
    ]

async def delete_product(product_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM product_cache WHERE id = ?", (product_id,))
        await db.commit()

async def clear_cache():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM product_cache")
        await db.commit()

async def delete_history(query) :
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("DELETE FROM product_cache WHERE query = ?", (query,))
        await db.commit()

async def get_all_product_names():
    """
    Retrieves all product names from the database.
    Used for rebuilding the NLP index.
    """
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT name FROM product_cache") as cursor:
            rows = [row[0] async for row in cursor]
    return rows