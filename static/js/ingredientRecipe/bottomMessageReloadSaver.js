document.addEventListener('DOMContentLoaded', function () {
    const section = document.getElementById('conversion-section');
    if (!section) return;

    // Any form submit inside this section: remember scroll position first
    section.querySelectorAll('form').forEach(function (form) {
        form.addEventListener('submit', function () {
            sessionStorage.setItem('editIngredientScrollY', window.scrollY);
        });
    });
});

// After reload, restore scroll position if one was saved for this page
window.addEventListener('load', function () {
    const savedScroll = sessionStorage.getItem('editIngredientScrollY');
    if (savedScroll !== null) {
        window.scrollTo(0, parseInt(savedScroll, 10));
        sessionStorage.removeItem('editIngredientScrollY');
    }
});
