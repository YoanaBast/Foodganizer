document.addEventListener('DOMContentLoaded', function () {
    const fileInput = document.getElementById('id_profile_picture');
    if (!fileInput) return;

    const label = document.querySelector('label[for="id_profile_picture"]');
    if (!label) return;

    const defaultText = label.textContent;

    fileInput.addEventListener('change', function () {
        if (fileInput.files.length > 0) {
            label.textContent = fileInput.files[0].name;
        } else {
            label.textContent = defaultText;
        }
    });

    // Remove the bare "Change:" text node Django inserts before the file input
    const changeTextNode = Array.from(fileInput.parentNode.childNodes).find(
        node => node.nodeType === Node.TEXT_NODE && node.textContent.trim() === 'Change:'
    );
    if (changeTextNode) {
        changeTextNode.remove();
    }
});