function loadUnits() {
    const select = document.getElementById('ingredientSelect');
    const unitSelect = document.getElementById('unitSelect');

    // Clear completely
    unitSelect.innerHTML = '';
    unitSelect.value = '';

    const selectedOption = select.options[select.selectedIndex];
    if (!selectedOption || !selectedOption.value) return;

    const unitsData = selectedOption.getAttribute('data-units');

    if (!unitsData) return;

    const units = JSON.parse(unitsData);

    units.forEach((u, index) => {
        const opt = document.createElement('option');
        opt.value = u.id;
        opt.textContent = u.name;
        unitSelect.appendChild(opt);
    });

    // Force first unit selected
    if (unitSelect.options.length > 0) {
        unitSelect.selectedIndex = 0;
    }

    console.log("Units loaded:", units);
    console.log("Selected unit:", unitSelect.value);
}

function closeModal() {
    const modal = document.getElementById('addFridgeItemModal');
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
}

document.getElementById('addFridgeItemForm').addEventListener('submit', function(e) {
    const qty = parseFloat(document.getElementById('quantityInput').value);
    const MIN_QTY = 0.01; // set minimum allowed
    const MAX_QTY = 100000; // set minimum allowed

    if (!qty || qty <= 0 || qty < MIN_QTY || qty > MAX_QTY) {
        e.preventDefault();
        alert(`Quantity must be greater than ${MIN_QTY} and less than ${MAX_QTY}.`);
    }
});