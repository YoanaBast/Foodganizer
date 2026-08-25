const meta = document.getElementById('recipe-meta');
const mode = meta.dataset.mode;

// ---------- Modal open/close ----------

document.getElementById('addIngredientBtn').addEventListener('click', function () {
    document.getElementById('ingredientModal').style.display = 'flex';
});

function closeModal() {
    document.getElementById('ingredientModal').style.display = 'none';
    document.getElementById('ingredientSelect').value = '';
    document.getElementById('ingredientSearch').value = '';
    document.getElementById('quantityInput').value = '';
    document.getElementById('unitSelect').innerHTML = '';
    document.getElementById('ingredientOptions').classList.remove('open');
}

// ---------- Searchable ingredient dropdown ----------

function openIngredientDropdown() {
    document.getElementById('ingredientOptions').classList.add('open');
}

function getUsedIngredientIds() {
    const usedIngredients = new Set();

    document.querySelectorAll(
        '#ingredientsContainer select[name$="-ingredient"]'
    ).forEach(select => {
        if (select.value) {
            usedIngredients.add(select.value);
        }
    });

    return usedIngredients;
}

// Visibility logic only — no side effect on open/closed state.
// Single source of truth: visible only if it matches search text
// AND isn't already added to the ingredientRecipe (unsaved rows included).
function applyIngredientFilter() {
    const filter = document.getElementById('ingredientSearch').value.toLowerCase();
    const usedIngredients = getUsedIngredientIds();
    const options = document.querySelectorAll('#ingredientOptions .search-option');

    options.forEach(opt => {
        const matchesText = !filter || opt.textContent.toLowerCase().includes(filter);
        const isUsed = usedIngredients.has(opt.dataset.value);
        opt.style.display = (matchesText && !isUsed) ? '' : 'none';
    });
}

// Called from oninput/onfocus on the search box: filters AND opens the dropdown.
function filterIngredients() {
    applyIngredientFilter();
    openIngredientDropdown();
}

// Called after add/delete/page-load: refreshes visibility WITHOUT forcing
// the dropdown open (so it doesn't pop open on page load or after adding a row).
function updateIngredientOptions() {
    applyIngredientFilter();
}

function selectIngredient(opt) {
    document.getElementById('ingredientSearch').value = opt.textContent.trim();
    document.getElementById('ingredientSelect').value = opt.dataset.value;
    document.getElementById('ingredientOptions').classList.remove('open');

    const units = JSON.parse(opt.dataset.units || '[]');
    const unitSelect = document.getElementById('unitSelect');
    unitSelect.innerHTML = '';
    units.forEach(u => {
        const o = document.createElement('option');
        o.value = u.id;
        o.textContent = u.name;
        unitSelect.appendChild(o);
    });
}

function loadUnits() {
    // Kept for backward compatibility if referenced elsewhere;
    // selectIngredient() now handles unit population directly.
    const select = document.getElementById('ingredientSelect');
    if (!select.value) return;
    const opt = document.querySelector(
        `#ingredientOptions .search-option[data-value="${select.value}"]`
    );
    if (opt) selectIngredient(opt);
}

// ---------- Add ingredient row ----------

function addIngredient() {
    const ingredient_id = document.getElementById('ingredientSelect').value;
    const quantity = parseFloat(document.getElementById('quantityInput').value);
    const unit_id = document.getElementById('unitSelect').value;

    const ingredient_name = document.getElementById('ingredientSearch').value;
    const unitSelect = document.getElementById('unitSelect');
    const unit_name = unitSelect.selectedIndex >= 0
        ? unitSelect.options[unitSelect.selectedIndex].text
        : '';

    if (!ingredient_id || quantity === '' || isNaN(quantity) || !unit_id) {
        alert('Please fill in all fields.');
        return;
    }

    if (quantity <= 0) {
        alert('Quantity must be greater than 0.');
        return;
    }

    if (quantity > 100000) {
        alert('Quantity must be less than 100 000.');
        return;
    }

    const container = document.getElementById('ingredientsContainer');
    const totalForms = document.getElementById('id_recipe_ingredient-TOTAL_FORMS');
    const formIndex = parseInt(totalForms.value);

    const newRow = document.createElement('div');

    newRow.classList.add('search_filter');
    newRow.classList.add('flex-row-flex-start');
    newRow.classList.add('mb-3');

    newRow.innerHTML = `
        <input type="hidden" name="recipe_ingredient-${formIndex}-id" value="">

        <label>Ingredient</label>
        <select name="recipe_ingredient-${formIndex}-ingredient">
            <option value="${ingredient_id}" selected>${ingredient_name}</option>
        </select>

        <label>Quantity</label>
        <input type="number"
               name="recipe_ingredient-${formIndex}-quantity"
               value="${quantity}"
               step="0.01"
               min="0.01">

        <label>Unit</label>
        <select name="recipe_ingredient-${formIndex}-unit">
            <option value="${unit_id}" selected>${unit_name}</option>
        </select>

        <input type="checkbox"
               name="recipe_ingredient-${formIndex}-DELETE"
               id="delete_${formIndex}"
               data-ingredient-id="${ingredient_id}"
               data-ingredient-name="${ingredient_name}"
               onchange="handleAddDelete(this)">

        <label for="delete_${formIndex}">Delete</label>
    `;

    container.insertBefore(
        newRow,
        document.getElementById('addIngredientBtn').parentElement
    );

    totalForms.value = formIndex + 1;

    // Re-apply used/search filter now that a new row exists
    updateIngredientOptions();

    closeModal();
}

function handleAddDelete(checkbox) {
    const line = checkbox.closest('.search_filter');
    line.style.opacity = checkbox.checked ? '0.3' : '1';

    // A checked DELETE box frees that ingredient back up for selection
    updateIngredientOptions();
}

// ---------- Wiring ----------

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('#ingredientOptions .search-option').forEach(opt => {
        opt.addEventListener('click', () => selectIngredient(opt));
    });

    document.addEventListener('click', e => {
        if (!e.target.closest('#ingredientDropdown')) {
            document.getElementById('ingredientOptions').classList.remove('open');
        }
    });

    updateIngredientOptions();
});