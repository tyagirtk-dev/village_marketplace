// Live search suggestions
const searchInput = document.getElementById('searchInput');
const suggestionsBox = document.getElementById('searchSuggestions');
if (searchInput) {
    let debounceTimer;
    searchInput.addEventListener('input', function() {
        clearTimeout(debounceTimer);
        const query = this.value.trim();
        if (query.length < 2) {
            suggestionsBox.classList.remove('show');
            return;
        }
        debounceTimer = setTimeout(() => {
            fetch(`/search-suggestions?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    suggestionsBox.innerHTML = '';
                    if (data.length) {
                        data.forEach(item => {
                            const a = document.createElement('a');
                            a.className = 'dropdown-item';
                            a.href = `/product/${item.id}`;
                            a.innerHTML = `<img src="${item.image}" width="30" height="30" class="me-2"> ${item.name} - ₹${item.price}`;
                            suggestionsBox.appendChild(a);
                        });
                        suggestionsBox.classList.add('show');
                    } else {
                        suggestionsBox.classList.remove('show');
                    }
                });
        }, 300);
    });
    document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target)) suggestionsBox.classList.remove('show');
    });
}
// Dark Mode
const toggle = document.getElementById('darkModeToggle');
const html = document.documentElement;
const saved = localStorage.getItem('theme');
if (saved) html.setAttribute('data-bs-theme', saved);
toggle?.addEventListener('click', () => {
    const newTheme = html.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-bs-theme', newTheme);
    localStorage.setItem('theme', newTheme);
});

// Search suggestions
const searchInput = document.querySelector('.search-input');
const suggestionsDiv = document.querySelector('.search-suggestions');
if (searchInput) {
    let timer;
    searchInput.addEventListener('input', function() {
        clearTimeout(timer);
        const q = this.value.trim();
        if (q.length < 2) { suggestionsDiv.classList.remove('show'); return; }
        timer = setTimeout(() => {
            fetch(`/search-suggestions?q=${encodeURIComponent(q)}`)
                .then(res => res.json())
                .then(data => {
                    suggestionsDiv.innerHTML = '';
                    if (data.length) {
                        data.forEach(p => {
                            const a = document.createElement('a');
                            a.className = 'dropdown-item';
                            a.href = `/product/${p.id}`;
                            a.innerHTML = `<img src="${p.image}" width="30" height="30" class="me-2"> ${p.name} – ₹${p.price}`;
                            suggestionsDiv.appendChild(a);
                        });
                        suggestionsDiv.classList.add('show');
                    } else { suggestionsDiv.classList.remove('show'); }
                });
        }, 300);
    });
    document.addEventListener('click', (e) => { if (!searchInput.contains(e.target)) suggestionsDiv.classList.remove('show'); });
}

// Update cart count via API (optional)
function updateCartCount() {
    fetch('/api/cart/count').then(r=>r.json()).then(data=>{
        document.querySelectorAll('.cart-count-badge').forEach(el=>{ el.textContent = data.count; el.style.display = data.count ? 'inline-block' : 'none'; });
    }).catch(e=>console.log);
}
updateCartCount();
setInterval(updateCartCount, 30000);
