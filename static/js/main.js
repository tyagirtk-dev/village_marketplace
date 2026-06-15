document.addEventListener('DOMContentLoaded', function () {

    /* =========================
       DARK MODE
    ========================= */
    const darkModeToggle = document.getElementById('darkModeToggle');
    const html = document.documentElement;

    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        html.setAttribute('data-bs-theme', savedTheme);
        updateIcon(savedTheme);
    }

    function updateIcon(theme) {
        const icon = darkModeToggle?.querySelector('i');
        if (!icon) return;

        if (theme === 'dark') {
            icon.classList.remove('bi-moon-stars');
            icon.classList.add('bi-sun');
        } else {
            icon.classList.remove('bi-sun');
            icon.classList.add('bi-moon-stars');
        }
    }

    darkModeToggle?.addEventListener('click', function () {
        const current = html.getAttribute('data-bs-theme') || 'light';
        const next = current === 'dark' ? 'light' : 'dark';

        html.setAttribute('data-bs-theme', next);
        localStorage.setItem('theme', next);

        updateIcon(next);
    });

    /* =========================
       CART COUNT
    ========================= */
    function updateCartCount() {
        fetch('/api/cart/count')
            .then(r => r.json())
            .then(data => {
                document.querySelectorAll('.cart-count-badge').forEach(el => {
                    if (data.count > 0) {
                        el.textContent = data.count;
                        el.style.display = 'inline-block';
                    } else {
                        el.style.display = 'none';
                    }
                });
            })
            .catch(() => {});
    }

    if (document.querySelector('.cart-count-badge')) {
        updateCartCount();
        setInterval(updateCartCount, 30000);
    }

    /* =========================
       NOTIFICATIONS
    ========================= */
    function updateNotifications() {
        fetch('/api/notifications/unread-count')
            .then(r => r.json())
            .then(data => {
                const badge = document.getElementById('notificationBadge');
                if (!badge) return;

                if (data.count > 0) {
                    badge.textContent = data.count;
                    badge.style.display = 'inline-block';
                } else {
                    badge.style.display = 'none';
                }
            })
            .catch(() => {});
    }

    if (document.getElementById('notificationBadge')) {
        updateNotifications();
        setInterval(updateNotifications, 30000);
    }

    /* =========================
       LIVE SEARCH
    ========================= */
    const searchInput = document.getElementById('searchInput');
    const suggestionsBox = document.getElementById('searchSuggestions');

    if (searchInput && suggestionsBox) {
        let timer;

        searchInput.addEventListener('input', function () {
            clearTimeout(timer);

            const q = this.value.trim();

            if (q.length < 2) {
                suggestionsBox.classList.remove('show');
                return;
            }

            timer = setTimeout(() => {
                fetch(`/search-suggestions?q=${encodeURIComponent(q)}`)
                    .then(r => r.json())
                    .then(data => {
                        suggestionsBox.innerHTML = '';

                        if (data.length) {
                            data.forEach(p => {
                                const a = document.createElement('a');
                                a.className = 'dropdown-item';
                                a.href = `/product/${p.id}`;
                                a.innerHTML = `
                                    <img src="${p.image}" width="30" height="30" class="me-2">
                                    ${p.name} - ₹${p.price}
                                `;
                                suggestionsBox.appendChild(a);
                            });
                            suggestionsBox.classList.add('show');
                        } else {
                            suggestionsBox.classList.remove('show');
                        }
                    })
                    .catch(() => {});
            }, 300);
        });

        document.addEventListener('click', function (e) {
            if (!searchInput.contains(e.target)) {
                suggestionsBox.classList.remove('show');
            }
        });
    }

    /* =========================
       QUANTITY BUTTONS
    ========================= */
    document.querySelectorAll('.quantity-input').forEach(input => {
        const plus = input.nextElementSibling;
        const minus = input.previousElementSibling;

        plus?.addEventListener('click', () => {
            input.value = parseInt(input.value || 1) + 1;
            input.dispatchEvent(new Event('change'));
        });

        minus?.addEventListener('click', () => {
            const val = parseInt(input.value || 1);
            if (val > 1) {
                input.value = val - 1;
                input.dispatchEvent(new Event('change'));
            }
        });
    });

    /* =========================
       CONFIRM DELETE
    ========================= */
    document.querySelectorAll('.confirm-delete').forEach(btn => {
        btn.addEventListener('click', function (e) {
            if (!confirm('Are you sure? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });

    /* =========================
       AUTO CLOSE ALERTS
    ========================= */
    setTimeout(() => {
        document.querySelectorAll('.alert').forEach(alert => {
            try {
                const bsAlert = new bootstrap.Alert(alert);
                setTimeout(() => bsAlert.close(), 4000);
            } catch (e) {}
        });
    }, 1000);

});
