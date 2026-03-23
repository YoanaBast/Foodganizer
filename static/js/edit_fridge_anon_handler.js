const displayInput = document.getElementById('quantityInput');
const trueInput = document.getElementById('quantityTrue');
const unitSelect = document.getElementById('unitSelect');

const ingredientId = document.getElementById('ingredientId')?.value;
const anonIndex = document.getElementById('anonIndex')?.value;


let previousConversion = parseFloat(
    unitSelect.selectedOptions[0].dataset.conversion
);

let baseQuantity = parseFloat(trueInput.value) * previousConversion;

displayInput.addEventListener('input', () => {
    const val = parseFloat(displayInput.value);
    if (!isNaN(val)) {
        baseQuantity = val * previousConversion;
        trueInput.value = val;

        if (anonIndex !== undefined && anonIndex !== null) {
            updateSession(val, unitSelect.value);
        } else {
        }
    }
});

function convertQuantity(select) {
    const newConversion = parseFloat(select.selectedOptions[0].dataset.conversion);

    if (!isNaN(baseQuantity) && newConversion) {
        const converted = baseQuantity / newConversion;
        displayInput.value = converted.toFixed(2);
        trueInput.value = converted;

        if (anonIndex !== undefined && anonIndex !== null) {
            updateSession(converted, select.value);
        }
    }

    previousConversion = newConversion;
}

function updateSession(quantity, unitId) {
    const url = `/planner/fridge/anon/edit/${anonIndex}/`;

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
        },
        body: JSON.stringify({
            quantity: quantity,
            unit_id: unitId
        })
    })
    .then(res => {
        return res.json();
    })
    .then(data => console.log('fetch response data:', data))
    .catch(err => console.error('Session update failed:', err));
}

function getCSRFToken() {
    return document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
}