//tracks selected recipes across pages and filters visible recipes dynamically


document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('recipe-form');

    // Collect all visible checkbox values on this page
    const visibleIds = new Set(
        Array.from(form.querySelectorAll('.recipe-checkbox')).map(cb => cb.value)
    );

    // Remove server-rendered hidden inputs that duplicate a visible checkbox.
    // The real checkbox handles submission for current-page items.
    form.querySelectorAll('.hidden-selection').forEach(h => {
        if (visibleIds.has(h.value)) h.remove();
    });

    // For pre-checked boxes (restored from URL params), re-add hidden inputs
    // so they survive when the user navigates to another page.
    form.querySelectorAll('.recipe-checkbox:checked').forEach(cb => {
        ensureHidden(cb.value);
    });
    updatePaginationLinks();
});

function ensureHidden(value) {
    const form = document.getElementById('recipe-form');
    const exists = Array.from(form.querySelectorAll('.hidden-selection')).some(h => h.value === value);
    if (!exists) {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'recipes';
        input.value = value;
        input.className = 'hidden-selection';
        form.appendChild(input);
    }
}

function removeHidden(value) {
    document.getElementById('recipe-form').querySelectorAll('.hidden-selection').forEach(h => {
        if (h.value === value) h.remove();
    });
}

// When user checks/unchecks a box, keep hidden inputs in sync
// and update pagination links so the selection survives page navigation.
function updateSelection(checkbox) {
    if (checkbox.checked) {
        ensureHidden(checkbox.value);
    } else {
        removeHidden(checkbox.value);
    }
    updatePaginationLinks();
}

function updatePaginationLinks() {
    const form = document.getElementById('recipe-form');

    const checkedIds = Array.from(form.querySelectorAll('.recipe-checkbox:checked')).map(cb => cb.value);
    const hiddenIds  = Array.from(form.querySelectorAll('.hidden-selection')).map(h => h.value);
    const allSelected = [...new Set([...checkedIds, ...hiddenIds])];

    document.querySelectorAll('.pagination a').forEach(link => {
        const url = new URL(link.href);
        url.searchParams.delete('recipes');
        allSelected.forEach(id => url.searchParams.append('recipes', id));
        link.href = url.toString();
    });
}

function filterRecipes() {
    const search = document.getElementById('search-box').value.toLowerCase();

    document.querySelectorAll('.recipe-line').forEach(div => {
        const name = div.dataset.name;
        div.style.display = name.includes(search) ? 'flex' : 'none';
    });
}
