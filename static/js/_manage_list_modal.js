// this is used to handle the more (...) menu next to Categories and Dietary Tags in ingredientRecipe/ingredient creation and edition

let _pendingDeleteFn = null;
let _pendingEditFn = null;
let _manageHasChanges = false;
let _manageSelectId = null;  // which select to update on edit/delete

function showManageMsg(msg, isError) {
    const el = document.getElementById('manageListMsg');
    el.textContent = msg;
    el.style.display = 'block';
    el.style.background = isError ? '#3a1a1a' : '#1a3a1a';
    el.style.border = `1px solid ${isError ? '#a33' : '#3a3'}`;
    el.style.color = isError ? '#f88' : '#8f8';
    setTimeout(() => {
        el.style.display = 'none';
    }, 3000);
}

function confirmDeleteYes() {
    document.getElementById('manageListConfirm').style.display = 'none';
    if (_pendingDeleteFn) _pendingDeleteFn();
    _pendingDeleteFn = null;
}

function confirmDeleteNo() {
    document.getElementById('manageListConfirm').style.display = 'none';
    _pendingDeleteFn = null;
}

function confirmEditYes() {
    const inputs = document.querySelectorAll('#manageListEditFields input');
    const data = {};
    inputs.forEach(input => {
        data[input.name] = input.value.trim();
    });
    document.getElementById('manageListEdit').style.display = 'none';
    if (_pendingEditFn) _pendingEditFn(data);
    _pendingEditFn = null;
}

function confirmEditNo() {
    document.getElementById('manageListEdit').style.display = 'none';
    _pendingEditFn = null;
}

function askConfirm(msg, fn) {
    document.getElementById('manageListConfirmMsg').textContent = msg;
    document.getElementById('manageListConfirm').style.display = 'block';
    document.getElementById('manageListEdit').style.display = 'none';
    _pendingDeleteFn = fn;
}

function askEdit(fields, fn) {
    const container = document.getElementById('manageListEditFields');
    container.innerHTML = '';

    fields.forEach((f, i) => {
        const input = document.createElement('input');
        input.type = 'text';
        input.name = f.key;
        input.placeholder = f.placeholder || f.key;
        input.value = f.value || '';
        input.style.cssText = 'width:100%; box-sizing:border-box; margin-bottom:0.4rem;';
        if (i === 0) setTimeout(() => {
            input.focus();
            input.select();
        }, 50);
        container.appendChild(input);
    });

    document.getElementById('manageListEdit').style.display = 'block';
    document.getElementById('manageListConfirm').style.display = 'none';
    _pendingEditFn = fn;
}

document.getElementById('manageListEdit').addEventListener('keydown', function (e) {
    if (e.key === 'Enter') confirmEditYes();
    if (e.key === 'Escape') confirmEditNo();
});

function openManageModal(title, items, selectId) {
    _manageHasChanges = false;
    _manageSelectId = selectId || null;
    document.getElementById('manageListTitle').textContent = title;
    document.getElementById('manageListMsg').style.display = 'none';
    document.getElementById('manageListConfirm').style.display = 'none';
    document.getElementById('manageListEdit').style.display = 'none';
    const container = document.getElementById('manageListItems');
    container.innerHTML = '';

    if (!items || items.length === 0) {
        container.innerHTML = '<p style="color:#888">Nothing here yet.</p>';
        document.getElementById('manageListModal').style.display = 'flex';
        return;
    }

    items.forEach(item => {
        const row = document.createElement('div');
        row.id = `manage-row-${item.id}`;
        row.style.cssText = 'display:flex; align-items:center; gap:0.5rem; padding:0.4rem 0; border-bottom:1px solid #333;';

        const nameSpan = document.createElement('span');
        nameSpan.textContent = item.name;
        nameSpan.style.flex = '1';

        const editBtn = document.createElement('button');
        editBtn.type = 'button';
        editBtn.className = 'icon-table';
        editBtn.title = 'Edit';
        editBtn.innerHTML = '<i class="fa-solid fa-pen-to-square"></i>';
        editBtn.onclick = () => {
            askEdit(item.edit_fields, (data) => {
                fetch(item.edit_url, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    body: new URLSearchParams(data)
                }).then(r => r.json()).then(result => {
                    if (result.error) showManageMsg(result.error, true);
                    else {
                        nameSpan.textContent = result.name;
                        showManageMsg(`Updated to "${result.name}"`, false);
                        _manageHasChanges = true;
                        if (_manageSelectId) {
                            const select = document.getElementById(_manageSelectId);
                            if (select) {
                                const opt = select.querySelector(`option[value="${item.id}"]`);
                                if (opt) opt.textContent = result.name;
                            }
                        }
                    }
                }).catch(() => showManageMsg('Request failed.', true));
            });
        };

        const delBtn = document.createElement('button');
        delBtn.type = 'button';
        delBtn.className = 'icon-delete-btn';
        delBtn.title = 'Delete';
        delBtn.innerHTML = '<i class="fa-solid fa-trash"></i>';
        delBtn.onclick = () => {
            askConfirm(`Delete "${nameSpan.textContent}"?`, () => {
                fetch(item.delete_url, {
                    method: 'POST',
                    headers: {'X-CSRFToken': getCookie('csrftoken')}
                }).then(r => r.json()).then(result => {
                    if (result.error) showManageMsg(result.error, true);
                    else {
                        document.getElementById(`manage-row-${item.id}`)?.remove();
                        showManageMsg('Deleted.', false);
                        _manageHasChanges = true;
                        if (_manageSelectId) {
                            const select = document.getElementById(_manageSelectId);
                            if (select) {
                                const opt = select.querySelector(`option[value="${item.id}"]`);
                                if (opt) opt.remove();
                            }
                        }
                    }
                }).catch(() => showManageMsg('Request failed.', true));
            });
        };

        row.appendChild(nameSpan);
        row.appendChild(editBtn);
        row.appendChild(delBtn);
        container.appendChild(row);
    });

    document.getElementById('manageListModal').style.display = 'flex';
}

function closeManageModal() {
    document.getElementById('manageListModal').style.display = 'none';
    if (_manageHasChanges) location.reload();
}

document.getElementById('manageListModal').addEventListener('click', function (e) {
    if (e.target === this) closeManageModal();
});



