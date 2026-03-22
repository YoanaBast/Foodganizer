function toggleFav(recipeId, btn) {
    fetch(`/recipes/${recipeId}/toggle_fav/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(res => {
        if (res.redirected || res.status === 302) {
            window.location.href = '/users/login/';
            return;
        }
        return res.json();
    })
    .then(data => {
        if (!data) return;
        const src = data.favourited ? btn.dataset.fullHeart : btn.dataset.emptyHeart;
        btn.innerHTML = `<img src="${src}" alt="fav" class="heart-icon" />`;
    });
}

// helper to get csrf token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
