import random
import asyncio
import logging
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NetworkManager:
    def __init__(self, proxy_file="proxies.txt", strict_mode=True):
        self.ua = UserAgent()
        self.strict_mode = strict_mode  # If True, stops script rather than leaking IP
        self.proxies = self._load_proxies(proxy_file)
        self.current_proxy_index = 0

    def _load_proxies(self, proxy_file):
        """Loads proxies from file. If empty, tries to fetch free ones from web."""
        proxies = []
        try:
            with open(proxy_file, "r") as f:
                proxies = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            logger.warning(f"File '{proxy_file}' not found.")

        # If file failed or was empty, try to fetch fresh ones
        if not proxies:
            logger.info("Proxy list empty. Attempting to fetch free proxies from web...")
            proxies = self._fetch_free_proxies_sync()
        
        if not proxies:
            if self.strict_mode:
                raise RuntimeError("CRITICAL: No proxies available! Stopping to prevent IP leak.")
            else:
                logger.warning("Running WITHOUT proxies. Your IP is visible.")
                return []
        
        logger.info(f"Loaded {len(proxies)} proxies.")
        return proxies

    def _fetch_free_proxies_sync(self):
        """
        Quick hack to get free proxies (http/https) to populate the list.
        Uses requests (blocking) for simplicity during init.
        """
        import requests
        try:
            # This is a public list of free proxies
            url = "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return [line.strip() for line in response.text.splitlines() if line.strip()]
        except Exception as e:
            logger.error(f"Failed to fetch free proxies: {e}")
        return []

    def get_proxy(self):
        """Returns the next proxy or raises error in strict mode."""
        if not self.proxies:
            if self.strict_mode:
                raise RuntimeError("No proxies available.")
            return None
        
        proxy = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        
        # Ensure proxy has scheme (aiohttp needs http://)
        if not proxy.startswith("http"):
            return f"http://{proxy}"
        return proxy

    async def verify_ip(self):
        """Test function to see which IP is being used."""
        test_url = "http://httpbin.org/ip"
        proxy = self.get_proxy()
        
        try:
            async with aiohttp.ClientSession() as session:
                logger.info(f"Testing with proxy: {proxy}")
                async with session.get(test_url, proxy=proxy, timeout=5) as resp:
                    data = await resp.json()
                    logger.info(f"SUCCESS! The server sees this IP: {data['origin']}")
        except Exception as e:
            logger.error(f"Proxy failed: {e}")

    def get_headers(self):
        """Returns a random User-Agent header."""
        return {
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

# Singleton instance for import
network_manager = NetworkManager(strict_mode=False)

# Usage Example
async def main():
    # strict_mode=True ensures we crash instead of leaking IP
    # We use a local instance for testing here
    nm = NetworkManager(strict_mode=True)
    
    # Verify it works
    await nm.verify_ip()

if __name__ == "__main__":
    asyncio.run(main())