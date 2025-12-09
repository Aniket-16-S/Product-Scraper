# ⚡ UniScrape: AI-Powered Multi-Platform Product Search

> **Compare products from Amazon, Flipkart, Myntra, and Meesho in milliseconds.**  
> *Built for speed, stealth, and scalability.*

---

## 🚀 Overview

**UniScrape** is a high-performance, asynchronous product aggregation engine. It scrapes multiple e-commerce platforms in parallel using **Playwright** (browser automation), processes data with **Natural Language Processing (NLP)**, and serves results via a **FastAPI** backend. 

Designed for developers who need robust data extraction without the headache of managing proxies, captchas, or basic DOM parsing.

---

## ✨ Key Features

### 🧠 Intelligent Core
- **NLP-Powered Search**: Uses `all-MiniLM-L6-v2` to understand user queries and match products more accurately.
- **Smart Caching**: SQLite-based caching with Time-To-Live (TTL) mechanisms. Cached queries return instantly (<50ms).
- **Session Management**: Handles multiple user sessions with query prioritization.

### 🚄 High-Performance Architecture
- **Async First**: Built on `asyncio` and `aiohttp` for non-blocking operations.
- **Concurrency Control**: Implements Semaphores to manage load and rate limits, preventing IP bans.
- **Stealth Mode**: Uses headless browser behaviors to mimic real users, bypassing standard bot detection.

### 🌐 Universal Coverage
- **Supported Platforms**:
  - 🛒 **Amazon**
  - 🛍️ **Flipkart**
  - 👗 **Myntra**
  - 📦 **Meesho**

### 🎨 Modern UI
- **Responsive Frontend**: Clean, dark-themed interface built with Vanilla JS & CSS.
- **Advanced Filtering**: Filter by price, platform, and sort options.

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | Python 3.10+, FastAPI, Uvicorn |
| **Scraping** | Playwright (Async), Aiohttp |
| **Database** | SQLite3 (Async) |
| **ML/NLP** | Sentence-Transformers (HuggingFace) |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript |

---

## ⚡ Quick Start

### Prerequisites
- Python 3.8+
- Node.js (optional, for frontend dev)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Aniket-16-S/product-Sraper.git
   cd product-Sraper
   ```

2. **Install Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright Browsers**
   ```bash
   playwright install chromium
   ```

### Running the Application

Start the API server (Backend + Frontend served statically):

```bash
python api.py
```

- **Frontend**: Open `http://localhost:8000` in your browser.
- **API Docs**: Explore endpoints at `http://localhost:8000/docs`.

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/search?q={query}` | Search for products across all platforms. |
| `GET` | `/api/admin/stats` | View cache hit rates and stored product counts. |
| `POST` | `/api/admin/clear` | Flush all cached data. |
| `POST` | `/api/admin/ttl` | Set cache Time-To-Live (TTL). |

---

## ⚠️ Legal Disclaimer

This tool is created for **educational and research purposes only**. 
- Respect the `robots.txt` of all target websites.
- Do not use this tool for high-frequency scraping that degrades service for others.
- The authors are not responsible for any misuse of this software.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---
*Crafted with ❤️ by Aniket*
