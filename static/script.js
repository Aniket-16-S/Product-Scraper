document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('search-btn');
    const productGrid = document.getElementById('product-grid');
    const bottomBar = document.getElementById('bottom-bar');

    // Filter Elements
    const filterBtn = document.getElementById('filter-btn');
    const filterPopup = document.getElementById('filter-popup');
    const closeFilterBtn = document.getElementById('close-filter');
    const applyFiltersBtn = document.getElementById('apply-filters');
    const viewBtns = document.querySelectorAll('.view-btn');
    const sortSelect = document.getElementById('sort-select');
    const minPriceInput = document.getElementById('min-price');
    const maxPriceInput = document.getElementById('max-price');
    const siteCheckboxes = document.querySelectorAll('.site-filters input');

    // State
    let allProducts = [];
    let currentView = 'detailed';
    let lastScrollTop = 0;

    // --- Search Logic ---
    async function performSearch() {
        const query = searchInput.value.trim();
        if (!query) return;

        // Reset
        allProducts = [];
        productGrid.innerHTML = '';

        // --- Loading Animation Logic ---
        const loadingContainer = document.createElement('div');
        loadingContainer.className = 'loading';
        loadingContainer.innerHTML = '<div class="fade-text">Initializing . . .</div>';
        productGrid.appendChild(loadingContainer);

        const fadeText = loadingContainer.querySelector('.fade-text');

        // Message Lists
        const phase1Messages = [
            "Setting up server cores for scraping . . .",
            "Allocating processing threads . . .",
            "Initializing all sites",
            "Deploying scraper agents . . .",
            `Fetching data for ${query} . . .`,
            "Organizing and verifying results"
        ];

        const phase2Messages = [
            "Almost there . . .",
            "Applying finishing touches . . .",
            "Fetching final payload from backend . . .",
            "Packaging results for display . . ."
        ];

        let isResponseReceived = false;
        let animationStartTime = Date.now();
        let messageTimeout = null;

        // Function to update message with fade effect
        function updateMessage(msg) {
            if (!fadeText) return;
            // Fade out
            fadeText.style.opacity = 0;
            setTimeout(() => {
                fadeText.textContent = msg;
                // Fade in
                fadeText.style.opacity = 1;
            }, 600); // Half of 0.8s transition if we did CSS transition, but we use keyframes. 
            // Actually, the keyframe animation handles the pulsing. We just change text.
            // To make it smooth, let's just change text. The pulsing opacity handles the "breath" effect.
            fadeText.textContent = msg;
        }

        // Define this variable OUTSIDE the function so it persists between calls
        let phase1Index = 0;

        function runMessageLoop() {
            if (isResponseReceived) return;

            let currentMsg;
            let minTime, maxTime;

            // Check if we still have messages left in Phase 1
            if (phase1Index < phase1Messages.length) {
                // --- PHASE 1: SEQUENTIAL ---
                currentMsg = phase1Messages[phase1Index];

                // Move the index forward for the next loop
                phase1Index++;

                // Phase 1 timing (faster updates for initial steps)
                minTime = 5500;
                maxTime = 7400;

            } else {
                // --- PHASE 2: RANDOM ---
                // We have exhausted phase 1, so pick randomly from phase 2
                const messages = phase2Messages;
                currentMsg = messages[Math.floor(Math.random() * messages.length)];

                // Phase 2 timing (slower updates for "almost done" feel)
                minTime = 4200;
                maxTime = 7300;
            }

            // Update the message
            updateMessage(currentMsg);

            // Calculate random duration for the NEXT message
            const randomDuration = Math.floor(Math.random() * (maxTime - minTime + 1)) + minTime;

            messageTimeout = setTimeout(runMessageLoop, randomDuration);
        }



        // Start the 1.5s initial wait
        const initialWaitPromise = new Promise(resolve => setTimeout(resolve, 1800));

        // Start message loop after 1.5s if not done
        setTimeout(() => {
            if (!isResponseReceived) {
                runMessageLoop();
            }
        }, 1500);

        try {
            // Fetch Data
            const fetchPromise = fetch(`/api/search?q=${encodeURIComponent(query)}`);

            // Wait for both fetch and initial 1.5s
            const [response] = await Promise.all([fetchPromise, initialWaitPromise]);
            const result = await response.json();

            isResponseReceived = true;
            if (messageTimeout) clearTimeout(messageTimeout);

            if (result.data && result.data.length > 0) {
                allProducts = result.data;
                applyFilters(); // This will render products
            } else {
                productGrid.innerHTML = '<div class="empty-state"><h2>No products found.</h2></div>';
            }
        } catch (error) {
            console.error('Search error:', error);
            isResponseReceived = true;
            if (messageTimeout) clearTimeout(messageTimeout);
            productGrid.innerHTML = '<div class="empty-state"><h2>Something went wrong. Please try again.</h2></div>';
        }
    }

    searchBtn.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performSearch();
    });

    // --- Filter & Sort Logic ---
    function applyFilters() {
        // 1. Filter by Site
        const selectedSites = Array.from(siteCheckboxes)
            .filter(cb => cb.checked)
            .map(cb => cb.value);

        let filtered = allProducts.filter(p => selectedSites.includes(p.source));

        // 2. Filter by Price
        const minPrice = parseFloat(minPriceInput.value) || 0;
        const maxPrice = parseFloat(maxPriceInput.value) || Infinity;

        filtered = filtered.filter(p => {
            const priceVal = parsePrice(p.price).value;
            return priceVal >= minPrice && priceVal <= maxPrice;
        });

        // 3. Sort
        const sortMode = sortSelect.value;
        if (sortMode === 'price-low') {
            filtered.sort((a, b) => parsePrice(a.price).value - parsePrice(b.price).value);
        } else if (sortMode === 'price-high') {
            filtered.sort((a, b) => parsePrice(b.price).value - parsePrice(a.price).value);
        } else if (sortMode === 'random') {
            // Shuffle
            filtered = shuffleArray([...filtered]);
        }

        renderProducts(filtered);
        filterPopup.classList.add('hidden');
    }

    applyFiltersBtn.addEventListener('click', applyFilters);

    // --- Rendering ---
    function renderProducts(products) {
        productGrid.innerHTML = '';

        if (products.length === 0) {
            productGrid.innerHTML = '<div class="empty-state"><h2>No products match your filters.</h2></div>';
            return;
        }

        products.forEach(product => {
            const card = document.createElement('div');
            card.className = `product-card ${currentView}`;

            // Validate productlink
            let productLink = product.product_link || product.link;

            console.log(`Product: ${product.name ? product.name.substring(0, 30) : 'N/A'}...`, `Link: ${productLink}`);

            // Ensure link is valid and absolute
            if (!productLink || productLink === 'null' || productLink === 'N/A' || productLink === 'undefined') {
                productLink = '#';
                console.warn(`Invalid link for: ${product.name}`);
            } else if (!productLink.startsWith('http')) {
                const baseUrls = {
                    'Amazon': 'https://www.amazon.in',
                    'Flipkart': 'https://www.flipkart.com',
                    'Myntra': 'https://www.myntra.com',
                    'Meesho': 'https://www.meesho.com'
                };
                const baseUrl = baseUrls[product.source] || '';
                productLink = baseUrl + productLink;
                console.log(`Fixed relative link to: ${productLink}`);
            }

            // Image
            const imgHtml = product.image_url
                ? `<img src="${product.image_url}" alt="${product.name}" class="product-image" onerror="this.style.display='none'">`
                : '<div class="product-image" style="display:flex;align-items:center;justify-content:center;color:#555;">No Image</div>';

            // Price Parsing
            const priceData = parsePrice(product.price);
            let priceHtml = '';
            if (priceData.display) {
                priceHtml = `
                    <div class="product-price-container">
                        <span class="product-price">${priceData.display}</span>
                        ${priceData.mrp ? `<span class="product-mrp">${priceData.mrp}</span>` : ''}
                        ${priceData.discount ? `<span class="product-discount">${priceData.discount}</span>` : ''}
                    </div>
                `;
            }

            // Meta
            let metaHtml = '';
            if (currentView === 'detailed') {
                const rating = product.review && product.review.includes('Rating:')
                    ? product.review.split(',')[0].replace('Rating:', '').trim()
                    : null;

                if (rating && rating !== 'N/A') {
                    metaHtml += `<span>★ ${rating}</span>`;
                }
                if (product.delivery && product.delivery !== 'N/A') {
                    metaHtml += `<span>${product.delivery}</span>`;
                }
                if (metaHtml) {
                    metaHtml = `<div class="product-meta">${metaHtml}</div>`;
                }
            }

            card.innerHTML = `
                ${imgHtml}
                <div class="product-info">
                    <div class="product-source">${product.source}</div>
                    <a href="${productLink}" target="_blank" rel="noopener noreferrer" class="product-name" title="${product.name}">
                        ${product.name}
                    </a>
                    ${priceHtml}
                    ${metaHtml}
                </div>
            `;

            // Make entire card clickable
            card.style.cursor = 'pointer';
            card.addEventListener('click', (e) => {
                // Don't trigger if clicking the link directly (to avoid double open)
                if (!e.target.closest('a')) {
                    if (productLink && productLink !== '#' && productLink !== 'null' && productLink !== 'N/A') {
                        window.open(productLink, '_blank', 'noopener,noreferrer');
                    }
                }
            });

            productGrid.appendChild(card);
        });
    }

    // --- UI Interactions ---

    // Scroll Hide/Show
    window.addEventListener('scroll', () => {
        const st = window.pageYOffset || document.documentElement.scrollTop;
        if (st > lastScrollTop && st > 100) {
            // Scroll Down
            bottomBar.classList.add('hidden');
        } else {
            // Scroll Up
            bottomBar.classList.remove('hidden');
        }
        lastScrollTop = st <= 0 ? 0 : st;
    });

    // Filter Popup
    filterBtn.addEventListener('click', () => {
        filterPopup.classList.remove('hidden');
    });

    closeFilterBtn.addEventListener('click', () => {
        filterPopup.classList.add('hidden');
    });

    filterPopup.addEventListener('click', (e) => {
        if (e.target === filterPopup) {
            filterPopup.classList.add('hidden');
        }
    });

    // View Toggle
    viewBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            viewBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentView = btn.dataset.view;

            // Toggle grid class for responsive layout
            if (currentView === 'compact') {
                productGrid.classList.add('compact-view');
            } else {
                productGrid.classList.remove('compact-view');
            }

            // Re-render without filtering if possible, or just re-apply filters
            applyFilters();
        });
    });

    // Focus animation
    searchInput.addEventListener('focus', () => {
        document.querySelector('.search-gradient').style.animation = 'gradientMove 3s infinite linear';
    });

    searchInput.addEventListener('blur', () => {
        document.querySelector('.search-gradient').style.animation = 'none';
    });
});

// --- Helpers ---
function parsePrice(priceStr) {
    // Clean string
    if (!priceStr) return { value: 0, display: '' };

    // Remove "price :" prefix if present (Myntra)
    let cleanStr = priceStr.replace(/^price\s*:\s*/i, '').trim();

    // Default fallback: show the cleaned string as is
    let mainPrice = cleanStr;
    let mrp = '';
    let discount = '';
    let value = 0;

    try {
        // Check for Standard Format: "123 (MRP: 456, Off: 10%)"
        if (cleanStr.includes('MRP:')) {
            const parts = cleanStr.split('(');
            mainPrice = parts[0].trim();

            const matchMrp = cleanStr.match(/MRP:\s*(.*?),/);
            if (matchMrp) mrp = matchMrp[1].trim();

            const matchOff = cleanStr.match(/Off:\s*(.*?)\)/);
            if (matchOff) {
                discount = matchOff[1].trim();
                if (discount.startsWith('(')) discount = discount.substring(1);
            }
        }
        // Check for Myntra Format: "Rs. 1234 Rs. 5678 (60% OFF)"
        else if (cleanStr.includes('Rs.') && cleanStr.includes('OFF')) {
            // Regex to capture: Rs. <price> Rs. <mrp> (<discount> OFF)
            // Flexible regex to handle spacing
            const myntraRegex = /(Rs\.\s*[\d,]+)\s*(Rs\.\s*[\d,]+)\s*\((.*?OFF)\)/i;
            const match = cleanStr.match(myntraRegex);

            if (match) {
                mainPrice = match[1].trim();
                mrp = match[2].trim();
                discount = match[3].trim();
            } else {
                // Try to just grab the first part if regex fails
                const parts = cleanStr.split('Rs.');
                if (parts.length > 1) {
                    mainPrice = 'Rs.' + parts[1].trim();
                }
            }
        }
        // Check for Flipkart Format: "₹12,999 ( ₹16,999 with 23% off)"
        else if (cleanStr.includes('with') && cleanStr.includes('(')) {
            // Regex: <price> ( <mrp> with <discount>)
            const flipkartRegex = /^(.*?)\s*\(\s*(.*?)\s*with\s*(.*?)\s*\)/i;
            const match = cleanStr.match(flipkartRegex);

            if (match) {
                mainPrice = match[1].trim();
                mrp = match[2].trim();
                discount = match[3].replace(')', '').trim();
            } else {
                mainPrice = cleanStr.split('(')[0].trim();
            }
        }
    } catch (e) {
        console.error("Price parse error for:", priceStr, e);
        mainPrice = cleanStr; // Fallback on error
    }

    // Calculate numeric value for sorting
    value = parseFloat(mainPrice.replace(/[^\d.]/g, ''));

    return {
        value: isNaN(value) ? 0 : value,
        display: mainPrice,
        mrp: mrp,
        discount: discount
    };
}

function shuffleArray(array) {
    for (let i = array.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [array[i], array[j]] = [array[j], array[i]];
    }
    return array;
}
