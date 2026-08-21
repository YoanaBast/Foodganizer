document.addEventListener('DOMContentLoaded', function () {
    const btn = document.getElementById('iconHelpButton');
    const modal = document.getElementById('iconHelpModal');

    if (!btn || !modal) return;

    btn.addEventListener('click', function () {
        modal.classList.add('open');
    });

    modal.addEventListener('click', function (e) {
        if (e.target === modal) {
            modal.classList.remove('open');
        }
    });
});

function closeIconHelp() {
    document.getElementById('iconHelpModal').classList.remove('open');
}