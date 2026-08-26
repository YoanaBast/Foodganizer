async function calculateDeficit() {
    const start = document.getElementById('deficit-start').value;
    const end = document.getElementById('deficit-end').value;
    const fillEmpty = document.getElementById('fill-empty').checked;
    const resultDiv = document.getElementById('deficit-result');
    const errorDiv = document.getElementById('deficit-error');

    errorDiv.style.display = 'none';
    resultDiv.style.display = 'none';

    if (!start || !end) {
        errorDiv.textContent = 'Please select both dates.';
        errorDiv.style.display = 'block';
        return;
    }

    const res = await fetch(`/planner/calendar/deficit/?start=${start}&end=${end}&fill_empty=${fillEmpty}`);
    const data = await res.json();

    if (data.error === 'no_biometrics') {
        errorDiv.innerHTML = 'No biometrics found. <a href="{% url "biometrics" %}">Set your TDEE first</a>.';
        errorDiv.style.display = 'block';
        return;
    }

    if (data.error) {
        errorDiv.textContent = data.error;
        errorDiv.style.display = 'block';
        return;
    }

    document.getElementById('deficit-text').textContent = data.result;
    document.getElementById('deficit-days').textContent = data.days;
    document.getElementById('deficit-consumed').textContent = `${Math.round(data.total_consumed)} kcal`;
    document.getElementById('deficit-maintenance').textContent = `${Math.round(data.total_maintenance)} kcal`;

    const net = Math.round(data.deficit);
    const netEl = document.getElementById('deficit-net');
    netEl.textContent = net > 0 ? `-${net} kcal` : net < 0 ? `+${Math.abs(net)} kcal` : `0 kcal`;
    netEl.style.color = net > 0 ? '#22c55e' : net < 0 ? '#ff6b6b' : '#f59e0b';

    resultDiv.style.display = 'block';
}

// default dates to current month
const now = new Date();
const y = now.getFullYear();
const m = String(now.getMonth()+1).padStart(2,'0');
const firstDay = `${y}-${m}-01`;
const lastDay = `${y}-${m}-${String(new Date(y, now.getMonth()+1, 0).getDate()).padStart(2,'0')}`;
document.getElementById('deficit-start').value = firstDay;
document.getElementById('deficit-end').value = lastDay;

let current = new Date();
let today = new Date();
let monthData = {};
let tdee = null;
let selectedDate = null;
let addType = 'recipe';
let selectedItem = null;
let editingEntry = null;

function fmt(d) { return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; }

async function loadMonth() {
    renderSkeleton();
    const res = await fetch(`/planner/calendar/data/?year=${current.getFullYear()}&month=${current.getMonth()+1}`);
    const data = await res.json();
    monthData = data.days || {};
    tdee = data.tdee;
    renderCalendar();
}

function renderCalendar() {
    const grid = document.getElementById('cal-grid');
    grid.querySelectorAll('.cal-day, .cal-day-skeleton').forEach(d => d.remove());

    const months = ['January','February','March','April','May','June','July','August','September','October','November','December'];
    document.getElementById('cal-title').textContent = `${months[current.getMonth()]} ${current.getFullYear()}`;

    const first = new Date(current.getFullYear(), current.getMonth(), 1);
    const last = new Date(current.getFullYear(), current.getMonth()+1, 0);
    const startDay = first.getDay();

    for (let i = 0; i < startDay; i++) {
        const d = new Date(first); d.setDate(d.getDate() - (startDay - i));
        grid.appendChild(makeDay(d, true));
    }
    for (let i = 1; i <= last.getDate(); i++) {
        grid.appendChild(makeDay(new Date(current.getFullYear(), current.getMonth(), i), false));
    }
    const remaining = 7 - ((startDay + last.getDate()) % 7);
    if (remaining < 7) {
        for (let i = 1; i <= remaining; i++) {
            const d = new Date(last); d.setDate(d.getDate() + i);
            grid.appendChild(makeDay(d, true));
        }
    }
}

function makeDay(d, other) {
    const div = document.createElement('div');
    const key = fmt(d);
    const isToday = d.toDateString() === today.toDateString();
    const dayData = monthData[key];
    const kcal = dayData ? dayData.kcal : 0;

    const classes = ['cal-day'];
    let status = null;

    if (other) {
        classes.push('other-month');
    } else if (dayData) {
        if (tdee) {
            const ratio = kcal / tdee;
            status = (ratio >= 0.9 && ratio <= 1.1) ? 'target'
                   : (ratio > 1.1) ? 'surplus' : 'deficit';
            classes.push(`status-${status}`);
        } else {
            classes.push('status-nodata');
        }
    }
    if (isToday) classes.push('today');

    div.className = classes.join(' ');

    const numDiv = document.createElement('div');
    numDiv.className = 'cal-day-num';
    numDiv.textContent = d.getDate();
    div.appendChild(numDiv);

    if (!other && dayData) {
        const kcalDiv = document.createElement('div');
        kcalDiv.className = 'cal-day-kcal';
        kcalDiv.textContent = `${Math.round(kcal)} kcal`;
        div.appendChild(kcalDiv);

        if (tdee) {
            const bar = document.createElement('div');
            bar.className = 'cal-day-bar';
            const fill = document.createElement('div');
            fill.className = 'cal-day-bar-fill';
            fill.style.width = `${Math.min(100, Math.round((kcal / tdee) * 100))}%`; // dynamic value only
            bar.appendChild(fill);
            div.appendChild(bar);

            const defDiv = document.createElement('div');
            defDiv.className = 'cal-day-diff';
            const diff = Math.round(kcal - tdee);
            defDiv.textContent = diff >= 0 ? `+${diff} surplus` : `${diff} deficit`;
            div.appendChild(defDiv);
        }
    }

    if (!other) div.onclick = () => openModal(d);
    return div;
}

function openModal(d) {
    selectedDate = fmt(d);
    document.getElementById('modal-date-title').textContent = d.toLocaleDateString('en-GB', {weekday:'long', day:'numeric', month:'long', year:'numeric'});
    renderModalEntries();
    document.getElementById('add-form').style.display = 'none';
    document.getElementById('search-results').innerHTML = '';
    document.getElementById('search-input').value = '';
    setType('recipe');
    document.getElementById('day-modal').style.display = 'flex';
}

function renderModalEntries() {
    const dayData = monthData[selectedDate];
    const summary = document.getElementById('modal-summary');
    const entriesDiv = document.getElementById('modal-entries');

    if (dayData && dayData.kcal) {
        let html = `<div style="display:flex; gap:1rem; align-items:center; background:var(--bg-tertiary); border-radius:0.5rem; padding:0.75rem;">`;
        html += `<div><div style="font-size:0.75rem; color:var(--text-secondary);">Consumed</div><div style="font-size:1.25rem; font-weight:500;">${Math.round(dayData.kcal)} kcal</div></div>`;
        if (tdee) {
            const diff = Math.round(dayData.kcal - tdee);
            const color = diff > 0 ? '#f59e0b' : diff < 0 ? '#3b82f6' : '#22c55e';
            html += `<div><div style="font-size:0.75rem; color:var(--text-secondary);">Target</div><div style="font-size:1.25rem; font-weight:500;">${Math.round(tdee)} kcal</div></div>`;
            html += `<div><div style="font-size:0.75rem; color:var(--text-secondary);">Difference</div><div style="font-size:1.25rem; font-weight:500; color:${color};">${diff >= 0 ? '+' : ''}${diff} kcal</div></div>`;
        }
        html += '</div>';
        summary.innerHTML = html;
    } else {
        summary.innerHTML = `<p style="font-size:0.875rem; color:var(--text-secondary);">No entries yet.</p>`;
    }

    if (dayData && dayData.entries && dayData.entries.length) {
        let html = '<div style="display:flex; flex-direction:column; gap:0.5rem;">';
        dayData.entries.forEach(e => {
            const detail = e.servings ? `${e.servings} serving(s)` : e.quantity ? `${e.quantity} ${e.unit || ''}` : '';
            html += `<div style="display:flex; justify-content:space-between; align-items:center; padding:0.5rem 0.75rem; background:color-mix(in srgb, var(--mint) 60%, white); border-radius:0.5rem;">
                <div>
                    <div class="entry-name">${e.name}</div>
                    <div class="entry-detail">${detail} · ${Math.round(e.kcal)} kcal</div>
                </div>
                <button class="btn btn-secondary btn-small" onclick="openEdit(${JSON.stringify(e).replace(/"/g,'&quot;')})">Edit</button>
            </div>`;
        });
        html += '</div>';
        entriesDiv.innerHTML = html;
    } else {
        entriesDiv.innerHTML = '';
    }
}

function closeModal() {
    document.getElementById('day-modal').style.display = 'none';
    selectedDate = null;
}

function setType(type) {
    addType = type;
    selectedItem = null;
    document.getElementById('add-form').style.display = 'none';
    document.getElementById('search-results').innerHTML = '';
    document.getElementById('search-input').value = '';

    document.getElementById('btn-recipe').classList.toggle('active', type === 'recipe');
    document.getElementById('btn-ingredient').classList.toggle('active', type === 'ingredient');
}

let searchTimeout;
function doSearch(q) {
    clearTimeout(searchTimeout);
    if (!q) { document.getElementById('search-results').innerHTML = ''; return; }
    searchTimeout = setTimeout(async () => {
        const res = await fetch(`/planner/calendar/search/?kind=${addType}&q=${encodeURIComponent(q)}`);
        const data = await res.json();
        const div = document.getElementById('search-results');
        if (!data.results.length) { div.innerHTML = '<p class="search-no-results">No results</p>'; return; }
        div.innerHTML = data.results.map(r =>
            `<div class="search-result-item" onclick='selectItem(${JSON.stringify(r).replace(/'/g,"&#39;")})'>${r.name}</div>`
        ).join('');
    }, 300);
}

function selectItem(item) {
    selectedItem = item;
    document.getElementById('selected-name').textContent = item.name;
    document.getElementById('search-results').innerHTML = '';
    document.getElementById('search-input').value = item.name;

    if (addType === 'recipe') {
        document.getElementById('recipe-fields').style.display = 'block';
        document.getElementById('ingredient-fields').style.display = 'none';
        document.getElementById('input-servings').value = item.servings || 1;
    } else {
        document.getElementById('recipe-fields').style.display = 'none';
        document.getElementById('ingredient-fields').style.display = 'block';
        const select = document.getElementById('input-unit');
        select.innerHTML = item.units.map(u => `<option value="${u['unit__id']}">${u['unit__name_singular']}</option>`).join('');
    }
    document.getElementById('add-form').style.display = 'block';
}

async function submitAdd() {
    if (!selectedItem) return;
    const body = { date: selectedDate, type: addType };
    if (addType === 'recipe') {
        body.recipe_id = selectedItem.id;
        body.servings = parseFloat(document.getElementById('input-servings').value);
    } else {
        body.ingredient_id = selectedItem.id;
        body.quantity = parseFloat(document.getElementById('input-quantity').value);
        body.unit_id = parseInt(document.getElementById('input-unit').value);
    }

    const res = await fetch('/planner/calendar/add/', {
        method: 'POST',
        headers: {'X-CSRFToken': CSRF, 'Content-Type': 'application/json'},
        body: JSON.stringify(body)
    });
    const result = await res.json();
    if (result.error) {
        alert(result.error); // or swap for a nicer inline message
        return;
    }

    await loadMonth();
    renderModalEntries();
    document.getElementById('add-form').style.display = 'none';
    document.getElementById('search-input').value = '';
    selectedItem = null;
}

function openEdit(entry) {
    editingEntry = entry;
    document.getElementById('edit-title').textContent = entry.name;
    const fields = document.getElementById('edit-fields');
    if (entry.servings !== null) {
        fields.innerHTML = `<label style="font-size:0.8rem;">Servings</label><input type="number" id="edit-val" min="0.1" step="0.1" value="${entry.servings}" style="width:100%; margin-top:4px;">`;
    } else {
        fields.innerHTML = `<label style="font-size:0.8rem;">Quantity</label><input type="number" id="edit-val" min="0.01" step="0.01" value="${entry.quantity}" style="width:100%; margin-top:4px;">`;
    }
    document.getElementById('edit-modal').style.display = 'flex';
}

function closeEdit() {
    document.getElementById('edit-modal').style.display = 'none';
    editingEntry = null;
}

async function submitEdit() {
    const val = parseFloat(document.getElementById('edit-val').value);
    const body = editingEntry.servings !== null ? { servings: val } : { quantity: val };

    const res = await fetch(`/planner/calendar/edit/${editingEntry.id}/`, {
        method: 'POST',
        headers: {'X-CSRFToken': CSRF, 'Content-Type': 'application/json'},
        body: JSON.stringify(body)
    });
    const result = await res.json();
    if (result.error) {
        alert(result.error);
        return;
    }

    closeEdit();
    await loadMonth();
    renderModalEntries();
}

async function submitDelete() {
    await fetch(`/planner/calendar/delete/${editingEntry.id}/`, { method:'POST', headers:{'X-CSRFToken':CSRF,'Content-Type':'application/json'}, body:'{}' });
    closeEdit();
    await loadMonth();
    renderModalEntries();
}

function changeMonth(dir) {
    current.setMonth(current.getMonth() + dir);
    loadMonth();
}

function goToday() {
    current = new Date();
    loadMonth();
}

function renderSkeleton() {
    const grid = document.getElementById('cal-grid');
    grid.querySelectorAll('.cal-day, .cal-day-skeleton').forEach(d => d.remove());
    for (let i = 0; i < 35; i++) {
        const div = document.createElement('div');
        div.className = 'cal-day-skeleton';
        grid.appendChild(div);
    }
}
document.getElementById('day-modal').addEventListener('click', e => { if (e.target === document.getElementById('day-modal')) closeModal(); });
document.getElementById('edit-modal').addEventListener('click', e => { if (e.target === document.getElementById('edit-modal')) closeEdit(); });

loadMonth();
