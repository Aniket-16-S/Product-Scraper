# ⚡ AI-Powered Multi-Platform Product Search

> **Compare products from Amazon, Flipkart, Myntra, and Meesho in seconds.**  
> *Built for speed, stealth, and scalability.*

---

## 🚀 Overview

This project is a high-performance, asynchronous web-scraping engine. It scrapes multiple e-commerce platforms in parallel using **Playwright** (browser automation) and serves results via a **FastAPI** backend. 

Designed for developers who need robust data extraction without the headache of managing proxies, captchas, or basic DOM parsing.

---
<p align=left >
<img src="https://github.com/Aniket-16-S/ML-Models-Automation/blob/606a3321633631c7c0b6971cd849889c42f1e994/Models/Mediafiles_other_projects/ps/Screenshot%202025-12-09%20163944.png" width=45% > 
&nbsp; &nbsp;
<img src="https://github.com/Aniket-16-S/ML-Models-Automation/blob/aec1b12e0c6c6524ff0723407e33c40538a47418/Models/Mediafiles_other_projects/ps/Screenshot%202025-12-09%20163920.png" width=45%> 
  </p>
<img src="https://github.com/Aniket-16-S/ML-Models-Automation/blob/aec1b12e0c6c6524ff0723407e33c40538a47418/Models/Mediafiles_other_projects/ps/Screenshot%202025-12-09%20164045.png" width=90%>


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
| **Scraping** | Playwright, BS4, selenium, Aiohttp |
| **Database** | aiosqlite3  |
| **ML/NLP** | Sentence-Transformers |
| **Frontend** | HTML5, CSS3, JavaScript |

---

## ⚡ Quick Start

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
