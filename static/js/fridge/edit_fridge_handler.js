const displayInput = document.getElementById('quantityInput');
const trueInput = document.getElementById('quantityTrue');

let previousConversion = parseFloat(
    document.getElementById('unitSelect').selectedOptions[0].dataset.conversion
);

//  initialize base from TRUE value (not rounded)
let baseQuantity = parseFloat(trueInput.value) * previousConversion;

// when user types → update BOTH
displayInput.addEventListener('input', () => {
    const val = parseFloat(displayInput.value);
    if (!isNaN(val)) {
        baseQuantity = val * previousConversion;
        trueInput.value = val; // keep true in sync
    }
});

function convertQuantity(select) {
    const newConversion = parseFloat(select.selectedOptions[0].dataset.conversion);

    if (!isNaN(baseQuantity) && newConversion) {
        const converted = baseQuantity / newConversion;

        // show rounded
        displayInput.value = converted.toFixed(2);

        // store full precision
        trueInput.value = converted;
    }

    previousConversion = newConversion;
}