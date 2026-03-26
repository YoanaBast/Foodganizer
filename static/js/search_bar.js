function filterTable(inputId, tableSelector, columnIndex = 0) {
    const query = document.getElementById(inputId).value.toLowerCase();
    const rows = document.querySelectorAll(`${tableSelector} tbody tr`);
    rows.forEach(row => {
        const cell = row.querySelectorAll('td')[columnIndex];
        const text = cell?.textContent.toLowerCase() || '';
        row.style.display = text.includes(query) ? '' : 'none';
    });
}