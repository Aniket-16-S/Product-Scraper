const PASSWORD = "abcd#1234";

function checkLogin() {
    const input = document.getElementById('password-input').value;
    if (input === PASSWORD) {
        document.getElementById('login-overlay').style.display = 'none';
        document.getElementById('admin-content').style.display = 'block';
        localStorage.setItem('admin_auth', 'true');
        loadStats();
        loadProducts();
    } else {
        document.getElementById('login-error').style.display = 'block';
    }
}

function logout() {
    localStorage.removeItem('admin_auth');
    location.reload();
}

// Check session
if (localStorage.getItem('admin_auth') === 'true') {
    document.getElementById('login-overlay').style.display = 'none';
    document.getElementById('admin-content').style.display = 'block';
    loadStats();
    loadProducts();
}

async function loadStats() {
    try {
        const res = await fetch('/api/admin/stats');
        const data = await res.json();
        document.getElementById('total-items').textContent = data.total_items;
        document.getElementById('total-queries').textContent = data.total_queries;
        document.getElementById('db-size').textContent = (data.db_size_bytes / (1024 * 1024)).toFixed(2) + ' MB';
    } catch (e) {
        console.error("Failed to load stats", e);
    }
}

async function loadProducts() {
    try {
        const res = await fetch('/api/admin/products?limit=50');
        const products = await res.json();
        const list = document.getElementById('product-list');
        list.innerHTML = '';

        products.forEach(p => {
            const div = document.createElement('div');
            div.className = 'list-item';
            div.innerHTML = `
                <div>
                    <div style="font-weight: bold;">${p.name}</div>
                    <div style="font-size: 0.8rem; color: #aaa;">${p.source} | ${p.query} | ${new Date(p.timestamp).toLocaleString()}</div>
                </div>
                <button class="btn btn-danger" style="padding: 5px 10px; font-size: 0.8rem;" onclick="deleteItem(${p.id})">Delete</button>
            `;
            list.appendChild(div);
        });
    } catch (e) {
        console.error("Failed to load products", e);
    }
}

async function updateTTL() {
    const ttl = document.getElementById('ttl-input').value;
    if (!ttl) return;

    try {
        await fetch('/api/admin/ttl', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ttl_minutes: parseInt(ttl) })
        });
        alert('TTL cleanup started');
        loadStats();
    } catch (e) {
        alert('Failed to set TTL');
    }
}

async function clearCache() {
    if (!confirm('Are you sure you want to delete ALL data?')) return;

    try {
        await fetch('/api/admin/clear', { method: 'POST' });
        alert('Cache cleared');
        loadStats();
        loadProducts();
    } catch (e) {
        alert('Failed to clear cache');
    }
}

async function deleteItem(id) {
    if (!confirm('Delete this item?')) return;

    try {
        await fetch(`/api/admin/item/${id}`, { method: 'DELETE' });
        loadStats();
        loadProducts();
    } catch (e) {
        alert('Failed to delete item');
    }
}
