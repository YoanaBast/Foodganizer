

function fetchAndManage(url, title) {
    fetch(url)
        .then(r => r.json())
        .then(d => openManageModal(title, d.items))
        .catch(e => alert('Failed to load: ' + e));
}
