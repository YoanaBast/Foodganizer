document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('input[id^="id_base_quantity_"]').forEach(input => {
        const initial = input.value;

        input.addEventListener('focus', () => {
            if (parseFloat(input.value) === 0) input.value = '';
        });

        input.addEventListener('blur', () => {
            if (input.value === '' || parseFloat(input.value) < 0) {
                input.value = initial;
            }
        });
    });
});