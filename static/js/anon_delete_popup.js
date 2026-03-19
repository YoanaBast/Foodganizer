function openDeleteModal(type, id, name) {
    const modal = document.getElementById('deleteModal');
    const text = document.getElementById('deleteModalText');
    const form = document.getElementById('deleteForm');

    text.textContent = `Are you sure you want to delete "${name}"?`;
    form.action = `/planner/fridge/anon/delete/${id}/`;

    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeDeleteModal() {
    const modal = document.getElementById('deleteModal');
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
}