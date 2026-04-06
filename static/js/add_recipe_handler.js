const meta = document.getElementById('recipe-meta');
const mode = meta.dataset.mode;

const addIngredientUrl = mode === 'edit' ? meta.dataset.addIngredientUrl : null;
const csrftoken = document.cookie.split('; ')
    .find(row => row.startsWith('csrftoken='))
    ?.split('=')[1];

// Open/close modal
document.getElementById('addIngredientBtn').addEventListener('click', function () {
    document.getElementById('ingredientModal').style.display = 'flex';
});

function closeModal() {
    document.getElementById('ingredientModal').style.display = 'none';
    document.getElementById('ingredientSelect').value = '';
    document.getElementById('ingredientSearch').value = '';  // add this
    document.getElementById('quantityInput').value = '';
    document.getElementById('unitSelect').innerHTML = '';
}


function loadUnits() {
    const select = document.getElementById('ingredientSelect');
    const selected = select.options[select.selectedIndex];
    const units = JSON.parse(selected.dataset.units || '[]');
    const unitSelect = document.getElementById('unitSelect');

    unitSelect.innerHTML = units.map(u =>
        `<option value="${u.id}">${u.name}</option>`
    ).join('');
}

function addIngredient() {
    const ingredient_id = document.getElementById('ingredientSelect').value;
    const quantity = parseFloat(document.getElementById('quantityInput').value);
    const unit_id = document.getElementById('unitSelect').value;

    // get name from the search input instead of select.options
    const ingredient_name = document.getElementById('ingredientSearch').value;
    const unit_name = document.getElementById('unitSelect').options[
        document.getElementById('unitSelect').selectedIndex
    ]?.text;

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

    if (mode === 'edit') {
        fetch(addIngredientUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrftoken,
            },
            body: JSON.stringify({ingredient_id, quantity, unit_id})
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                // hide option in dropdown instead of removing
                const opt = document.querySelector(`#ingredientOptions .search-option[data-value="${ingredient_id}"]`);
                if (opt) opt.style.display = 'none';

                appendIngredientLine(
                    data.ingredient_name,
                    data.quantity,
                    data.unit_name,
                    data.ingredient_id,
                    data.unit_id
                );
                closeModal();
            } else {
                alert('Error: ' + data.error);
            }
        });

    } else {
        const container = document.getElementById('ingredientsContainer');
        const totalForms = document.getElementById('id_recipe_ingredient-TOTAL_FORMS');
        const formIndex = parseInt(totalForms.value);

        // hide option in dropdown instead of removing
        const opt = document.querySelector(`#ingredientOptions .search-option[data-value="${ingredient_id}"]`);
        if (opt) opt.style.display = 'none';

        const newRow = document.createElement('div');
        newRow.classList.add('ingredient-line');
        newRow.innerHTML = `
            <input type="hidden" name="recipe_ingredient-${formIndex}-id" value="">
            <label>Ingredient</label>
            <select name="recipe_ingredient-${formIndex}-ingredient">
                <option value="${ingredient_id}" selected>${ingredient_name}</option>
            </select>
            <label>Quantity</label>
            <input type="number" name="recipe_ingredient-${formIndex}-quantity"
                   value="${quantity}" step="0.01" min="0.01">
            <label>Unit</label>
            <select name="recipe_ingredient-${formIndex}-unit">
                <option value="${unit_id}" selected>${unit_name}</option>
            </select>
            <input type="checkbox" name="recipe_ingredient-${formIndex}-DELETE"
                   id="delete_${formIndex}"
                   data-ingredient-id="${ingredient_id}"
                   data-ingredient-name="${ingredient_name}"
                   onchange="handleAddDelete(this)">
            <label for="delete_${formIndex}">Delete</label>
        `;

        container.appendChild(newRow);
        totalForms.value = formIndex + 1;
        closeModal();
    }
}

function appendIngredientLine(name, quantity, unit_name, ingredient_id, unit_id) {
    const container = document.getElementById('ingredientsContainer');
    const div = document.createElement('div');
    div.classList.add('ingredient-line');
    div.innerHTML = `
        <label>Ingredient</label>
        <select name="new_ingredient">
            <option value="${ingredient_id}" selected>${name}</option>
        </select>
        <label>Quantity</label>
        <input type="number" value="${quantity}" step="0.01" min="0.01">
        <label>Unit</label>
        <select name="new_unit">
            <option value="${unit_id}" selected>${unit_name}</option>
        </select>
        <input type="checkbox" id="delete_${ingredient_id}" onchange="deleteIngredient(${ingredient_id}, this)">
        <label for="delete_${ingredient_id}">Delete</label>
    `;
    container.insertBefore(div, document.getElementById('addIngredientBtn').parentElement);
}

function handleAddDelete(checkbox) {
    const line = checkbox.closest('.ingredient-line');
    line.style.opacity = checkbox.checked ? '0.3' : '1';

    const ingredientSelect = document.getElementById('ingredientSelect');
    const id = checkbox.dataset.ingredientId;
    const name = checkbox.dataset.ingredientName;

    if (checkbox.checked) {
        // marked for deletion - remove from dropdown
        const opt = ingredientSelect.querySelector(`option[value="${id}"]`);
        if (opt) opt.remove();
    } else {
        // unchecked - add back to dropdown
        const alreadyExists = ingredientSelect.querySelector(`option[value="${id}"]`);
        if (!alreadyExists) {
            const opt = document.createElement('option');
            opt.value = id;
            opt.text = name;
            ingredientSelect.appendChild(opt);
        }
    }
}