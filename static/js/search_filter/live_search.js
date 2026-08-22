document.addEventListener('DOMContentLoaded', function () {
    const form = document.querySelector('.search_filter form');
    if (!form) return;

    const searchInput = form.querySelector('.searchbar');
    const selects = form.querySelectorAll('select');
    const tagCheckboxes = form.querySelectorAll('.tag-dropdown input[type="checkbox"]');

    let debounceTimer;
    const DEBOUNCE_DELAY = 500;

    function submitPreservingScroll() {
        sessionStorage.setItem('scrollY', window.scrollY);
        form.requestSubmit();
    }

    // Search input: debounced
    if (searchInput) {
        searchInput.addEventListener('input', function () {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(submitPreservingScroll, DEBOUNCE_DELAY);
        });
    }

    // Selects (category, sort): instant
    selects.forEach(function (select) {
        select.addEventListener('change', submitPreservingScroll);
    });

    // Tag checkboxes: instant
    tagCheckboxes.forEach(function (checkbox) {
        checkbox.addEventListener('change', submitPreservingScroll);
    });
});

// Restore scroll position after reload, if one was saved
window.addEventListener('load', function () {
    const savedScroll = sessionStorage.getItem('scrollY');
    if (savedScroll !== null) {
        window.scrollTo(0, parseInt(savedScroll, 10));
        sessionStorage.removeItem('scrollY');
    }
});