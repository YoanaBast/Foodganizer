function openDeleteModal(type, id, name) {
    // type: 'recipe' or 'ingredient'
    const modal = document.getElementById('deleteModal');
    const text = document.getElementById('deleteModalText');
    const form = document.getElementById('deleteForm');

    text.textContent = `Are you sure you want to delete "${name}"?`;

    if (type === 'fridge') {
        form.action = `/planner/fridge/${id}/delete/`;
    } else {
        form.action = `/${type}s/${id}/delete/`;
    }
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeDeleteModal() {
    const modal = document.getElementById('deleteModal');
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
}
