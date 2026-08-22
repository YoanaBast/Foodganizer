//this is used for adding categories, tags and units when creating/editing recipe/ingredient


let _modalUrl = '';
let _targetSelect = null;
let _modalFields = [];

function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^|;\\s*)' + name + '=([^;]*)'));
    return match ? decodeURIComponent(match[2]) : '';
}

// fields = [{key, placeholder}]
function openQuickModal(title, url, selectId, fields) {
    _modalUrl = url;
    _targetSelect = selectId ? document.getElementById(selectId) : null;
    _modalFields = fields || [{key: 'name', placeholder: 'Enter name...'}];

    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-error').style.display = 'none';

    const container = document.getElementById('modal-fields');
    container.innerHTML = '';
    _modalFields.forEach((f, i) => {
        const input = document.createElement('input');
        input.id = `modal-field-${f.key}`;
        input.placeholder = f.placeholder || f.key;
        input.style = 'width:100%; box-sizing:border-box; margin-bottom:0.75rem;';
        container.appendChild(input);
    });

    document.getElementById('quick-add-modal').style.display = 'flex';
    setTimeout(() => document.getElementById(`modal-field-${_modalFields[0].key}`).focus(), 50);
}

function closeQuickModal() {
    document.getElementById('quick-add-modal').style.display = 'none';
}

async function submitQuickModal() {
    const errorEl = document.getElementById('modal-error');
    const body = {};
    for (const f of _modalFields) {
        const val = document.getElementById(`modal-field-${f.key}`).value.trim();
        if (!val) {
            errorEl.textContent = `${f.placeholder || f.key} cannot be empty.`;
            errorEl.style.display = 'block';
            return;
        }
        body[f.key] = val;
    }

    const res = await fetch(_modalUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
        body: JSON.stringify(body)
    });

    const data = await res.json();
    if (!res.ok) {
        errorEl.textContent = data.error || JSON.stringify(data);
        errorEl.style.display = 'block';
        return;
    }

    if (_targetSelect) {
        if (_targetSelect.tagName === 'SELECT') {
            const opt = new Option(data.name, data.id, true, true);
            _targetSelect.add(opt);
            opt.selected = true;
        } else {
            const index = _targetSelect.querySelectorAll('li').length;
            const li = document.createElement('li');
            li.innerHTML = `<label for="id_dietary_tag_${index}">
                <input type="checkbox" name="dietary_tag" value="${data.id}" id="id_dietary_tag_${index}" checked>
                ${data.name}
            </label>`;
            _targetSelect.appendChild(li);
        }
    }

    closeQuickModal();
}

document.getElementById('quick-add-modal').addEventListener('click', function(e) {
    if (e.target === this) closeQuickModal();
});

document.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && document.getElementById('quick-add-modal').style.display === 'flex') {
        submitQuickModal();
    }
});


