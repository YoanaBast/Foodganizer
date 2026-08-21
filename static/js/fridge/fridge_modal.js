const modal = document.getElementById('addFridgeItemModal');
const openBtn = document.getElementById('openAddFridgeModal');

openBtn.addEventListener('click', function(e) {
    e.preventDefault();
    modal.style.display = 'block';
});

// Close modal when clicking outside or with a close button
window.addEventListener('click', function(e) {
    if (e.target == modal) {
        modal.style.display = 'none';
    }
});
