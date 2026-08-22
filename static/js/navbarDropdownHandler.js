document.querySelectorAll(".tab-button").forEach(button => {
    button.addEventListener("click", () => {
        const dropdown = button.parentElement;

        document.querySelectorAll(".tab-dropdown").forEach(item => {
            if (item !== dropdown) {
                item.classList.remove("open");
            }
        });

        dropdown.classList.toggle("open");
    });
});