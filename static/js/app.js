const API_BASE = (window.location.protocol === 'file:' || (window.location.port && window.location.port !== '8000'))
    ? 'http://127.0.0.1:8000/api/v1'
    : '/api/v1';
let authToken = localStorage.getItem('access_token') || null;
let currentUser = JSON.parse(localStorage.getItem('user_data')) || null;
let currentFolder = '/';

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
    fetchPasswordRequirements();
    if (authToken && currentUser) {
        showDashboardView();
    } else {
        showAuthView();
    }
});

// Toast Notifications
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let iconClass = 'fa-circle-info';
    if (type === 'success') iconClass = 'fa-circle-check';
    if (type === 'error') iconClass = 'fa-circle-exclamation';

    toast.innerHTML = `<i class="fa-solid ${iconClass}"></i> <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Heartbeat & Online Status Loop
let heartbeatInterval = null;

function startHeartbeat() {
    if (heartbeatInterval) clearInterval(heartbeatInterval);
    sendHeartbeat();
    heartbeatInterval = setInterval(sendHeartbeat, 20000);
}

function stopHeartbeat() {
    if (heartbeatInterval) clearInterval(heartbeatInterval);
    heartbeatInterval = null;
}

async function sendHeartbeat() {
    if (!authToken) return;
    try {
        await fetch(`${API_BASE}/users/me/heartbeat`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
    } catch (e) {}
}

// Views Navigation
function showAuthView() {
    stopHeartbeat();
    document.getElementById('view-auth').classList.add('active');
    document.getElementById('view-dashboard').classList.remove('active');
    document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'none');
    document.querySelectorAll('.student-only-btn').forEach(el => el.style.display = 'inline-flex');
    document.querySelectorAll('.admin-only-btn').forEach(el => el.style.display = 'none');
    updateNavActions();
}

function showDashboardView() {
    document.getElementById('view-auth').classList.remove('active');
    document.getElementById('view-dashboard').classList.add('active');
    
    if (currentUser && currentUser.role === 'ADMIN') {
        document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'block');
        document.querySelectorAll('.student-only-btn').forEach(el => el.style.display = 'none');
        document.querySelectorAll('.admin-only-btn').forEach(el => el.style.display = 'flex');
    } else {
        document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'none');
        document.querySelectorAll('.student-only-btn').forEach(el => el.style.display = 'inline-flex');
        document.querySelectorAll('.admin-only-btn').forEach(el => el.style.display = 'none');
    }

    updateUserHeaderUI();
    loadUserFiles();
    startHeartbeat();
}

function updateNavActions() {
    updateUserHeaderUI();
}

// Auth Tab Switch
function switchAuthTab(tab) {
    document.getElementById('tab-login-btn').classList.toggle('active', tab === 'login');
    document.getElementById('tab-register-btn').classList.toggle('active', tab === 'register');
    document.getElementById('form-login').classList.toggle('active', tab === 'login');
    document.getElementById('form-register').classList.toggle('active', tab === 'register');
}

function fillDemo(email, password) {
    switchAuthTab('login');
    document.getElementById('login-email').value = email;
    document.getElementById('login-password').value = password;
}

// Auth Operations
async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;

    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Login failed');

        authToken = data.access_token;
        currentUser = data.user;
        localStorage.setItem('access_token', authToken);
        localStorage.setItem('user_data', JSON.stringify(currentUser));

        showToast(`Welcome back, ${currentUser.name}!`, 'success');
        showDashboardView();
    } catch (err) {
        const msg = (err.message === 'Failed to fetch' || err.name === 'TypeError')
            ? 'Cannot connect to backend server. Please make sure py -m app.main is running on http://127.0.0.1:8000'
            : err.message;
        showToast(msg, 'error');
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const name = document.getElementById('reg-name').value;
    const email = document.getElementById('reg-email').value;
    const username = document.getElementById('reg-username').value || null;
    const password = document.getElementById('reg-password').value;
    const confirm_password = document.getElementById('reg-confirm-password').value;
    const role = document.getElementById('reg-role').value;

    try {
        const res = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, username, password, confirm_password, role })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Registration failed');

        showToast('Registration successful! Please sign in.', 'success');
        switchAuthTab('login');
        fillDemo(email, password);
    } catch (err) {
        const msg = (err.message === 'Failed to fetch' || err.name === 'TypeError')
            ? 'Cannot connect to backend server. Please make sure py -m app.main is running on http://127.0.0.1:8000'
            : err.message;
        showToast(msg, 'error');
    }
}

function handleLogout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_data');
    showToast('Logged out successfully', 'info');
    showAuthView();
}

// Helper: HTML Escaping
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Dashboard Tabs
function switchDashboardTab(tab) {
    document.querySelectorAll('.dash-tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.dash-tab-content').forEach(content => content.classList.remove('active'));

    const tabBtn = document.getElementById(`tab-${tab}`);
    const contentBox = document.getElementById(`content-${tab}`);
    if (tabBtn) tabBtn.classList.add('active');
    if (contentBox) contentBox.classList.add('active');

    if (tab === 'files') loadUserFiles();
    if (tab === 'shared') loadSharedFiles();
    if (tab === 'logs') loadAuditLogs();
    if (tab === 'trash') loadTrashFiles();
    if (tab === 'admin') loadAdminStats();
}

// Breadcrumbs & Folder Navigation
function renderBreadcrumbs() {
    const container = document.getElementById('breadcrumb-bar');
    if (!container) return;

    const parts = currentFolder.split('/').filter(p => p.length > 0);
    let html = `
        <span style="cursor: pointer; color: var(--accent-blue, #38bdf8); font-weight: 500;" onclick="navigateToFolder('/')">
            <i class="fa-solid fa-house"></i> Home
        </span>
    `;

    let accumulatedPath = '';
    for (let i = 0; i < parts.length; i++) {
        accumulatedPath += '/' + parts[i];
        const folderName = parts[i];
        const isLast = (i === parts.length - 1);

        html += ` <span style="color: var(--text-muted, #94a3b8); margin: 0 0.25rem;">/</span> `;
        if (isLast) {
            html += `<span style="font-weight: 600; color: var(--text-main, #f8fafc);"><i class="fa-solid fa-folder-open text-primary"></i> ${escapeHtml(folderName)}</span>`;
        } else {
            const pathEscaped = accumulatedPath.replace(/'/g, "\\'");
            html += `<span style="cursor: pointer; color: var(--accent-blue, #38bdf8);" onclick="navigateToFolder('${pathEscaped}')">${escapeHtml(folderName)}</span>`;
        }
    }

    container.innerHTML = html;
}

function navigateToFolder(folderPath) {
    currentFolder = folderPath || '/';
    loadUserFiles();
}

// Files Operations
async function loadUserFiles() {
    const searchInput = document.getElementById('file-search');
    const sortSelect = document.getElementById('file-sort');
    const search = searchInput ? searchInput.value : '';
    const sortBy = sortSelect ? sortSelect.value : 'date_desc';
    const tbody = document.getElementById('files-table-body');
    if (!tbody) return;

    renderBreadcrumbs();
    tbody.innerHTML = `<tr><td colspan="5" class="text-center">Loading contents...</td></tr>`;

    try {
        // Fetch Subfolders
        const folderUrl = new URL(`${window.location.origin.replace(/\/$/, '')}${API_BASE}/files/folders`);
        folderUrl.searchParams.append('parent_folder', currentFolder);

        const folderRes = await fetch(folderUrl, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        let subfolders = [];
        if (folderRes.ok) {
            subfolders = await folderRes.json();
        }

        // Fetch Files
        const fileUrl = new URL(`${window.location.origin.replace(/\/$/, '')}${API_BASE}/files`);
        fileUrl.searchParams.append('folder', currentFolder);
        if (search) fileUrl.searchParams.append('search', search);
        if (sortBy) fileUrl.searchParams.append('sort_by', sortBy);

        const res = await fetch(fileUrl, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (res.status === 401) {
            handleLogout();
            showToast('Session expired. Please log in again.', 'error');
            return;
        }

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || 'Failed to load files');
        }

        const files = await res.json();

        if ((!subfolders || subfolders.length === 0) && (!files || files.length === 0)) {
            tbody.innerHTML = `<tr><td colspan="5" class="text-center subtext">Folder '${escapeHtml(currentFolder)}' is empty. Upload a file or create a subfolder above!</td></tr>`;
            return;
        }

        let rowsHtml = '';

        // Render Folder Rows first
        if (subfolders && subfolders.length > 0 && !search) {
            subfolders.forEach(folder => {
                const safeFolderName = escapeHtml(folder.name);
                const jsPath = folder.path.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
                rowsHtml += `
                    <tr style="background: rgba(56, 189, 248, 0.04); cursor: pointer;" onclick="navigateToFolder('${jsPath}')">
                        <td>
                            <div style="display:flex; align-items:center; gap:0.6rem;">
                                <i class="fa-solid fa-folder text-warning" style="font-size: 1.1rem; color: #f59e0b;"></i>
                                <strong>${safeFolderName}</strong>
                            </div>
                        </td>
                        <td>--</td>
                        <td><span class="badge badge-warning">Folder</span></td>
                        <td>${new Date(folder.created_at).toLocaleString()}</td>
                        <td>
                            <button class="btn btn-sm btn-outline" onclick="event.stopPropagation(); navigateToFolder('${jsPath}')" title="Open Folder">
                                <i class="fa-solid fa-folder-open"></i> Open
                            </button>
                        </td>
                    </tr>
                `;
            });
        }

        // Render File Rows
        if (files && files.length > 0) {
            files.forEach(file => {
                const safeName = escapeHtml(file.original_name || 'Unnamed File');
                const safeMime = escapeHtml((file.mime_type || '').split('/')[1] || 'binary');
                const jsEscapedName = (file.original_name || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
                const jsEscapedFolder = (file.folder || '/').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
                rowsHtml += `
                    <tr>
                        <td><strong><i class="fa-solid fa-file-shield text-primary"></i> ${safeName}</strong></td>
                        <td>${formatBytes(file.file_size)}</td>
                        <td><span class="badge">${safeMime}</span></td>
                        <td>${new Date(file.created_at).toLocaleString()}</td>
                        <td>
                            <div class="demo-btn-group">
                                <button class="btn btn-sm btn-outline" onclick="previewVaultFile(${file.id}, '${jsEscapedName}')" title="View / Preview Online"><i class="fa-solid fa-eye"></i></button>
                                <button class="btn btn-sm btn-outline" onclick="downloadFile(${file.id}, '${jsEscapedName}')" title="Download & Decrypt"><i class="fa-solid fa-download"></i></button>
                                <button class="btn btn-sm btn-outline" onclick="openShareModal(${file.id}, '${jsEscapedName}')" title="Share Access"><i class="fa-solid fa-share-nodes"></i></button>
                                <button class="btn btn-sm btn-outline" onclick="openMoveModal(${file.id}, '${jsEscapedName}', '${jsEscapedFolder}')" title="Move File"><i class="fa-solid fa-folder-tree"></i></button>
                                <button class="btn btn-sm btn-outline" onclick="openRenameModal(${file.id}, '${jsEscapedName}')" title="Rename"><i class="fa-solid fa-pen"></i></button>
                                <button class="btn btn-sm btn-danger" onclick="deleteFile(${file.id})" title="Delete"><i class="fa-solid fa-trash"></i></button>
                            </div>
                        </td>
                    </tr>
                `;
            });
        }

        tbody.innerHTML = rowsHtml;
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center text-danger">${escapeHtml(err.message)}</td></tr>`;
    }
}

let searchTimer;
function debounceSearch() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(loadUserFiles, 300);
}

// Drag & Drop File Upload
const dropzone = document.getElementById('dropzone');
if (dropzone) {
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.style.background = 'rgba(56, 189, 248, 0.15)';
    });
    dropzone.addEventListener('dragleave', () => {
        dropzone.style.background = '';
    });
    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.style.background = '';
        if (e.dataTransfer.files.length) {
            uploadSelectedFile(e.dataTransfer.files[0]);
        }
    });
}

function handleFileSelect(e) {
    if (e.target.files.length) {
        uploadSelectedFile(e.target.files[0]);
    }
}

async function uploadSelectedFile(file) {
    showToast(`Encrypting & uploading '${file.name}' into ${currentFolder}...`, 'info');
    const formData = new FormData();
    formData.append('file', file);
    formData.append('folder', currentFolder);

    try {
        const res = await fetch(`${API_BASE}/files/upload`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` },
            body: formData
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Upload failed');

        showToast(`File '${file.name}' uploaded and AES-256 encrypted successfully!`, 'success');
        const fileInput = document.getElementById('file-input');
        if (fileInput) fileInput.value = '';
        const searchInput = document.getElementById('file-search');
        if (searchInput) searchInput.value = '';
        loadUserFiles();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// File Download
async function downloadFile(fileId, filename) {
    showToast(`Decrypting & downloading '${filename}'...`, 'info');
    try {
        const res = await fetch(`${API_BASE}/files/${fileId}/download`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || 'Download failed');
        }

        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast(`File decrypted successfully!`, 'success');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// Rename & Delete File
function openRenameModal(id, name) {
    document.getElementById('rename-file-id').value = id;
    document.getElementById('rename-input').value = name;
    document.getElementById('modal-rename').classList.add('active');
}

async function submitRenameForm() {
    const id = document.getElementById('rename-file-id').value;
    const new_name = document.getElementById('rename-input').value;

    try {
        const res = await fetch(`${API_BASE}/files/${id}/rename`, {
            method: 'PUT',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ new_name })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Rename failed');

        showToast('File renamed successfully', 'success');
        closeModal('modal-rename');
        loadUserFiles();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function deleteFile(id) {
    if (!confirm('Are you sure you want to move this file to the Recycle Bin?')) return;
    try {
        const res = await fetch(`${API_BASE}/files/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!res.ok) throw new Error('Failed to move file to Recycle Bin');
        showToast('File moved to Recycle Bin', 'info');
        loadUserFiles();
        if (typeof loadTrashFiles === 'function') loadTrashFiles();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// Sharing Operations
let lastGeneratedShareUrl = '';

function generateAndSetSharePassword() {
    const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*';
    let pwd = '';
    for (let i = 0; i < 12; i++) {
        pwd += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    const pwdInput = document.getElementById('share-password');
    if (pwdInput) pwdInput.value = pwd;
    showToast('Secure share password generated', 'info');
}

function copySharePassword() {
    const pwdInput = document.getElementById('share-password');
    if (pwdInput && pwdInput.value) {
        navigator.clipboard.writeText(pwdInput.value);
        showToast('Share password copied to clipboard!', 'success');
    } else {
        showToast('No password generated to copy', 'error');
    }
}

function toggleSharePasswordVisibility(checked) {
    const pwdContainer = document.getElementById('share-password-container');
    if (pwdContainer) pwdContainer.style.display = checked ? 'block' : 'none';
    if (checked && !document.getElementById('share-password').value) {
        generateAndSetSharePassword();
    }
}

function handleExpiryPresetSelectChange(val) {
    const customContainer = document.getElementById('share-custom-date-container');
    const expiryHoursInput = document.getElementById('share-expiry-hours');
    if (val === 'custom') {
        if (customContainer) customContainer.style.display = 'block';
        if (expiryHoursInput) expiryHoursInput.value = '';
    } else {
        if (customContainer) customContainer.style.display = 'none';
        if (expiryHoursInput) expiryHoursInput.value = val === 'null' ? '' : val;
    }
}

function setExpiryPreset(hours, btn) {
    document.querySelectorAll('.expiry-preset-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    document.getElementById('share-expiry-hours').value = hours !== null ? hours : '';
    const customContainer = document.getElementById('share-custom-date-container');
    if (customContainer) customContainer.style.display = 'none';
}

function toggleCustomDateExpiry(btn) {
    document.querySelectorAll('.expiry-preset-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    document.getElementById('share-expiry-hours').value = '';
    const customContainer = document.getElementById('share-custom-date-container');
    if (customContainer) customContainer.style.display = 'block';
}

function setDownloadPreset(count, btn) {
    document.querySelectorAll('.download-preset-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    document.getElementById('share-max-downloads').value = count !== null ? count : '';
}

let userSearchTimer;
function handleUserSearchInput(val) {
    clearTimeout(userSearchTimer);
    const resultsBox = document.getElementById('share-user-results');
    if (!resultsBox) return;
    
    if (!val || val.trim().length < 1) {
        resultsBox.style.display = 'none';
        return;
    }

    userSearchTimer = setTimeout(async () => {
        try {
            const res = await fetch(`${API_BASE}/users/search?q=${encodeURIComponent(val)}`, {
                headers: { 'Authorization': `Bearer ${authToken}` }
            });
            if (!res.ok) return;
            const users = await res.json();
            if (!users || users.length === 0) {
                resultsBox.style.display = 'none';
                return;
            }

            resultsBox.innerHTML = users.map(u => {
                const isOnline = u.is_online;
                const statusDotClass = isOnline ? 'online' : 'offline';
                const statusText = u.last_seen_text || (isOnline ? 'Active now' : 'Offline');
                const pillClass = isOnline ? 'online' : 'offline';
                const initials = getInitials(u.name);

                return `
                    <div style="padding: 10px 14px; cursor: pointer; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 0.85rem; display: flex; align-items: center; justify-content: space-between;" 
                         onclick="selectUserSearchItem('${escapeHtml(u.email)}')">
                        <div style="display: flex; align-items: center; gap: 0.65rem;">
                            <div class="avatar-wrapper">
                                <div class="avatar-circle" style="width: 32px; height: 32px; font-size: 0.8rem;">
                                    <span>${escapeHtml(initials)}</span>
                                </div>
                                <span class="status-dot ${statusDotClass}" title="${escapeHtml(statusText)}"></span>
                            </div>
                            <div>
                                <strong style="display: block; line-height: 1.2; color: var(--text-primary);">${escapeHtml(u.name)}</strong>
                                <span class="subtext" style="font-size: 0.75rem;">${escapeHtml(u.email)}</span>
                            </div>
                        </div>
                        <span class="online-pill ${pillClass}">
                            <span class="dot"></span> ${escapeHtml(statusText)}
                        </span>
                    </div>
                `;
            }).join('');
            resultsBox.style.display = 'block';
        } catch (e) {
            resultsBox.style.display = 'none';
        }
    }, 200);
}

let registeredStudentsCache = [];

async function loadRegisteredStudentsDirectory() {
    const badge = document.getElementById('share-students-count-badge');
    if (badge) badge.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Loading...`;

    try {
        const res = await fetch(`${API_BASE}/users/students`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!res.ok) throw new Error('Failed to load students directory');
        const data = await res.json();
        registeredStudentsCache = data.students || [];

        if (badge) {
            badge.innerHTML = `<i class="fa-solid fa-user-graduate"></i> ${data.total_registered_count || (registeredStudentsCache.length + 1)} Students`;
        }

        renderShareClientAutocomplete(registeredStudentsCache);
    } catch (err) {
        if (badge) badge.innerHTML = `<i class="fa-solid fa-user-graduate"></i> Directory ready`;
    }
}

function renderShareClientAutocomplete(list) {
    const dropdown = document.getElementById('share-client-autocomplete-list');
    if (!dropdown) return;

    if (!list || list.length === 0) {
        dropdown.innerHTML = `
            <div style="padding: 0.75rem; text-align: center; color: var(--text-muted); font-size: 0.8rem;">
                <i class="fa-solid fa-user-slash"></i> No matching registered clients found.
            </div>
        `;
        return;
    }

    let itemsHtml = `
        <div class="share-client-item" onclick="selectSharePublicShare()" style="background: rgba(37, 99, 235, 0.08); margin-bottom: 0.25rem;">
            <div class="share-client-avatar" style="background: linear-gradient(135deg, #10b981, #059669);"><i class="fa-solid fa-globe"></i></div>
            <div class="share-client-info">
                <div class="share-client-name" style="color: #34d399;">🌐 Public Share (Anyone with Link / Code)</div>
                <div class="share-client-email">No specific recipient restriction</div>
            </div>
            <span class="badge" style="font-size: 0.65rem;">Public</span>
        </div>
    `;

    itemsHtml += list.map(student => {
        const isOnline = student.is_online;
        const jsEscapedName = escapeHtml(student.name).replace(/'/g, "\\'");
        const jsEscapedEmail = escapeHtml(student.email).replace(/'/g, "\\'");

        return `
            <div class="share-client-item" onclick="selectShareClientRecipient('${jsEscapedEmail}', '${jsEscapedName}')">
                <div class="share-client-avatar">
                    ${escapeHtml((student.name || 'U').charAt(0).toUpperCase())}
                </div>
                <div class="share-client-info">
                    <div class="share-client-name">${escapeHtml(student.name)} <span class="subtext">(@${escapeHtml(student.username || 'user')})</span></div>
                    <div class="share-client-email">${escapeHtml(student.email)}</div>
                </div>
                <span class="online-pill ${isOnline ? 'online' : 'offline'}" style="font-size: 0.68rem; padding: 1px 6px;">
                    <span class="dot"></span> ${escapeHtml(student.last_seen_text || 'Offline')}
                </span>
            </div>
        `;
    }).join('');

    dropdown.innerHTML = itemsHtml;
}

function onShareClientSearchInput(query) {
    const q = (query || '').toLowerCase().trim();
    const clearBtn = document.getElementById('share-client-clear-btn');
    if (clearBtn) clearBtn.style.display = q ? 'block' : 'none';

    const filtered = !q 
        ? registeredStudentsCache 
        : registeredStudentsCache.filter(s => 
            (s.name || '').toLowerCase().includes(q) || 
            (s.email || '').toLowerCase().includes(q) || 
            (s.username || '').toLowerCase().includes(q)
        );

    renderShareClientAutocomplete(filtered);
    showShareClientDropdown();
}

function showShareClientDropdown() {
    const dropdown = document.getElementById('share-client-autocomplete-list');
    if (dropdown) dropdown.style.display = 'block';
}

function hideShareClientDropdown() {
    const dropdown = document.getElementById('share-client-autocomplete-list');
    if (dropdown) dropdown.style.display = 'none';
}

// Close search dropdown on click outside
document.addEventListener('click', (e) => {
    const dropdown = document.getElementById('share-client-autocomplete-list');
    if (dropdown && dropdown.style.display === 'block') {
        if (!e.target.closest('#modal-share .search-input-wrapper') && !e.target.closest('#share-client-autocomplete-list')) {
            hideShareClientDropdown();
        }
    }
});

function selectShareClientRecipient(email, name) {
    const hiddenInput = document.getElementById('share-recipient');
    if (hiddenInput) hiddenInput.value = email;

    const searchInput = document.getElementById('share-client-search-input');
    if (searchInput) searchInput.value = name || email;

    const card = document.getElementById('share-selected-client-card');
    const nameEl = document.getElementById('share-selected-client-name');
    const emailEl = document.getElementById('share-selected-client-email');
    const publicNotice = document.getElementById('share-public-mode-notice');
    const clearBtn = document.getElementById('share-client-clear-btn');

    if (nameEl) nameEl.textContent = name || email;
    if (emailEl) emailEl.textContent = `(${email})`;
    if (card) card.style.display = 'flex';
    if (publicNotice) publicNotice.style.display = 'none';
    if (clearBtn) clearBtn.style.display = 'block';

    hideShareClientDropdown();
}

function selectSharePublicShare() {
    clearShareRecipientSelection();
}

function clearShareRecipientSelection() {
    const hiddenInput = document.getElementById('share-recipient');
    if (hiddenInput) hiddenInput.value = '';

    const searchInput = document.getElementById('share-client-search-input');
    if (searchInput) searchInput.value = '';

    const card = document.getElementById('share-selected-client-card');
    const publicNotice = document.getElementById('share-public-mode-notice');
    const clearBtn = document.getElementById('share-client-clear-btn');

    if (card) card.style.display = 'none';
    if (publicNotice) publicNotice.style.display = 'block';
    if (clearBtn) clearBtn.style.display = 'none';

    renderShareClientAutocomplete(registeredStudentsCache);
    hideShareClientDropdown();
}

function openShareModal(id, name) {
    document.getElementById('share-file-id').value = id;
    document.getElementById('share-file-name').textContent = name;
    clearShareRecipientSelection();
    loadRegisteredStudentsDirectory();
    document.getElementById('share-permission').value = 'DOWNLOAD';
    document.getElementById('share-expiry-preset-select').value = '24';
    document.getElementById('share-expiry-hours').value = '24';
    
    // Default download limit to Unlimited
    const presetBtns = document.querySelectorAll('.download-preset-btn');
    if (presetBtns && presetBtns.length >= 4) {
        setDownloadPreset(null, presetBtns[3]);
    } else if (presetBtns && presetBtns.length > 0) {
        setDownloadPreset(null, presetBtns[0]);
    }
    
    const reqPwdCheckbox = document.getElementById('share-requires-password');
    if (reqPwdCheckbox) {
        reqPwdCheckbox.checked = false;
        toggleSharePasswordVisibility(false);
    }
    const pwdInput = document.getElementById('share-password');
    if (pwdInput) pwdInput.value = '';

    const customDateContainer = document.getElementById('share-custom-date-container');
    if (customDateContainer) customDateContainer.style.display = 'none';

    document.getElementById('share-result-container').style.display = 'none';
    const submitBtn = document.getElementById('btn-submit-share');
    if (submitBtn) {
        submitBtn.innerHTML = '<i class="fa-solid fa-link"></i> Create Share Link';
        submitBtn.disabled = false;
    }
    document.getElementById('modal-share').classList.add('active');
}

async function submitShareForm() {
    const file_id = parseInt(document.getElementById('share-file-id').value);
    const target_user_identifier = document.getElementById('share-recipient') ? document.getElementById('share-recipient').value.trim() : '';
    const permission = document.getElementById('share-permission').value;
    
    let expiry_hours = document.getElementById('share-expiry-hours').value ? parseInt(document.getElementById('share-expiry-hours').value) : null;
    let expiry_date = null;
    const customDateInput = document.getElementById('share-custom-date-input');
    if (customDateInput && customDateInput.value) {
        expiry_date = new Date(customDateInput.value).toISOString();
    }

    const max_downloads = document.getElementById('share-max-downloads').value ? parseInt(document.getElementById('share-max-downloads').value) : null;
    const requires_password = document.getElementById('share-requires-password') ? document.getElementById('share-requires-password').checked : false;
    const password = requires_password ? (document.getElementById('share-password').value || null) : null;

    const submitBtn = document.getElementById('btn-submit-share');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Creating...';
    }

    try {
        const res = await fetch(`${API_BASE}/shares`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                file_id,
                target_user_identifier: target_user_identifier || null,
                permission,
                expiry_hours,
                expiry_date,
                max_downloads,
                password,
                requires_otp: false,
                requires_password,
                one_time_access: false
            })
        });

        let data;
        try {
            data = await res.json();
        } catch (jsonErr) {
            throw new Error(`Server error (${res.status}). Please try again.`);
        }
        if (!res.ok) throw new Error(data.detail || 'Share creation failed');

        const shareToken = data.share_token || (data.share_code || '');
        lastGeneratedShareUrl = `${window.location.origin}/#share/${shareToken}`;
        lastGeneratedShareCode = data.share_code || (data.share_token ? data.share_token.slice(0, 6).toUpperCase() : '');

        const urlInput = document.getElementById('share-generated-url');
        if (urlInput) urlInput.value = lastGeneratedShareUrl;

        const openLinkBtn = document.getElementById('share-open-link-btn');
        if (openLinkBtn) openLinkBtn.href = lastGeneratedShareUrl;

        const codeBadge = document.getElementById('share-generated-code');
        if (codeBadge) codeBadge.textContent = lastGeneratedShareCode || '------';

        document.getElementById('share-result-container').style.display = 'block';

        if (data.generated_password && document.getElementById('share-password')) {
            document.getElementById('share-password').value = data.generated_password;
        }

        showToast(data.message || 'Share link and code created successfully!', 'success');
        loadSharedFiles();
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fa-solid fa-link"></i> Create Share Link';
        }
    }
}

let lastGeneratedShareCode = '';

function copyShareGeneratedCode() {
    if (lastGeneratedShareCode) {
        navigator.clipboard.writeText(lastGeneratedShareCode);
        showToast(`Share Code "${lastGeneratedShareCode}" copied!`, 'success');
    } else {
        showToast('No share code available to copy', 'error');
    }
}

function copyShareGeneratedLink() {
    const urlInput = document.getElementById('share-generated-url');
    if (urlInput && urlInput.value) {
        navigator.clipboard.writeText(urlInput.value);
        showToast('Share link copied to clipboard!', 'success');
    }
}

function openEnterCodeModal() {
    const input = document.getElementById('enter-share-code-input');
    if (input) {
        input.value = '';
        setTimeout(() => input.focus(), 150);
    }
    document.getElementById('modal-enter-code').classList.add('active');
}

function submitEnterCodeForm(e) {
    if (e) e.preventDefault();
    const input = document.getElementById('enter-share-code-input');
    if (!input || !input.value.trim()) return;

    const code = input.value.trim();
    closeModal('modal-enter-code');
    window.location.hash = `#share/${encodeURIComponent(code)}`;
    openTokenShareView(code);
}

function showShareQRCode() {
    if (lastGeneratedShareUrl) {
        openQRCodeModal(lastGeneratedShareUrl);
    }
}

function openQRCodeModal(url) {
    const display = document.getElementById('qr-code-display');
    const textLabel = document.getElementById('qr-code-url-text');
    if (!display) return;

    display.innerHTML = '';
    textLabel.textContent = url;
    
    // Quick SVG QR renderer or Google Chart API fallback if needed
    const qrApiUrl = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(url)}`;
    display.innerHTML = `<img src="${qrApiUrl}" alt="QR Code" style="width: 200px; height: 200px; display: block;" onerror="this.onerror=null; this.src='https://chart.googleapis.com/chart?cht=qr&chs=200x200&chl=${encodeURIComponent(url)}';">`;
    document.getElementById('modal-qr-code').classList.add('active');
}

function copyQRShareLink() {
    const textLabel = document.getElementById('qr-code-url-text');
    if (textLabel && textLabel.textContent) {
        navigator.clipboard.writeText(textLabel.textContent);
        showToast('Link copied to clipboard!', 'success');
    }
}

// Shared Files Management
async function loadSharedFiles() {
    loadReceivedShares();
    loadCreatedShares();
}

async function loadReceivedShares() {
    const tbody = document.getElementById('shared-table-body');
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="6" class="text-center">Loading shared files...</td></tr>`;

    try {
        const res = await fetch(`${API_BASE}/shares/received`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (res.status === 401) {
            handleLogout();
            showToast('Session expired. Please log in again.', 'error');
            return;
        }

        if (!res.ok) throw new Error('Failed to load shared files');
        const shares = await res.json();

        if (!shares || shares.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center subtext">No files have been shared with you yet.</td></tr>`;
            return;
        }

        tbody.innerHTML = shares.map(s => {
            const safeFilename = escapeHtml(s.filename || 'Shared File');
            const safeSharedBy = escapeHtml(s.shared_by_email || 'Unknown');
            const jsEscapedFilename = (s.filename || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");

            const isOnline = s.shared_by_online;
            const statusText = s.shared_by_last_seen || (isOnline ? 'Active now' : 'Offline');
            const pillClass = isOnline ? 'online' : 'offline';
            const userStatusBadge = `<span class="online-pill ${pillClass}" style="margin-left: 0.35rem; vertical-align: middle;"><span class="dot"></span> ${escapeHtml(statusText)}</span>`;

            const isExpired = s.is_expired;
            const isLimitReached = s.max_downloads !== null && s.download_count >= s.max_downloads;
            const canDownload = !isExpired && !isLimitReached && s.permission !== 'VIEW';

            let validityBadge = '<span class="badge badge-success"><i class="fa-solid fa-infinity"></i> Never Expires</span>';
            if (s.expiry_at) {
                const expiryDate = new Date(s.expiry_at);
                const now = new Date();
                if (isExpired) {
                    validityBadge = `<span class="badge badge-danger"><i class="fa-solid fa-clock"></i> Expired</span>`;
                } else {
                    const diffMs = expiryDate - now;
                    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
                    const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
                    if (diffHours > 24) {
                        const days = Math.floor(diffHours / 24);
                        validityBadge = `<span class="badge badge-success"><i class="fa-solid fa-clock"></i> Valid (${days}d left)</span>`;
                    } else if (diffHours > 0) {
                        validityBadge = `<span class="badge badge-warning"><i class="fa-solid fa-clock"></i> Valid (${diffHours}h ${diffMins}m left)</span>`;
                    } else {
                        validityBadge = `<span class="badge badge-warning"><i class="fa-solid fa-clock"></i> Expiring Soon (${diffMins}m left)</span>`;
                    }
                }
            }

            let downloadStatus = `${s.download_count} / ${s.max_downloads !== null ? s.max_downloads : '∞'}`;
            if (isLimitReached) {
                downloadStatus += ` <span class="badge badge-danger">Limit Exceeded</span>`;
            }

            return `
                <tr>
                    <td><strong><i class="fa-solid fa-file-circle-check text-primary"></i> ${safeFilename}</strong></td>
                    <td>${safeSharedBy} ${userStatusBadge}</td>
                    <td><span class="badge">${escapeHtml(s.permission)}</span></td>
                    <td>${validityBadge}</td>
                    <td>${downloadStatus}</td>
                    <td>
                        ${canDownload ? 
                            `<button class="btn btn-sm btn-primary" onclick="downloadSharedFile(${s.id}, '${jsEscapedFilename}')"><i class="fa-solid fa-download"></i> Download</button>` : 
                            `<button class="btn btn-sm btn-outline" disabled><i class="fa-solid fa-lock"></i> Restricted</button>`}
                    </td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">${err.message}</td></tr>`;
    }
}

async function loadCreatedShares() {
    const tbody = document.getElementById('created-shares-table-body');
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="7" class="text-center">Loading sent shares...</td></tr>`;

    try {
        const res = await fetch(`${API_BASE}/shares/created`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (res.status === 401) {
            handleLogout();
            showToast('Session expired. Please log in again.', 'error');
            return;
        }

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || 'Failed to load sent shares');
        }
        const shares = await res.json();

        if (!shares || shares.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-center subtext">You have not shared any files with others yet.</td></tr>`;
            return;
        }

        tbody.innerHTML = shares.map(s => {
            const safeFilename = escapeHtml(s.filename || 'Shared File');
            const safeRecipient = escapeHtml(s.recipient_email || s.shared_with_email || 'Public Link');

            const isOnline = s.shared_with_online;
            const statusText = s.shared_with_last_seen || (isOnline ? 'Active now' : 'Offline');
            const pillClass = isOnline ? 'online' : 'offline';
            const recipientStatusBadge = s.shared_with_email ? `<span class="online-pill ${pillClass}" style="margin-left: 0.35rem; vertical-align: middle;"><span class="dot"></span> ${escapeHtml(statusText)}</span>` : '';

            const isRevoked = s.is_revoked;
            const isExpired = s.is_expired;
            const isLimitReached = s.max_downloads !== null && s.download_count >= s.max_downloads;

            let statusBadge = '<span class="badge badge-success">🟢 Active</span>';
            if (isRevoked) {
                statusBadge = `<span class="badge badge-danger">⚫ Revoked</span>`;
            } else if (isExpired) {
                statusBadge = `<span class="badge badge-danger">🔴 Expired</span>`;
            } else if (isLimitReached) {
                statusBadge = `<span class="badge badge-warning">🟠 Limit Reached</span>`;
            }

            let expiryText = 'Never';
            if (s.expiry_at) {
                const diffMs = new Date(s.expiry_at) - new Date();
                const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
                expiryText = isExpired ? 'Expired' : `${diffHours}h left`;
            }

            // Security indicators
            let secBadges = `<span class="security-tag"><i class="fa-solid fa-shield"></i> AES-256</span>`;
            if (s.requires_otp) secBadges += ` <span class="security-tag otp-tag" title="OTP verification required">OTP ✓</span>`;
            if (s.has_password || s.requires_password) secBadges += ` <span class="security-tag pwd-tag" title="Password protected">Password ✓</span>`;
            if (s.expiry_at) secBadges += ` <span class="security-tag" title="Link expiration active">Expiry ✓</span>`;

            const shareUrl = s.share_url || `${window.location.origin}/#share/${s.share_token}`;

            return `
                <tr>
                    <td><strong><i class="fa-solid fa-share-nodes text-primary"></i> ${safeFilename}</strong></td>
                    <td>${safeRecipient} ${recipientStatusBadge}</td>
                    <td><span class="badge">${escapeHtml(s.permission)}</span></td>
                    <td>${expiryText}</td>
                    <td>${s.download_count} / ${s.max_downloads !== null ? s.max_downloads : '∞'}</td>
                    <td>${secBadges}</td>
                    <td>${statusBadge}</td>
                    <td>
                        <div class="demo-btn-group">
                            <button class="btn btn-sm btn-outline" onclick="openShareDetailsModal(${s.id})" title="View Details & Edit Controls"><i class="fa-solid fa-gear"></i></button>
                            <button class="btn btn-sm btn-outline" onclick="copyDirectShareUrl('${escapeHtml(shareUrl)}')" title="Copy Link"><i class="fa-solid fa-copy"></i></button>
                            ${!isRevoked ? 
                                `<button class="btn btn-sm btn-danger" onclick="revokeShareAccess(${s.id})" title="Revoke Access"><i class="fa-solid fa-user-xmark"></i></button>` : 
                                `<span class="subtext" style="font-size: 0.75rem;">Revoked</span>`}
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">${err.message}</td></tr>`;
    }
}

function copyDirectShareUrl(url) {
    navigator.clipboard.writeText(url);
    showToast('Share link copied to clipboard!', 'success');
}

async function openShareDetailsModal(shareId) {
    try {
        const res = await fetch(`${API_BASE}/shares/${shareId}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!res.ok) throw new Error('Failed to load share details');
        const data = await res.json();

        document.getElementById('details-share-id').value = data.id;
        document.getElementById('details-filename').querySelector('span').textContent = data.filename;
        document.getElementById('details-recipient-info').textContent = `Shared with: ${data.shared_with_email || 'Public Link'}`;
        document.getElementById('details-permission-select').value = data.permission;
        document.getElementById('details-limit-select').value = data.max_downloads !== null ? data.max_downloads.toString() : '';
        document.getElementById('details-expiry-hours').value = '';
        document.getElementById('details-password-input').value = '';
        document.getElementById('details-link-input').value = data.share_url || `${window.location.origin}/#share/${data.share_token}`;

        document.getElementById('modal-share-details').classList.add('active');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function submitUpdateShareDetails() {
    const shareId = document.getElementById('details-share-id').value;
    const permission = document.getElementById('details-permission-select').value;
    const max_downloads_val = document.getElementById('details-limit-select').value;
    const max_downloads = max_downloads_val ? parseInt(max_downloads_val) : null;
    const expiry_hours_val = document.getElementById('details-expiry-hours').value;
    const expiry_hours = expiry_hours_val ? parseInt(expiry_hours_val) : null;
    const password = document.getElementById('details-password-input').value || null;

    try {
        const res = await fetch(`${API_BASE}/shares/${shareId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ permission, max_downloads, expiry_hours, password })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Update failed');
        }

        showToast('Share controls updated successfully!', 'success');
        closeModal('modal-share-details');
        loadSharedFiles();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function submitRevokeFromDetails() {
    const shareId = document.getElementById('details-share-id').value;
    closeModal('modal-share-details');
    await revokeShareAccess(shareId);
}

function copyDetailsLink() {
    const linkInput = document.getElementById('details-link-input');
    if (linkInput && linkInput.value) {
        navigator.clipboard.writeText(linkInput.value);
        showToast('Share link copied to clipboard!', 'success');
    }
}

function showDetailsQRCode() {
    const linkInput = document.getElementById('details-link-input');
    if (linkInput && linkInput.value) {
        openQRCodeModal(linkInput.value);
    }
}

async function revokeShareAccess(shareId) {
    if (!confirm('Are you sure you want to revoke share access for this file? The recipient will no longer be able to download it.')) return;
    try {
        const res = await fetch(`${API_BASE}/shares/${shareId}/revoke`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!res.ok) throw new Error('Failed to revoke share');
        showToast('Share access revoked successfully', 'success');
        loadSharedFiles();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function downloadSharedFile(shareId, filename) {
    showToast(`Validating permissions & downloading '${filename}'...`, 'info');
    try {
        const res = await fetch(`${API_BASE}/shares/${shareId}/download`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || 'Shared download failed');
        }

        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast('Shared file downloaded and decrypted!', 'success');
        loadSharedFiles();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

let otpResendCountdownTimer = null;
let currentShareTokenState = {
    token: null,
    shareData: null,
    otpVerified: false,
    passwordVerified: false,
    passwordInput: null
};

function checkShareTokenHash() {
    const hash = window.location.hash;
    if (hash) {
        let token = '';
        if (hash.startsWith('#share/')) {
            token = hash.replace('#share/', '').trim();
        } else if (hash.startsWith('#/share/')) {
            token = hash.replace('#/share/', '').trim();
        } else if (hash.startsWith('#s/')) {
            token = hash.replace('#s/', '').trim();
        }
        if (token) {
            openTokenShareView(token);
        }
    }
}

async function openTokenShareView(token) {
    const modalBody = document.getElementById('token-share-body');
    if (!modalBody) return;

    modalBody.innerHTML = `<div class="text-center" style="padding: 2.5rem;"><i class="fa-solid fa-shield-cat fa-spin fa-2x text-primary"></i><p style="margin-top: 1rem; color: #94a3b8;">Validating multi-factor security link...</p></div>`;
    document.getElementById('modal-token-share').classList.add('active');

    try {
        const res = await fetch(`${API_BASE}/shares/token/${token}`);
        const data = await res.json();

        if (!res.ok) {
            if (res.status === 401) {
                // Share requires a password!
                currentShareTokenState = {
                    token,
                    shareData: {
                        filename: 'Protected Shared File',
                        shared_by_name: 'File Owner',
                        permission: 'DOWNLOAD',
                        requires_password: true,
                        requires_otp: false
                    },
                    otpVerified: true,
                    passwordVerified: false,
                    passwordInput: null
                };
                renderRecipientVerificationStep();
                return;
            }
            renderAccessDeniedForToken(data.detail || 'Invalid or expired share link');
            return;
        }

        currentShareTokenState = {
            token,
            shareData: data,
            otpVerified: !data.requires_otp,
            passwordVerified: !data.requires_password,
            passwordInput: null
        };

        renderRecipientVerificationStep();
    } catch (err) {
        renderAccessDeniedForToken(err.message || 'Network error connecting to SecureShare server');
    }
}

function renderRecipientVerificationStep() {
    const modalBody = document.getElementById('token-share-body');
    const state = currentShareTokenState;
    const share = state.shareData;

    if (!share) return;

    const safeFilename = escapeHtml(share.filename || 'Shared File');
    const safeSender = escapeHtml(share.shared_by_name || share.shared_by_email || 'Sender');
    const safePermission = escapeHtml(share.permission || 'DOWNLOAD');
    const expiryText = share.expiry_at ? new Date(share.expiry_at).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : 'Never';

    // Step calculations
    const step1Done = true; // Email/Link verification
    const step2Done = !share.requires_otp || state.otpVerified;
    const step3Done = !share.requires_password || state.passwordVerified;

    // Header Card & Stepper
    let html = `
        <div style="padding: 0.25rem;">
            <!-- Main Title & File Summary Card -->
            <div style="background: rgba(30, 58, 95, 0.25); border: 1px solid rgba(56, 189, 248, 0.2); border-radius: 10px; padding: 1.25rem; margin-bottom: 1.25rem;">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
                    <span style="color: #38bdf8; font-weight: 700; font-size: 0.85rem; letter-spacing: 0.5px;">SECURESHARE</span>
                    <span class="badge badge-success"><i class="fa-solid fa-shield-halved"></i> Multi-Factor Security</span>
                </div>
                <h3 style="margin: 0 0 0.5rem 0; font-size: 1.15rem; color: #f8fafc;"><i class="fa-solid fa-file-shield text-primary"></i> ${safeFilename}</h3>
                <div style="display: flex; flex-wrap: wrap; gap: 1rem; font-size: 0.82rem; color: #94a3b8; margin-top: 0.5rem;">
                    <span>Shared by: <strong style="color: #f1f5f9;">${safeSender}</strong></span>
                    <span>Permission: <strong style="color: #38bdf8;">${safePermission}</strong></span>
                    <span>Expires: <strong style="color: #f1f5f9;">${expiryText}</strong></span>
                </div>
            </div>

            ${share.requires_otp ? `
            <!-- Stepper Progress Bar -->
            <div class="stepper-container">
                <div class="stepper-step completed">
                    <div class="stepper-circle"><i class="fa-solid fa-check"></i></div>
                    <span class="stepper-label">Step 1: Link ✓</span>
                </div>

                <div class="stepper-line ${step2Done ? 'active' : ''}"></div>

                <div class="stepper-step ${step2Done ? 'completed' : 'active'}">
                    <div class="stepper-circle">${step2Done ? '<i class="fa-solid fa-check"></i>' : '2'}</div>
                    <span class="stepper-label">Step 2: OTP</span>
                </div>

                <div class="stepper-line ${step3Done ? 'active' : ''}"></div>

                <div class="stepper-step ${step3Done ? 'completed' : (step2Done ? 'active' : '')}">
                    <div class="stepper-circle">${step3Done ? '<i class="fa-solid fa-check"></i>' : '3'}</div>
                    <span class="stepper-label">Step 3: Password</span>
                </div>
            </div>` : ''}
        </div>
    `;

    // Render active step view
    if (!step2Done) {
        // Step 2: OTP Verification
        const targetEmail = escapeHtml(share.recipient_email || 'your registered email');
        html += `
            <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid var(--border-color, #334155); border-radius: 10px; padding: 1.5rem; text-align: center; margin-top: 1rem;">
                <h4 style="margin-bottom: 0.5rem; font-size: 1.05rem;"><i class="fa-solid fa-mobile-screen-button text-primary"></i> Step 2: Enter OTP Verification Code</h4>
                <p class="subtext" style="font-size: 0.85rem; margin-bottom: 1.25rem;">
                    A 6-digit verification code will be dispatched to <strong>${targetEmail}</strong>.
                </p>

                <form onsubmit="handleRecipientOTPVerify(event)">
                    <div class="form-group" style="max-width: 260px; margin: 0 auto 1.25rem auto;">
                        <input type="text" id="recipient-otp-input" class="pin-code-input" maxlength="6" pattern="[0-9]{6}" placeholder="------" required autocomplete="off">
                    </div>

                    <div style="display: flex; gap: 0.75rem; justify-content: center; align-items: center;">
                        <button type="submit" class="btn btn-primary" id="btn-verify-otp"><i class="fa-solid fa-shield-check"></i> Verify OTP</button>
                        <button type="button" class="btn btn-outline" id="btn-request-otp" onclick="handleRecipientOTPRequest()"><i class="fa-solid fa-paper-plane"></i> Send OTP</button>
                    </div>
                    <div id="otp-resend-countdown" style="font-size: 0.8rem; color: #94a3b8; margin-top: 0.85rem;"></div>
                </form>
            </div>
        `;
    } else if (!step3Done) {
        // Step 3: Separate Share Password
        html += `
            <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid var(--border-color, #334155); border-radius: 10px; padding: 1.5rem; text-align: center; margin-top: 1rem;">
                <h4 style="margin-bottom: 0.5rem; font-size: 1.05rem;"><i class="fa-solid fa-key text-primary"></i> Enter Share Password</h4>
                <p class="subtext" style="font-size: 0.85rem; margin-bottom: 1.25rem;">
                    This file is password-protected. Enter the share password to unlock access.
                </p>

                <form onsubmit="handleRecipientPasswordVerify(event)">
                    <div class="form-group" style="max-width: 320px; margin: 0 auto 1.25rem auto;">
                        <div class="password-input-wrapper">
                            <input type="password" id="recipient-password-input" placeholder="Enter share password" required>
                            <i class="fa-solid fa-eye toggle-pwd-icon" onclick="togglePasswordVisibility('recipient-password-input', this)"></i>
                        </div>
                    </div>

                    <button type="submit" class="btn btn-primary" id="btn-submit-pwd-verify"><i class="fa-solid fa-lock-open"></i> Unlock & Access File</button>
                </form>
            </div>
        `;
    } else {
        // Access Granted!
        const canDownload = share.permission !== 'VIEW' && !share.is_expired;

        html += `
            <div style="background: rgba(34, 197, 94, 0.08); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 10px; padding: 1.5rem; text-align: center; margin-top: 1rem;">
                <div style="font-size: 2.2rem; color: #22c55e; margin-bottom: 0.5rem;"><i class="fa-solid fa-circle-check"></i></div>
                <h3 style="color: #22c55e; margin: 0 0 0.5rem 0; font-size: 1.3rem;">ACCESS GRANTED</h3>
                <p class="subtext" style="margin-bottom: 1.25rem; font-size: 0.9rem;">
                    All security verification checks completed successfully.
                </p>

                <div style="display: flex; gap: 0.75rem; justify-content: center; flex-wrap: wrap;">
                    <button type="button" class="btn btn-outline" onclick="openTokenShareFilePreview()"><i class="fa-solid fa-eye"></i> View File Online</button>
                    ${canDownload ? 
                        `<button type="button" class="btn btn-primary" onclick="downloadTokenSharedFile()"><i class="fa-solid fa-download"></i> Download File</button>` : 
                        `<button type="button" class="btn btn-outline" disabled style="opacity: 0.7;"><i class="fa-solid fa-lock"></i> Download Restricted (View Only)</button>`}
                </div>
            </div>
        `;
    }

    html += `</div>`;
    modalBody.innerHTML = html;
}

async function handleRecipientOTPRequest() {
    const state = currentShareTokenState;
    if (!state || !state.token) return;

    const btn = document.getElementById('btn-request-otp');
    if (btn) btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/shares/token/${state.token}/otp`, { method: 'POST' });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to request OTP');

        showToast(data.message || 'OTP verification code dispatched to email', 'success');
        startOTPResendTimer(45);
    } catch (err) {
        showToast(err.message, 'error');
        if (btn) btn.disabled = false;
    }
}

function startOTPResendTimer(seconds) {
    if (otpResendCountdownTimer) clearInterval(otpResendCountdownTimer);
    let remaining = seconds;
    const label = document.getElementById('otp-resend-countdown');
    const btn = document.getElementById('btn-request-otp');

    if (btn) btn.disabled = true;

    otpResendCountdownTimer = setInterval(() => {
        remaining--;
        if (label) label.textContent = `Resend available in ${remaining} seconds`;
        if (remaining <= 0) {
            clearInterval(otpResendCountdownTimer);
            if (label) label.textContent = '';
            if (btn) btn.disabled = false;
        }
    }, 1000);
}

async function handleRecipientOTPVerify(e) {
    e.preventDefault();
    const state = currentShareTokenState;
    const otpVal = document.getElementById('recipient-otp-input').value.trim();

    try {
        const res = await fetch(`${API_BASE}/shares/token/${state.token}/verify-otp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ otp: otpVal })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'OTP verification failed');

        showToast('OTP verified successfully!', 'success');
        state.otpVerified = true;
        renderRecipientVerificationStep();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function handleRecipientPasswordVerify(e) {
    e.preventDefault();
    const state = currentShareTokenState;
    const pwdVal = document.getElementById('recipient-password-input').value;
    const submitBtn = document.getElementById('btn-submit-pwd-verify');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Verifying...`;
    }

    try {
        const res = await fetch(`${API_BASE}/shares/token/${state.token}/verify-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: pwdVal })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Password verification failed');

        showToast('Share password verified!', 'success');
        state.passwordVerified = true;
        state.passwordInput = pwdVal;

        // Fetch full share details with password now verified
        try {
            const metaRes = await fetch(`${API_BASE}/shares/token/${state.token}?password=${encodeURIComponent(pwdVal)}`);
            if (metaRes.ok) {
                state.shareData = await metaRes.json();
                state.otpVerified = !state.shareData.requires_otp;
            }
        } catch (mErr) {}

        renderRecipientVerificationStep();
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        if (submitBtn && !state.passwordVerified) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<i class="fa-solid fa-lock-open"></i> Unlock & Access File`;
        }
    }
}

function renderAccessDeniedForToken(reason) {
    const modalBody = document.getElementById('token-share-body');
    modalBody.innerHTML = `
        <div style="text-align: center; padding: 2.5rem 1rem;">
            <i class="fa-solid fa-circle-exclamation text-danger fa-3x" style="margin-bottom: 1rem;"></i>
            <h3 class="text-danger" style="margin: 0 0 0.5rem 0;">Access Denied</h3>
            <p style="margin-top: 0.5rem; color: var(--text-muted); font-size: 0.9rem;">${escapeHtml(reason)}</p>
            <button class="btn btn-outline btn-sm" style="margin-top: 1.5rem;" onclick="closeModal('modal-token-share')">Close</button>
        </div>
    `;
}

window.addEventListener('hashchange', checkShareTokenHash);
window.addEventListener('DOMContentLoaded', checkShareTokenHash);


async function downloadSharedFile(shareId, filename) {
    showToast(`Validating permissions & downloading '${filename}'...`, 'info');
    try {
        const res = await fetch(`${API_BASE}/shares/${shareId}/download`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || 'Shared download failed');
        }

        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast('Shared file downloaded and decrypted!', 'success');
        loadSharedFiles();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// Audit Logs Tab
async function loadAuditLogs() {
    const tbody = document.getElementById('logs-table-body');
    tbody.innerHTML = `<tr><td colspan="5" class="text-center">Loading audit log stream...</td></tr>`;

    try {
        const res = await fetch(`${API_BASE}/audit/logs?limit=50`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (res.status === 401) {
            handleLogout();
            showToast('Session expired. Please log in again.', 'error');
            return;
        }

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || 'Failed to load audit logs');
        }
        const logs = await res.json();

        tbody.innerHTML = logs.map(log => `
            <tr>
                <td>${new Date(log.created_at).toLocaleString()}</td>
                <td><span class="badge ${log.success ? '' : 'badge-danger'}">${log.action}</span></td>
                <td>${log.resource || '-'}</td>
                <td>${log.details || '-'}</td>
                <td>${log.success ? '<span style="color:var(--accent-green)">Success</span>' : '<span style="color:var(--accent-red)">Denied / Fail</span>'}</td>
            </tr>
        `).join('');
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center text-danger">${err.message}</td></tr>`;
    }
}

// ==========================================
// Admin Master Portal Operations
// ==========================================
let adminCachedUsers = [];
let adminCachedFiles = [];

function switchAdminSubTab(tabName) {
    document.querySelectorAll('.admin-subtab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.admin-panel').forEach(panel => {
        panel.classList.remove('active');
        panel.style.display = 'none';
    });

    const activeBtn = document.getElementById(`btn-admintab-${tabName}`);
    if (activeBtn) activeBtn.classList.add('active');

    const activePanel = document.getElementById(`admin-panel-${tabName}`);
    if (activePanel) {
        activePanel.classList.add('active');
        activePanel.style.display = 'block';
    }
}

async function loadAdminStats() {
    try {
        const res = await fetch(`${API_BASE}/admin/stats`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!res.ok) throw new Error('Admin access denied');
        const stats = await res.json();

        // Metric Cards
        const statUsers = document.getElementById('stat-total-users');
        if (statUsers) statUsers.textContent = stats.total_users;

        const statBreakdown = document.getElementById('stat-user-breakdown');
        if (statBreakdown) statBreakdown.textContent = `${stats.total_students || 0} Students • ${stats.total_admins || 0} Admins`;

        const statOnline = document.getElementById('stat-online-users');
        if (statOnline) statOnline.textContent = stats.online_users_count || 0;

        const statFiles = document.getElementById('stat-total-files');
        if (statFiles) statFiles.textContent = stats.total_files;

        const statStorage = document.getElementById('stat-storage-used');
        if (statStorage) statStorage.textContent = formatBytes(stats.storage_used_bytes);

        const statActiveShares = document.getElementById('stat-active-shares');
        if (statActiveShares) statActiveShares.textContent = stats.active_shares;

        const statSecEvents = document.getElementById('stat-security-events');
        if (statSecEvents) statSecEvents.textContent = stats.security_events;

        // Subtab Counters
        const subUsersCount = document.getElementById('admin-subtab-users-count');
        if (subUsersCount) subUsersCount.textContent = stats.total_users;

        const subFilesCount = document.getElementById('admin-subtab-files-count');
        if (subFilesCount) subFilesCount.textContent = stats.total_files;

        const subClientsCount = document.getElementById('admin-subtab-clients-count');
        if (subClientsCount) subClientsCount.textContent = stats.online_users_count || 0;

        // Load Tab Contents
        loadAdminUsersTable();
        loadAdminFilesTable();
        loadAdminClientsTable();
        loadAdminAllActivityLogs();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function loadAdminUsersTable() {
    const tbody = document.getElementById('admin-users-table');
    if (!tbody) return;

    try {
        const res = await fetch(`${API_BASE}/admin/users`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!res.ok) throw new Error('Failed to load admin users');
        const users = await res.json();
        adminCachedUsers = users;
        renderAdminUsersTable(users);
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">${err.message}</td></tr>`;
    }
}

function renderAdminUsersTable(users) {
    const tbody = document.getElementById('admin-users-table');
    if (!tbody) return;

    if (!users || users.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center subtext" style="padding: 1.5rem;">No registered users found.</td></tr>`;
        return;
    }

    tbody.innerHTML = users.map(u => {
        const isOnline = u.is_online;
        const onlinePill = isOnline 
            ? `<span class="online-pill online" style="font-size: 0.72rem; padding: 2px 7px;"><span class="dot"></span> Active now</span>`
            : `<span class="online-pill offline" style="font-size: 0.72rem; padding: 2px 7px; opacity: 0.8;"><span class="dot"></span> ${escapeHtml(u.last_seen_text || 'Offline')}</span>`;

        const roleBadge = u.role === 'ADMIN'
            ? `<span class="badge" style="background: rgba(245, 158, 11, 0.18); color: #d97706; border: 1px solid rgba(245, 158, 11, 0.35); font-size: 0.72rem; padding: 2px 6px;"><i class="fa-solid fa-crown"></i> Admin</span>`
            : `<span class="badge" style="background: rgba(37, 99, 235, 0.15); color: #2563eb; border: 1px solid rgba(37, 99, 235, 0.3); font-size: 0.72rem; padding: 2px 6px;"><i class="fa-solid fa-graduation-cap"></i> Student</span>`;

        const statusBadge = u.is_active
            ? `<span class="badge badge-success" style="font-size: 0.72rem; padding: 2px 6px;"><i class="fa-solid fa-circle-check"></i> Active</span>`
            : `<span class="badge badge-danger" style="font-size: 0.72rem; padding: 2px 6px;"><i class="fa-solid fa-ban"></i> Suspended</span>`;

        const isSelf = (currentUser && currentUser.id === u.id);
        const jsEscapedName = escapeHtml(u.name || '').replace(/'/g, "\\'");
        const jsEscapedEmail = escapeHtml(u.email || '').replace(/'/g, "\\'");

        return `
            <tr>
                <td>
                    <div style="display: flex; align-items: center; gap: 0.55rem;">
                        <div style="width: 32px; height: 32px; border-radius: 50%; background: linear-gradient(135deg, #2563eb, #7c3aed); display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 0.78rem; flex-shrink: 0;">
                            ${escapeHtml((u.name || 'U').charAt(0).toUpperCase())}
                        </div>
                        <div style="min-width: 0;">
                            <strong style="color: var(--text-heading); font-size: 0.86rem; display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${escapeHtml(u.name)}</strong>
                            <div class="subtext" style="font-size: 0.73rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${escapeHtml(u.email)} <span style="opacity: 0.7;">• @${escapeHtml(u.username || 'user')}</span></div>
                        </div>
                    </div>
                </td>
                <td>
                    <div style="display: flex; align-items: center; gap: 0.35rem; flex-wrap: wrap;">
                        ${roleBadge}
                        ${statusBadge}
                    </div>
                    <div class="subtext" style="font-size: 0.7rem; margin-top: 2px;">Joined ${new Date(u.created_at).toLocaleDateString()}</div>
                </td>
                <td>
                    <strong style="font-size: 0.84rem; color: var(--text-heading);">${u.files_count || 0} files</strong>
                    <div class="subtext" style="font-size: 0.72rem;">${formatBytes(u.storage_used_bytes || 0)}</div>
                </td>
                <td>
                    ${onlinePill}
                </td>
                <td>
                    <div class="demo-btn-group" style="gap: 0.3rem; display: flex; align-items: center; justify-content: flex-end; flex-wrap: wrap;">
                        <button class="btn btn-sm btn-outline" onclick="openAdminEditUserModal(${u.id})" title="Edit Student Data & Password" style="padding: 0.2rem 0.5rem; font-size: 0.74rem; height: 30px;">
                            <i class="fa-solid fa-pen text-primary"></i> Edit
                        </button>
                        ${!isSelf ? `
                            <button class="btn btn-sm ${u.is_active ? 'btn-outline' : 'btn-primary'}" onclick="toggleUserActiveStatus(${u.id}, ${u.is_active})" title="${u.is_active ? 'Suspend Account' : 'Activate Account'}" style="padding: 0.2rem 0.5rem; font-size: 0.74rem; height: 30px;">
                                <i class="fa-solid ${u.is_active ? 'fa-ban text-danger' : 'fa-check text-success'}"></i> ${u.is_active ? 'Suspend' : 'Activate'}
                            </button>
                            <button class="btn btn-sm btn-outline" onclick="toggleUserRole(${u.id}, '${u.role}')" title="Change Role" style="padding: 0.2rem 0.5rem; font-size: 0.74rem; height: 30px;">
                                <i class="fa-solid fa-arrows-rotate"></i> ${u.role === 'ADMIN' ? 'Demote' : 'Make Admin'}
                            </button>
                            <button class="btn btn-sm btn-danger-outline" onclick="confirmAdminDeleteUser(${u.id}, '${jsEscapedName}', '${jsEscapedEmail}')" title="Delete Student & Stored Data" style="padding: 0.2rem 0.5rem; font-size: 0.74rem; height: 30px;">
                                <i class="fa-solid fa-trash"></i>
                            </button>
                        ` : `<span class="badge" style="font-size: 0.68rem; padding: 2px 6px;">Your Account</span>`}
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function filterAdminUsersTable(query) {
    const q = (query || '').toLowerCase().trim();
    if (!q) {
        renderAdminUsersTable(adminCachedUsers);
        return;
    }
    const filtered = adminCachedUsers.filter(u => 
        (u.name || '').toLowerCase().includes(q) ||
        (u.email || '').toLowerCase().includes(q) ||
        (u.username || '').toLowerCase().includes(q) ||
        (u.role || '').toLowerCase().includes(q)
    );
    renderAdminUsersTable(filtered);
}

async function toggleUserActiveStatus(userId, isCurrentlyActive) {
    const newStatus = !isCurrentlyActive;
    try {
        const res = await fetch(`${API_BASE}/admin/users/${userId}/status`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ is_active: newStatus })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to update user status');

        showToast(`User status updated to ${newStatus ? 'Active' : 'Suspended'}`, 'success');
        loadAdminStats();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function toggleUserRole(userId, currentRole) {
    const newRole = currentRole === 'ADMIN' ? 'USER' : 'ADMIN';
    try {
        const res = await fetch(`${API_BASE}/admin/users/${userId}/status`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ role: newRole })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to update user role');

        showToast(`User role updated to ${newRole}`, 'success');
        loadAdminStats();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ==========================================
// Admin Edit & Delete Operations
// ==========================================
async function openAdminEditUserModal(userId) {
    const user = adminCachedUsers.find(u => u.id === userId);
    if (!user) {
        showToast('Loading student details...', 'info');
        try {
            const res = await fetch(`${API_BASE}/admin/users/${userId}`, {
                headers: { 'Authorization': `Bearer ${authToken}` }
            });
            if (!res.ok) throw new Error('User not found');
            const data = await res.json();
            populateAdminEditUserModal(data);
        } catch (e) {
            showToast(e.message, 'error');
        }
        return;
    }
    populateAdminEditUserModal(user);
}

function populateAdminEditUserModal(user) {
    document.getElementById('admin-edit-user-id').value = user.id;
    document.getElementById('admin-edit-name').value = user.name || '';
    document.getElementById('admin-edit-email').value = user.email || '';
    document.getElementById('admin-edit-username').value = user.username || '';
    document.getElementById('admin-edit-role').value = user.role || 'USER';
    document.getElementById('admin-edit-status').value = user.is_active ? 'true' : 'false';
    document.getElementById('admin-edit-password').value = '';

    const msg = document.getElementById('admin-edit-user-msg');
    if (msg) msg.style.display = 'none';

    const deleteShortcutBtn = document.getElementById('btn-admin-edit-delete-shortcut');
    if (deleteShortcutBtn) {
        deleteShortcutBtn.style.display = (currentUser && currentUser.id === user.id) ? 'none' : 'inline-flex';
    }

    openModal('modal-admin-edit-user');
}

async function submitAdminEditUser(e) {
    if (e) e.preventDefault();
    const userId = parseInt(document.getElementById('admin-edit-user-id').value);
    const name = document.getElementById('admin-edit-name').value.trim();
    const email = document.getElementById('admin-edit-email').value.trim();
    const username = document.getElementById('admin-edit-username').value.trim();
    const role = document.getElementById('admin-edit-role').value;
    const is_active = document.getElementById('admin-edit-status').value === 'true';
    const new_password = document.getElementById('admin-edit-password').value;

    const msg = document.getElementById('admin-edit-user-msg');
    const submitBtn = document.getElementById('btn-submit-admin-edit-user');

    if (!name || !email) {
        if (msg) {
            msg.textContent = 'Name and Email are required.';
            msg.style.display = 'block';
            msg.style.background = 'var(--bg-error)';
            msg.style.color = 'var(--accent-error)';
        }
        return;
    }

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';
    }

    try {
        const body = { name, email, username, role, is_active };
        if (new_password && new_password.trim()) {
            body.new_password = new_password.trim();
        }

        const res = await fetch(`${API_BASE}/admin/users/${userId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify(body)
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to update student data');

        showToast(`Student data for '${name}' updated successfully!`, 'success');
        closeModal('modal-admin-edit-user');
        loadAdminStats();
    } catch (err) {
        if (msg) {
            msg.textContent = err.message;
            msg.style.display = 'block';
            msg.style.background = 'var(--bg-error)';
            msg.style.color = 'var(--accent-error)';
        }
        showToast(err.message, 'error');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Save Student Data';
        }
    }
}

function onAdminEditDeleteShortcut() {
    const userId = parseInt(document.getElementById('admin-edit-user-id').value);
    const name = document.getElementById('admin-edit-name').value;
    const email = document.getElementById('admin-edit-email').value;
    closeModal('modal-admin-edit-user');
    confirmAdminDeleteUser(userId, name, email);
}

function confirmAdminDeleteUser(userId, name, email) {
    if (currentUser && currentUser.id === userId) {
        showToast('You cannot delete your own logged-in admin account.', 'error');
        return;
    }

    document.getElementById('admin-delete-confirm-title').textContent = `Delete Student Account?`;
    document.getElementById('admin-delete-confirm-desc').innerHTML = `
        Are you sure you want to permanently delete student <strong>${escapeHtml(name)}</strong> (${escapeHtml(email)})?
        <br><br>
        <span style="color: var(--accent-error); font-weight: 600;">
            ⚠️ This will permanently erase this account and all their uploaded vault files.
        </span>
    `;

    const actionBtn = document.getElementById('btn-admin-confirm-delete-action');
    actionBtn.onclick = () => executeAdminDeleteUser(userId);

    openModal('modal-admin-confirm-delete');
}

async function executeAdminDeleteUser(userId) {
    const actionBtn = document.getElementById('btn-admin-confirm-delete-action');
    if (actionBtn) {
        actionBtn.disabled = true;
        actionBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Deleting...';
    }

    try {
        const res = await fetch(`${API_BASE}/admin/users/${userId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to delete user');

        closeModal('modal-admin-confirm-delete');
        showToast(data.message || 'Student and all associated files deleted successfully.', 'success');
        loadAdminStats();
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        if (actionBtn) {
            actionBtn.disabled = false;
            actionBtn.innerHTML = '<i class="fa-solid fa-trash"></i> Yes, Delete Permanently';
        }
    }
}

function confirmAdminDeleteFile(fileId, filename, ownerName) {
    document.getElementById('admin-delete-confirm-title').textContent = `Delete Stored Vault File?`;
    document.getElementById('admin-delete-confirm-desc').innerHTML = `
        Are you sure you want to permanently delete file <strong>${escapeHtml(filename)}</strong> owned by <strong>${escapeHtml(ownerName)}</strong>?
        <br><br>
        <span style="color: var(--accent-error); font-weight: 600;">
            ⚠️ The encrypted payload will be removed permanently from server storage.
        </span>
    `;

    const actionBtn = document.getElementById('btn-admin-confirm-delete-action');
    actionBtn.onclick = () => executeAdminDeleteFile(fileId);

    openModal('modal-admin-confirm-delete');
}

async function executeAdminDeleteFile(fileId) {
    const actionBtn = document.getElementById('btn-admin-confirm-delete-action');
    if (actionBtn) {
        actionBtn.disabled = true;
        actionBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Deleting...';
    }

    try {
        const res = await fetch(`${API_BASE}/admin/files/${fileId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to delete file');

        closeModal('modal-admin-confirm-delete');
        showToast(data.message || 'File permanently deleted.', 'success');
        loadAdminStats();
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        if (actionBtn) {
            actionBtn.disabled = false;
            actionBtn.innerHTML = '<i class="fa-solid fa-trash"></i> Yes, Delete Permanently';
        }
    }
}

async function downloadAdminSystemFile(fileId, filename) {
    try {
        showToast(`Preparing download for '${filename}'...`, 'info');
        const res = await fetch(`${API_BASE}/files/${fileId}/download`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'Download failed');
        }
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        showToast(`Downloaded '${filename}'`, 'success');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function loadAdminFilesTable() {
    const tbody = document.getElementById('admin-files-table');
    if (!tbody) return;

    try {
        const res = await fetch(`${API_BASE}/admin/files`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!res.ok) throw new Error('Failed to load system files');
        const files = await res.json();
        adminCachedFiles = files;
        renderAdminFilesTable(files);
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">${err.message}</td></tr>`;
    }
}

function renderAdminFilesTable(files) {
    const tbody = document.getElementById('admin-files-table');
    if (!tbody) return;

    if (!files || files.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" class="text-center subtext" style="padding: 1.5rem;">No stored files in platform vaults.</td></tr>`;
        return;
    }

    tbody.innerHTML = files.map(f => {
        const jsEscapedName = escapeHtml(f.filename).replace(/'/g, "\\'");
        const jsEscapedOwner = escapeHtml(f.owner_name || '').replace(/'/g, "\\'");
        return `
            <tr>
                <td>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <i class="fa-solid fa-file-shield text-primary" style="font-size: 1.1rem; flex-shrink: 0;"></i>
                        <div style="min-width: 0;">
                            <strong style="color: var(--text-heading); font-size: 0.86rem; display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${escapeHtml(f.filename)}</strong>
                            <div class="subtext" style="font-size: 0.72rem;">📁 ${escapeHtml(f.folder || '/')}</div>
                        </div>
                    </div>
                </td>
                <td>
                    <strong style="color: var(--text-heading); font-size: 0.84rem; display: block;">${escapeHtml(f.owner_name)}</strong>
                    <div class="subtext" style="font-size: 0.72rem;">${escapeHtml(f.owner_email)}</div>
                </td>
                <td>
                    <strong style="font-size: 0.84rem; color: var(--text-heading);">${formatBytes(f.file_size)}</strong>
                    <div class="subtext" style="font-size: 0.72rem;">${new Date(f.created_at).toLocaleDateString()}</div>
                </td>
                <td>
                    <div class="demo-btn-group" style="gap: 0.3rem; display: flex; align-items: center; justify-content: flex-end;">
                        <button class="btn btn-sm btn-outline" onclick="previewVaultFile(${f.id}, '${jsEscapedName}')" title="Inspect & View Online" style="padding: 0.2rem 0.5rem; font-size: 0.74rem; height: 30px;">
                            <i class="fa-solid fa-eye text-primary"></i> View
                        </button>
                        <button class="btn btn-sm btn-outline" onclick="downloadAdminSystemFile(${f.id}, '${jsEscapedName}')" title="Download Decrypted File" style="padding: 0.2rem 0.5rem; font-size: 0.74rem; height: 30px;">
                            <i class="fa-solid fa-download"></i>
                        </button>
                        <button class="btn btn-sm btn-danger-outline" onclick="confirmAdminDeleteFile(${f.id}, '${jsEscapedName}', '${jsEscapedOwner}')" title="Delete Stored File" style="padding: 0.2rem 0.5rem; font-size: 0.74rem; height: 30px;">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function filterAdminFilesTable(query) {
    const q = (query || '').toLowerCase().trim();
    if (!q) {
        renderAdminFilesTable(adminCachedFiles);
        return;
    }
    const filtered = adminCachedFiles.filter(f => 
        (f.filename || '').toLowerCase().includes(q) ||
        (f.owner_name || '').toLowerCase().includes(q) ||
        (f.owner_email || '').toLowerCase().includes(q) ||
        (f.folder || '').toLowerCase().includes(q)
    );
    renderAdminFilesTable(filtered);
}


async function loadAdminClientsTable() {
    const tbody = document.getElementById('admin-clients-table');
    if (!tbody) return;

    try {
        const res = await fetch(`${API_BASE}/admin/active-clients`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!res.ok) throw new Error('Failed to load active clients');
        const clients = await res.json();

        if (!clients || clients.length === 0) {
            tbody.innerHTML = `<tr><td colspan="3" class="text-center subtext" style="padding: 1.5rem;">No active client sessions right now.</td></tr>`;
            return;
        }

        tbody.innerHTML = clients.map(c => `
            <tr>
                <td>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <div style="width: 28px; height: 28px; border-radius: 50%; background: linear-gradient(135deg, #10b981, #059669); display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 0.75rem; flex-shrink: 0;">
                            ${escapeHtml((c.name || 'U').charAt(0).toUpperCase())}
                        </div>
                        <div>
                            <strong style="font-size: 0.86rem; color: var(--text-heading);">${escapeHtml(c.name)}</strong>
                            <div class="subtext" style="font-size: 0.72rem;">${escapeHtml(c.email)}</div>
                        </div>
                    </div>
                </td>
                <td>
                    <span class="badge ${c.role === 'ADMIN' ? 'badge-warning' : 'badge-blue'}" style="font-size: 0.72rem; padding: 2px 7px;">
                        ${escapeHtml(c.role)}
                    </span>
                </td>
                <td>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <span class="online-pill ${c.is_online ? 'online' : 'offline'}" style="font-size: 0.72rem; padding: 2px 7px;"><span class="dot"></span> ${escapeHtml(c.last_seen_text)}</span>
                        <span class="subtext" style="font-size: 0.72rem;">(${c.last_seen_at ? new Date(c.last_seen_at).toLocaleTimeString() : 'N/A'})</span>
                    </div>
                </td>
            </tr>
        `).join('');
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="3" class="text-center text-danger">${err.message}</td></tr>`;
    }
}

// ==========================================
// Admin Activity Stream & Audit Operations
// ==========================================
let adminCachedLogs = [];
let adminCurrentActivityCategory = 'all';
let adminCurrentActivitySearch = '';

async function loadAdminAllActivityLogs() {
    const tbody = document.getElementById('admin-activity-table');
    if (!tbody) return;

    tbody.innerHTML = `<tr><td colspan="5" class="text-center" style="padding: 1.5rem;">Loading live system activity stream...</td></tr>`;

    try {
        const logsRes = await fetch(`${API_BASE}/audit/logs?limit=150`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (!logsRes.ok) throw new Error('Failed to fetch activity logs');
        const logs = await logsRes.json();
        adminCachedLogs = logs;

        const countBadge = document.getElementById('admin-subtab-activity-count');
        if (countBadge) countBadge.textContent = logs.length;

        applyAdminActivityFilters();
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center text-danger">${err.message}</td></tr>`;
    }
}

// Backward compatibility alias
async function loadAdminSecurityLogs() {
    return loadAdminAllActivityLogs();
}

function filterAdminActivityCategory(category, btn) {
    adminCurrentActivityCategory = category;
    document.querySelectorAll('#admin-activity-filter-pills .activity-filter-btn').forEach(b => {
        b.classList.remove('active', 'btn-primary');
        b.classList.add('btn-outline');
    });
    if (btn) {
        btn.classList.remove('btn-outline');
        btn.classList.add('active', 'btn-primary');
    }
    applyAdminActivityFilters();
}

function filterAdminActivitySearch(query) {
    adminCurrentActivitySearch = (query || '').toLowerCase().trim();
    applyAdminActivityFilters();
}

function applyAdminActivityFilters() {
    let filtered = [...adminCachedLogs];

    // Category filter
    if (adminCurrentActivityCategory === 'logins') {
        filtered = filtered.filter(l => l.action && l.action.toLowerCase().includes('login'));
    } else if (adminCurrentActivityCategory === 'files') {
        filtered = filtered.filter(l => l.action && (l.action.includes('FILE_UPLOAD') || l.action.includes('FILE_DELETE') || l.action.includes('FOLDER') || l.action.includes('RENAME') || l.action.includes('MOVE')));
    } else if (adminCurrentActivityCategory === 'shares') {
        filtered = filtered.filter(l => l.action && (l.action.includes('SHARE') || l.action.includes('DOWNLOAD') || l.action.includes('VIEW')));
    } else if (adminCurrentActivityCategory === 'alerts') {
        filtered = filtered.filter(l => !l.success || l.action.includes('UNAUTHORIZED') || l.action.includes('FAILED') || l.action.includes('DENIED') || l.action.includes('OTP_FAILED'));
    }

    // Text search filter
    if (adminCurrentActivitySearch) {
        filtered = filtered.filter(l => 
            (l.user_email && l.user_email.toLowerCase().includes(adminCurrentActivitySearch)) ||
            (l.action && l.action.toLowerCase().includes(adminCurrentActivitySearch)) ||
            (l.resource && l.resource.toLowerCase().includes(adminCurrentActivitySearch)) ||
            (l.details && l.details.toLowerCase().includes(adminCurrentActivitySearch)) ||
            (l.ip_address && l.ip_address.toLowerCase().includes(adminCurrentActivitySearch))
        );
    }

    renderAdminActivityTable(filtered);
}

function renderAdminActivityTable(logs) {
    const tbody = document.getElementById('admin-activity-table');
    if (!tbody) return;

    if (!logs || logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center subtext" style="padding: 1.5rem;">No activity records match the selected filter.</td></tr>`;
        return;
    }

    tbody.innerHTML = logs.map(l => {
        const timeStr = new Date(l.created_at).toLocaleString();
        
        let actionBadgeClass = 'badge-blue';
        let actionIcon = 'fa-circle-info';

        if (l.action.includes('LOGIN_SUCCESS')) {
            actionBadgeClass = 'badge-success';
            actionIcon = 'fa-right-to-bracket';
        } else if (l.action.includes('LOGIN_FAILED') || l.action.includes('UNAUTHORIZED') || l.action.includes('DENIED') || !l.success) {
            actionBadgeClass = 'badge-danger';
            actionIcon = 'fa-triangle-exclamation';
        } else if (l.action.includes('UPLOAD')) {
            actionBadgeClass = 'badge-teal';
            actionIcon = 'fa-cloud-arrow-up';
        } else if (l.action.includes('DOWNLOAD') || l.action.includes('VIEW')) {
            actionBadgeClass = 'badge-blue';
            actionIcon = 'fa-download';
        } else if (l.action.includes('SHARE')) {
            actionBadgeClass = 'badge-purple';
            actionIcon = 'fa-share-nodes';
        } else if (l.action.includes('DELETE')) {
            actionBadgeClass = 'badge-gold';
            actionIcon = 'fa-trash';
        }

        const userDisplay = l.user_email 
            ? `<strong style="color: var(--text-heading); font-size: 0.82rem;">${escapeHtml(l.user_email)}</strong>`
            : `<span class="subtext" style="font-size: 0.78rem;">Anonymous / System</span>`;

        const resultBadge = l.success 
            ? `<span style="color: var(--accent-success); font-weight: 600; font-size: 0.78rem;"><i class="fa-solid fa-circle-check"></i> Success</span>`
            : `<span style="color: var(--accent-error); font-weight: 600; font-size: 0.78rem;"><i class="fa-solid fa-circle-xmark"></i> Denied</span>`;

        return `
            <tr>
                <td style="font-size: 0.78rem; color: var(--text-muted); white-space: nowrap;">
                    ${timeStr}
                    <div class="subtext" style="font-family: monospace; font-size: 0.7rem;">${escapeHtml(l.ip_address || '127.0.0.1')}</div>
                </td>
                <td>${userDisplay}</td>
                <td><span class="badge ${actionBadgeClass}" style="font-size: 0.72rem; padding: 2px 6px;"><i class="fa-solid ${actionIcon}"></i> ${escapeHtml(l.action)}</span></td>
                <td>
                    <div style="font-size: 0.82rem; max-width: 320px; word-break: break-word; color: var(--text-heading);">${escapeHtml(l.details || '-')}</div>
                    ${l.resource ? `<div class="subtext" style="font-family: monospace; font-size: 0.7rem;">${escapeHtml(l.resource)}</div>` : ''}
                </td>
                <td style="text-align: right;">${resultBadge}</td>
            </tr>
        `;
    }).join('');
}

// ==========================================
// Special Administrator Elevation & Switcher
// ==========================================
function openSpecialAdminModal() {
    const emailInput = document.getElementById('special-admin-email');
    const pwdInput = document.getElementById('special-admin-password');
    const errMsg = document.getElementById('special-admin-error-msg');
    if (emailInput && !emailInput.value) emailInput.value = 'admin@secure.local';
    if (pwdInput && !pwdInput.value) pwdInput.value = 'AdminSecret123!';
    if (errMsg) errMsg.style.display = 'none';
    openModal('modal-special-admin');
}

function fillSpecialAdminDemo() {
    const emailInput = document.getElementById('special-admin-email');
    const pwdInput = document.getElementById('special-admin-password');
    if (emailInput) emailInput.value = 'admin@secure.local';
    if (pwdInput) pwdInput.value = 'AdminSecret123!';
    showToast('Admin demo credentials populated', 'info');
}

async function submitSpecialAdminLogin(e) {
    if (e) e.preventDefault();
    const email = document.getElementById('special-admin-email').value.trim();
    const password = document.getElementById('special-admin-password').value;
    const errMsg = document.getElementById('special-admin-error-msg');
    const submitBtn = document.getElementById('btn-submit-special-admin');

    if (!email || !password) {
        if (errMsg) {
            errMsg.textContent = 'Please enter admin email/username and password.';
            errMsg.style.display = 'block';
        }
        return;
    }

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Authenticating...';
    }

    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.detail || 'Authentication failed');
        }

        if (data.user.role !== 'ADMIN') {
            throw new Error(`Account '${data.user.email}' does not have Administrator privileges. Please use an Admin account.`);
        }

        // Save session tokens and update current state
        authToken = data.access_token;
        currentUser = data.user;
        localStorage.setItem('access_token', authToken);
        localStorage.setItem('user_data', JSON.stringify(currentUser));

        closeModal('modal-special-admin');
        showToast('🎉 Admin Elevation Successful! Admin Security Center & All Activity Unlocked.', 'success');

        showDashboardView();
        switchDashboardTab('admin');
        loadAdminStats();
    } catch (err) {
        if (errMsg) {
            errMsg.textContent = err.message;
            errMsg.style.display = 'block';
        }
        showToast(err.message, 'error');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fa-solid fa-unlock-keyhole"></i> Elevate & Show All Activity';
        }
    }
}

async function switchToStudentProfile() {
    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: 'usera@secure.local', password: 'UserSecret123!' })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to switch to student account');

        authToken = data.access_token;
        currentUser = data.user;
        localStorage.setItem('access_token', authToken);
        localStorage.setItem('user_data', JSON.stringify(currentUser));

        showToast('Switched to Demo Student (Alice Johnson)', 'info');
        showDashboardView();
        switchDashboardTab('files');
    } catch (err) {
        showToast('Could not switch to student account: ' + err.message, 'error');
    }
}


// Recycle Bin Operations
async function loadTrashFiles() {
    const tbody = document.getElementById('trash-list-body');
    if (!tbody) return;

    tbody.innerHTML = `<tr><td colspan="5" class="text-center">Loading Recycle Bin files...</td></tr>`;

    try {
        const res = await fetch(`${API_BASE}/files/trash`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (res.status === 401) {
            handleLogout();
            showToast('Session expired. Please log in again.', 'error');
            return;
        }

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || 'Failed to load Recycle Bin files');
        }

        const files = await res.json();

        if (!files || files.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="empty-state text-center">No deleted files in Recycle Bin.</td></tr>`;
            return;
        }

        tbody.innerHTML = files.map(file => `
            <tr>
                <td>
                    <div style="display:flex; align-items:center; gap:0.6rem;">
                        <i class="fa-solid fa-file" style="color: var(--accent-blue, #3b82f6);"></i>
                        <strong>${escapeHtml(file.original_name)}</strong>
                    </div>
                </td>
                <td>${formatBytes(file.file_size)}</td>
                <td><span class="file-type-badge">${escapeHtml(file.mime_type || 'Unknown')}</span></td>
                <td>${new Date(file.updated_at || file.created_at).toLocaleString()}</td>
                <td>
                    <div style="display:flex; gap:0.5rem;">
                        <button class="btn btn-sm btn-outline" onclick="restoreFile(${file.id})" title="Restore to My Files">
                            <i class="fa-solid fa-rotate-left"></i> Restore
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="permanentlyDeleteFile(${file.id})" title="Permanently Delete">
                            <i class="fa-solid fa-trash-xmark"></i> Delete Permanently
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center text-danger">${escapeHtml(err.message)}</td></tr>`;
        showToast(err.message, 'error');
    }
}

async function restoreFile(fileId) {
    try {
        const res = await fetch(`${API_BASE}/files/${fileId}/restore`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!res.ok) {
            const data = await res.json();
            throw new Error(data.detail || 'Failed to restore file');
        }

        showToast('File restored successfully to My Files!', 'success');
        loadTrashFiles();
        loadUserFiles();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function permanentlyDeleteFile(fileId) {
    if (!confirm('Are you sure you want to PERMANENTLY delete this file? This action cannot be undone.')) return;

    try {
        const res = await fetch(`${API_BASE}/files/${fileId}/permanent`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!res.ok) {
            const data = await res.json();
            throw new Error(data.detail || 'Failed to purge file');
        }

        showToast('File permanently purged from system.', 'success');
        loadTrashFiles();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function emptyTrash() {
    if (!confirm('Are you sure you want to empty the entire Recycle Bin? All deleted files will be PERMANENTLY lost.')) return;

    try {
        const res = await fetch(`${API_BASE}/files/trash/empty`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to empty Recycle Bin');

        showToast(data.message || 'Recycle Bin emptied successfully!', 'success');
        loadTrashFiles();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// Folder Operations
function openCreateFolderModal() {
    const parentLabel = document.getElementById('create-folder-parent-label');
    if (parentLabel) parentLabel.textContent = currentFolder;
    const input = document.getElementById('create-folder-name');
    if (input) input.value = '';
    document.getElementById('modal-create-folder').classList.add('active');
}

async function submitCreateFolderForm() {
    const input = document.getElementById('create-folder-name');
    const folderName = input ? input.value.trim() : '';
    if (!folderName) {
        showToast('Please enter a folder name', 'error');
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/files/folders`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                folder_name: folderName,
                parent_folder: currentFolder
            })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to create folder');

        showToast(`Folder '${folderName}' created successfully!`, 'success');
        closeModal('modal-create-folder');
        loadUserFiles();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function openMoveModal(fileId, fileName, currentFileFolder) {
    document.getElementById('move-file-id').value = fileId;
    document.getElementById('move-file-name').textContent = fileName;

    const select = document.getElementById('move-target-folder');
    select.innerHTML = `<option value="/">Root Directory (/)</option>`;

    try {
        const res = await fetch(`${API_BASE}/files/folders?parent_folder=/`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (res.ok) {
            const rootFolders = await res.json();
            rootFolders.forEach(f => {
                const opt = document.createElement('option');
                opt.value = f.path;
                opt.textContent = f.path;
                if (f.path === currentFileFolder) opt.selected = true;
                select.appendChild(opt);
            });
        }
    } catch (err) {
        console.error("Failed to load destination folders", err);
    }

    document.getElementById('modal-move-file').classList.add('active');
}

async function submitMoveFileForm() {
    const fileId = document.getElementById('move-file-id').value;
    const targetFolder = document.getElementById('move-target-folder').value;

    try {
        const res = await fetch(`${API_BASE}/files/${fileId}/move`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ target_folder: targetFolder })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to move file');

        showToast(`File moved to '${targetFolder}' successfully!`, 'success');
        closeModal('modal-move-file');
        loadUserFiles();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// User Profile & Account Settings Functions
function getInitials(name) {
    if (!name || !name.trim()) return 'U';
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
        return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return parts[0].substring(0, 2).toUpperCase();
}

async function fetchUserAvatarBlob(imgElementId) {
    const img = document.getElementById(imgElementId);
    if (!img) return;
    try {
        const res = await fetch(`${API_BASE}/users/me/avatar`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (res.ok) {
            const blob = await res.blob();
            const objectUrl = URL.createObjectURL(blob);
            img.src = objectUrl;
            img.style.display = 'block';
        } else {
            img.style.display = 'none';
        }
    } catch (e) {
        img.style.display = 'none';
    }
}

function openAvatarFilePicker(e) {
    if (e) e.stopPropagation();
    closeAccountDropdown();
    const modal = document.getElementById('modal-account');
    if (modal && !modal.classList.contains('active')) {
        openAccountModal('profile');
    }
    setTimeout(() => {
        const fileInput = document.getElementById('avatar-file-input');
        if (fileInput) {
            fileInput.value = '';
            fileInput.click();
        }
    }, 150);
}

function updateUserHeaderUI() {
    const container = document.getElementById('account-control-container');
    if (!currentUser) {
        if (container) container.style.display = 'none';
        return;
    }

    if (container) container.style.display = 'inline-block';

    const nameEl = document.getElementById('user-display-name');
    const roleEl = document.getElementById('user-display-role');
    if (nameEl) nameEl.textContent = currentUser.name;
    if (roleEl) roleEl.textContent = currentUser.role;

    const dropdownName = document.getElementById('dropdown-user-name');
    const dropdownEmail = document.getElementById('dropdown-user-email');
    const dropdownRole = document.getElementById('dropdown-user-role');
    if (dropdownName) dropdownName.textContent = currentUser.name;
    if (dropdownEmail) dropdownEmail.textContent = currentUser.email;
    if (dropdownRole) dropdownRole.textContent = currentUser.role;

    // Update Online Status Dot & Pills
    const isOnline = currentUser.is_online !== undefined ? currentUser.is_online : true;
    const statusText = currentUser.last_seen_text || (isOnline ? 'Active now' : 'Offline');
    
    ['user-header-status-dot', 'dropdown-header-status-dot'].forEach(id => {
        const dot = document.getElementById(id);
        if (dot) {
            dot.className = `status-dot ${isOnline ? 'online' : 'offline'}`;
            dot.title = statusText;
        }
    });

    ['user-header-status-badge', 'dropdown-user-status'].forEach(id => {
        const pill = document.getElementById(id);
        if (pill) {
            pill.className = `online-pill ${isOnline ? 'online' : 'offline'}`;
            pill.innerHTML = `<span class="dot"></span> ${escapeHtml(statusText)}`;
        }
    });

    const initials = getInitials(currentUser.name);

    ['user-header-initials', 'dropdown-header-initials', 'modal-avatar-initials'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = initials;
    });

    if (currentUser.has_avatar) {
        ['user-header-photo', 'dropdown-header-photo', 'modal-avatar-photo'].forEach(id => {
            fetchUserAvatarBlob(id);
        });
        ['user-header-initials', 'dropdown-header-initials', 'modal-avatar-initials'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
    } else {
        ['user-header-photo', 'dropdown-header-photo', 'modal-avatar-photo'].forEach(id => {
            const img = document.getElementById(id);
            if (img) img.style.display = 'none';
        });
        ['user-header-initials', 'dropdown-header-initials', 'modal-avatar-initials'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'inline';
        });
    }

    if (currentUser.theme_preference) {
        applyTheme(currentUser.theme_preference);
    }
}

function applyTheme(theme) {
    if (theme === 'light') {
        document.body.classList.add('light-theme');
        document.body.classList.remove('dark-theme');
    } else if (theme === 'system') {
        const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        document.body.classList.toggle('dark-theme', prefersDark);
        document.body.classList.toggle('light-theme', !prefersDark);
    } else {
        document.body.classList.add('dark-theme');
        document.body.classList.remove('light-theme');
    }
}

function applyThemePreview(theme) {
    applyTheme(theme);
}

function toggleAccountDropdown(e) {
    if (e) e.stopPropagation();
    const menu = document.getElementById('account-dropdown-menu');
    const trigger = document.getElementById('account-dropdown-trigger');
    if (!menu) return;

    const isActive = menu.classList.contains('active');
    if (isActive) {
        closeAccountDropdown();
    } else {
        menu.classList.add('active');
        if (trigger) trigger.classList.add('active');
    }
}

function closeAccountDropdown() {
    const menu = document.getElementById('account-dropdown-menu');
    const trigger = document.getElementById('account-dropdown-trigger');
    if (menu) menu.classList.remove('active');
    if (trigger) trigger.classList.remove('active');
}

document.addEventListener('click', (e) => {
    const container = document.getElementById('account-control-container');
    if (container && !container.contains(e.target)) {
        closeAccountDropdown();
    }
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeAccountDropdown();
        document.querySelectorAll('.modal.active').forEach(m => m.classList.remove('active'));
    }
});

async function openAccountModal(tabName = 'profile') {
    closeAccountDropdown();
    const modal = document.getElementById('modal-account');
    if (!modal) return;

    modal.classList.add('active');
    switchAccountTab(tabName);

    try {
        const res = await fetch(`${API_BASE}/users/me`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (res.ok) {
            currentUser = await res.json();
            localStorage.setItem('user_data', JSON.stringify(currentUser));
            updateUserHeaderUI();

            const profileName = document.getElementById('profile-name-input');
            if (profileName) profileName.value = currentUser.name;
            const profileUser = document.getElementById('profile-username-display');
            if (profileUser) profileUser.value = currentUser.username;
            const profileEmail = document.getElementById('profile-email-display');
            if (profileEmail) profileEmail.value = currentUser.email;

            const emailCurr = document.getElementById('email-current-display');
            if (emailCurr) emailCurr.value = currentUser.email;

            const infoUser = document.getElementById('info-username');
            if (infoUser) infoUser.textContent = currentUser.username;
            const infoRole = document.getElementById('info-role');
            if (infoRole) infoRole.textContent = currentUser.role;
            const infoCreated = document.getElementById('info-created');
            if (infoCreated) infoCreated.textContent = new Date(currentUser.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
            const infoLogin = document.getElementById('info-last-login');
            if (infoLogin) infoLogin.textContent = currentUser.last_login_at ? new Date(currentUser.last_login_at).toLocaleString() : 'Just now';
            const infoPwd = document.getElementById('info-last-pwd-change');
            if (infoPwd) infoPwd.textContent = currentUser.last_password_change_at ? new Date(currentUser.last_password_change_at).toLocaleString() : 'Never';

            const prefTheme = document.getElementById('pref-theme-select');
            if (prefTheme) prefTheme.value = currentUser.theme_preference || 'dark';
            const prefSort = document.getElementById('pref-sort-select');
            if (prefSort) prefSort.value = currentUser.default_file_sort || 'date_desc';
            const prefItems = document.getElementById('pref-items-select');
            if (prefItems) prefItems.value = currentUser.items_per_page || 10;
        }
    } catch (e) {
        console.error("Failed to load user profile", e);
    }
}

function switchAccountTab(tabName) {
    document.querySelectorAll('.account-tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.account-panel').forEach(panel => panel.classList.remove('active'));

    const btn = document.getElementById(`acc-tab-btn-${tabName}`);
    const panel = document.getElementById(`acc-panel-${tabName}`);
    if (btn) btn.classList.add('active');
    if (panel) panel.classList.add('active');

    if (tabName === 'security') {
        loadUserSessions();
    }
}

function handleAvatarFileSelect(e) {
    if (!e.target.files.length) return;
    const file = e.target.files[0];

    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
    if (!allowedTypes.includes(file.type.toLowerCase())) {
        showToast('Invalid image format. Allowed formats: JPG, JPEG, PNG, WEBP', 'error');
        return;
    }

    if (file.size > 5 * 1024 * 1024) {
        showToast('Image size exceeds maximum limit of 5MB', 'error');
        return;
    }

    submitAvatarUpload(file);
}

async function submitAvatarUpload(file) {
    showToast('Uploading profile photo...', 'info');
    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch(`${API_BASE}/users/me/avatar`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` },
            body: formData
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to upload photo');

        currentUser = data;
        localStorage.setItem('user_data', JSON.stringify(currentUser));
        updateUserHeaderUI();
        showToast('Profile photo updated successfully!', 'success');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function submitRemovePhoto() {
    if (!confirm('Are you sure you want to remove your profile photo?')) return;

    try {
        const res = await fetch(`${API_BASE}/users/me/avatar`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to remove photo');

        currentUser = data;
        localStorage.setItem('user_data', JSON.stringify(currentUser));
        updateUserHeaderUI();
        showToast('Profile photo removed.', 'info');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function submitProfileForm(e) {
    e.preventDefault();
    const name = document.getElementById('profile-name-input').value.trim();

    try {
        const res = await fetch(`${API_BASE}/users/me/profile`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to update profile');

        currentUser = data;
        localStorage.setItem('user_data', JSON.stringify(currentUser));
        updateUserHeaderUI();
        showToast('Profile updated successfully!', 'success');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function submitEmailChangeForm(e) {
    e.preventDefault();
    const new_email = document.getElementById('email-new-input').value.trim();
    const confirm_new_email = document.getElementById('email-confirm-input').value.trim();
    const current_password = document.getElementById('email-password-input').value;

    if (new_email !== confirm_new_email) {
        showToast('New email and confirmation email do not match', 'error');
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/users/me/email`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ current_password, new_email, confirm_new_email })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to change email');

        currentUser = data;
        localStorage.setItem('user_data', JSON.stringify(currentUser));
        updateUserHeaderUI();
        document.getElementById('email-password-input').value = '';
        showToast('Email address changed successfully!', 'success');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

let livePasswordRequirements = {
    min_length: 8,
    require_uppercase: true,
    require_lowercase: true,
    require_digit: true,
    require_special: true
};

async function fetchPasswordRequirements() {
    try {
        const res = await fetch(`${API_BASE}/auth/password-requirements`);
        if (res.ok) {
            const data = await res.json();
            livePasswordRequirements = data;
        }
    } catch (err) {
        console.warn('Using default password rules:', err);
    }
}

function checkRegPasswordStrength(val) {
    const fill = document.getElementById('reg-strength-bar-fill');
    const label = document.getElementById('reg-strength-label');

    const minLen = livePasswordRequirements.min_length || 8;
    const hasLength = val.length >= minLen;
    const hasUpper = /[A-Z]/.test(val);
    const hasLower = /[a-z]/.test(val);
    const hasNumber = /[0-9]/.test(val);
    const hasSpecial = /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(val);

    updateCheckItem('reg-chk-length', hasLength);
    updateCheckItem('reg-chk-upper', hasUpper);
    updateCheckItem('reg-chk-lower', hasLower);
    updateCheckItem('reg-chk-number', hasNumber);
    updateCheckItem('reg-chk-special', hasSpecial);

    const score = [hasLength, hasUpper, hasLower, hasNumber, hasSpecial].filter(Boolean).length;

    if (fill && label) {
        if (!val) {
            fill.className = 'strength-fill';
            fill.style.width = '0%';
            label.textContent = 'Password Strength';
            label.style.color = 'var(--text-secondary)';
        } else if (score <= 2) {
            fill.className = 'strength-fill weak';
            label.textContent = 'Weak Password';
            label.style.color = 'var(--accent-red)';
        } else if (score <= 4) {
            fill.className = 'strength-fill medium';
            label.textContent = 'Medium Password';
            label.style.color = '#f59e0b';
        } else {
            fill.className = 'strength-fill strong';
            label.textContent = 'Strong Password';
            label.style.color = 'var(--accent-green)';
        }
    }

    checkRegPasswordMatch();
}

function checkRegPasswordMatch() {
    const pwd = document.getElementById('reg-password').value;
    const confirmPwd = document.getElementById('reg-confirm-password').value;
    const msgEl = document.getElementById('reg-pwd-match-msg');

    if (!msgEl) return;

    if (!confirmPwd) {
        msgEl.style.display = 'none';
        return;
    }

    msgEl.style.display = 'block';
    if (pwd === confirmPwd) {
        msgEl.innerHTML = `<i class="fa-solid fa-circle-check"></i> Passwords match`;
        msgEl.style.color = 'var(--accent-green)';
    } else {
        msgEl.innerHTML = `<i class="fa-solid fa-circle-xmark"></i> Passwords do not match`;
        msgEl.style.color = 'var(--accent-red)';
    }
}

function checkPasswordStrength(val) {
    const fill = document.getElementById('strength-bar-fill');
    const label = document.getElementById('strength-label');

    const hasLength = val.length >= (livePasswordRequirements.min_length || 8);
    const hasUpper = /[A-Z]/.test(val);
    const hasLower = /[a-z]/.test(val);
    const hasNumber = /[0-9]/.test(val);
    const hasSpecial = /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(val);

    updateCheckItem('chk-length', hasLength);
    updateCheckItem('chk-upper', hasUpper);
    updateCheckItem('chk-lower', hasLower);
    updateCheckItem('chk-number', hasNumber);
    updateCheckItem('chk-special', hasSpecial);

    const score = [hasLength, hasUpper, hasLower, hasNumber, hasSpecial].filter(Boolean).length;

    if (!fill || !label) return;

    if (score <= 2) {
        fill.className = 'strength-fill weak';
        label.textContent = 'Weak Password';
    } else if (score <= 4) {
        fill.className = 'strength-fill medium';
        label.textContent = 'Medium Password';
    } else {
        fill.className = 'strength-fill strong';
        label.textContent = 'Strong Password';
    }
}

function updateCheckItem(id, passed) {
    const el = document.getElementById(id);
    if (!el) return;
    const baseText = el.innerText.replace(/^[✔✖]\s*/, '').replace(/^✓\s*/, '');
    if (passed) {
        el.innerHTML = `<i class="fa-solid fa-circle-check" style="color:var(--accent-green)"></i> ${baseText}`;
        el.style.color = 'var(--accent-green)';
    } else {
        el.innerHTML = `<i class="fa-solid fa-circle-xmark" style="color:var(--accent-red)"></i> ${baseText}`;
        el.style.color = 'var(--text-secondary)';
    }
}

function togglePasswordVisibility(inputId, iconEl) {
    const input = document.getElementById(inputId);
    if (!input) return;
    if (input.type === 'password') {
        input.type = 'text';
        iconEl.classList.remove('fa-eye');
        iconEl.classList.add('fa-eye-slash');
    } else {
        input.type = 'password';
        iconEl.classList.remove('fa-eye-slash');
        iconEl.classList.add('fa-eye');
    }
}

async function submitPasswordChangeForm(e) {
    e.preventDefault();
    const current_password = document.getElementById('pwd-current-input').value;
    const new_password = document.getElementById('pwd-new-input').value;
    const confirm_new_password = document.getElementById('pwd-confirm-input').value;

    if (new_password !== confirm_new_password) {
        showToast('New password and confirmation password do not match', 'error');
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/users/me/password`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ current_password, new_password, confirm_new_password })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to change password');

        currentUser = data;
        localStorage.setItem('user_data', JSON.stringify(currentUser));
        document.getElementById('pwd-current-input').value = '';
        document.getElementById('pwd-new-input').value = '';
        document.getElementById('pwd-confirm-input').value = '';

        showToast('Password changed successfully.', 'success');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function submitPreferencesForm(e) {
    e.preventDefault();
    const theme_preference = document.getElementById('pref-theme-select').value;
    const default_file_sort = document.getElementById('pref-sort-select').value;
    const items_per_page = parseInt(document.getElementById('pref-items-select').value, 10);

    try {
        const res = await fetch(`${API_BASE}/users/me/preferences`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ theme_preference, default_file_sort, items_per_page })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to update preferences');

        currentUser = data;
        localStorage.setItem('user_data', JSON.stringify(currentUser));
        updateUserHeaderUI();
        showToast('Preferences saved successfully!', 'success');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function loadUserSessions() {
    const tbody = document.getElementById('sessions-table-body');
    if (!tbody) return;

    try {
        const res = await fetch(`${API_BASE}/users/me/sessions`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!res.ok) throw new Error('Failed to load active sessions');
        const sessions = await res.json();

        if (!sessions || sessions.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" class="text-center subtext">No active session records found.</td></tr>`;
            return;
        }

        tbody.innerHTML = sessions.map(s => `
            <tr>
                <td><strong><i class="fa-solid fa-desktop text-primary"></i> ${escapeHtml(s.user_agent)}</strong></td>
                <td>${escapeHtml(s.ip_address || '127.0.0.1')}</td>
                <td>${new Date(s.last_activity_at || s.created_at).toLocaleString()}</td>
                <td>${s.is_current ? '<span class="badge badge-success">Current Session</span>' : '<span class="badge">Active</span>'}</td>
            </tr>
        `).join('');
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="4" class="text-center text-danger">${escapeHtml(err.message)}</td></tr>`;
    }
}

async function submitRevokeOtherSessions() {
    if (!confirm('Are you sure you want to log out all other active sessions across devices?')) return;

    try {
        const res = await fetch(`${API_BASE}/users/me/sessions/revoke-others`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to revoke other sessions');

        showToast(data.message || 'Other active sessions revoked.', 'success');
        loadUserSessions();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// Helpers
function closeModal(id) {
    document.getElementById(id).classList.remove('active');
}

function formatBytes(bytes, decimals = 2) {
    if (!+bytes) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

// Forgot Password OTP Flow Functions
function openForgotPasswordModal() {
    document.getElementById('forgot-email-input').value = '';
    document.getElementById('forgot-otp-input').value = '';
    document.getElementById('forgot-new-password').value = '';
    document.getElementById('forgot-confirm-password').value = '';
    document.getElementById('forgot-step-1').style.display = 'block';
    document.getElementById('forgot-step-2').style.display = 'none';
    document.getElementById('modal-forgot-password').classList.add('active');
}

function backToStep1() {
    document.getElementById('forgot-step-1').style.display = 'block';
    document.getElementById('forgot-step-2').style.display = 'none';
}

async function submitForgotPasswordRequest(e) {
    e.preventDefault();
    const emailOrUser = document.getElementById('forgot-email-input').value.trim();
    if (!emailOrUser) return;

    const btn = document.getElementById('btn-send-otp');
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Sending OTP...`;

    try {
        const res = await fetch(`${API_BASE}/auth/forgot-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email_or_username: emailOrUser })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to send OTP code');

        document.getElementById('forgot-masked-email-text').textContent = data.message || `OTP sent to official email ${data.email_masked}`;
        document.getElementById('forgot-step-1').style.display = 'none';
        document.getElementById('forgot-step-2').style.display = 'block';
        showToast(`OTP Code sent to official email ${data.email_masked || ''}! Check your inbox.`, 'success');
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-paper-plane"></i> Send OTP Code`;
    }
}

async function submitResetPasswordForm(e) {
    e.preventDefault();
    const email_or_username = document.getElementById('forgot-email-input').value.trim();
    const otp_code = document.getElementById('forgot-otp-input').value.trim();
    const new_password = document.getElementById('forgot-new-password').value;
    const confirm_new_password = document.getElementById('forgot-confirm-password').value;

    if (new_password !== confirm_new_password) {
        showToast('New passwords do not match!', 'error');
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/auth/reset-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email_or_username,
                otp_code,
                new_password,
                confirm_new_password
            })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to reset password');

        closeModal('modal-forgot-password');
        showToast('Password reset successfully! Logging you in...', 'success');

        // Automatically log in user with new credentials
        document.getElementById('login-email').value = email_or_username;
        document.getElementById('login-password').value = new_password;
        
        // Trigger login submit
        const loginForm = document.getElementById('form-login');
        if (loginForm) {
            loginForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
        }
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// ==========================================
// Online Document / File Previewer System
// ==========================================

function getFileIconClass(filename) {
    const ext = (filename || '').split('.').pop().toLowerCase();
    if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext)) return 'fa-file-image text-primary';
    if (ext === 'pdf') return 'fa-file-pdf text-danger';
    if (['doc', 'docx'].includes(ext)) return 'fa-file-word text-primary';
    if (['xls', 'xlsx', 'csv'].includes(ext)) return 'fa-file-excel text-success';
    if (['ppt', 'pptx'].includes(ext)) return 'fa-file-powerpoint text-warning';
    if (['zip', 'rar', '7z', 'tar', 'gz'].includes(ext)) return 'fa-file-zipper text-warning';
    if (['mp4', 'webm', 'mov'].includes(ext)) return 'fa-file-video text-primary';
    if (['mp3', 'wav', 'ogg'].includes(ext)) return 'fa-file-audio text-primary';
    if (['txt', 'log', 'md'].includes(ext)) return 'fa-file-lines text-primary';
    if (['py', 'js', 'html', 'css', 'json', 'sql'].includes(ext)) return 'fa-file-code text-primary';
    return 'fa-file-shield text-primary';
}

function renderPreviewLoading(filename) {
    document.getElementById('preview-modal-title').textContent = filename || 'Loading File...';
    document.getElementById('preview-modal-size').textContent = '--';
    document.getElementById('preview-modal-type-badge').innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Decrypting...`;
    document.getElementById('preview-modal-icon').className = `fa-solid ${getFileIconClass(filename)}`;
    
    const body = document.getElementById('preview-modal-body');
    body.innerHTML = `
        <div style="text-align: center; padding: 4rem 1rem;">
            <i class="fa-solid fa-shield-halved fa-spin fa-3x text-primary" style="margin-bottom: 1rem;"></i>
            <h4 style="color: var(--text-heading); margin-bottom: 0.5rem;">Decrypting File in Memory...</h4>
            <p class="subtext" style="font-size: 0.85rem;">Processing AES-256 decrypted content for in-browser visual viewing.</p>
        </div>
    `;
    
    document.getElementById('preview-footer-info').innerHTML = `<i class="fa-solid fa-shield-halved text-primary"></i> Zero-Trust In-Memory Decryption`;
    document.getElementById('preview-modal-download-btn').style.display = 'none';
    document.getElementById('modal-file-preview').classList.add('active');
}

function renderPreviewModal(data, filename, downloadCallback) {
    document.getElementById('preview-modal-title').textContent = data.filename || filename;
    document.getElementById('preview-modal-size').textContent = formatBytes(data.size_bytes || 0);
    document.getElementById('preview-modal-icon').className = `fa-solid ${getFileIconClass(data.filename || filename)}`;
    
    const typeBadge = document.getElementById('preview-modal-type-badge');
    const body = document.getElementById('preview-modal-body');
    const footerInfo = document.getElementById('preview-footer-info');
    const dlBtn = document.getElementById('preview-modal-download-btn');

    typeBadge.className = 'badge badge-success';
    typeBadge.innerHTML = `<i class="fa-solid fa-eye"></i> Online Document View`;

    if (data.preview_type === 'docx') {
        typeBadge.innerHTML = `<i class="fa-solid fa-file-word"></i> Word Document View`;
        body.innerHTML = `
            <div class="docx-sheet-wrapper">
                <div class="docx-document-sheet">
                    ${data.html_content || '<p>No content in document.</p>'}
                </div>
            </div>
        `;
    } else if (data.preview_type === 'pdf') {
        typeBadge.innerHTML = `<i class="fa-solid fa-file-pdf"></i> PDF Document View`;
        body.innerHTML = `
            <iframe src="${data.data_uri}" class="preview-pdf-frame" title="PDF Document Preview"></iframe>
        `;
    } else if (data.preview_type === 'image') {
        typeBadge.innerHTML = `<i class="fa-solid fa-image"></i> Image Preview`;
        body.innerHTML = `
            <div class="preview-image-container">
                <img src="${data.data_uri}" alt="${escapeHtml(data.filename)}">
            </div>
        `;
    } else if (data.preview_type === 'text') {
        typeBadge.innerHTML = `<i class="fa-solid fa-file-lines"></i> ${data.line_count || 1} Lines Text`;
        body.innerHTML = `
            <pre class="preview-code-wrapper"><code>${escapeHtml(data.text_content || '')}</code></pre>
        `;
    } else if (data.preview_type === 'media') {
        if (data.media_kind === 'video') {
            typeBadge.innerHTML = `<i class="fa-solid fa-video"></i> Video Player`;
            body.innerHTML = `
                <div class="preview-media-container">
                    <video src="${data.data_uri}" controls autoplay muted style="max-height: 60vh;"></video>
                </div>
            `;
        } else {
            typeBadge.innerHTML = `<i class="fa-solid fa-headphones"></i> Audio Player`;
            body.innerHTML = `
                <div class="preview-media-container">
                    <audio src="${data.data_uri}" controls autoplay></audio>
                </div>
            `;
        }
    } else {
        typeBadge.className = 'badge badge-warning';
        typeBadge.innerHTML = `<i class="fa-solid fa-file-shield"></i> Binary File`;
        body.innerHTML = `
            <div class="preview-unsupported-card">
                <i class="fa-solid ${getFileIconClass(data.filename)} fa-3x text-primary" style="margin-bottom: 1rem;"></i>
                <h4 style="margin-bottom: 0.5rem;">${escapeHtml(data.filename)}</h4>
                <p class="subtext" style="font-size: 0.85rem; margin-bottom: 1.25rem;">
                    ${escapeHtml(data.message || 'This file format is encrypted and verified for secure download.')}
                </p>
            </div>
        `;
    }

    if (data.can_download && downloadCallback) {
        footerInfo.innerHTML = `<i class="fa-solid fa-circle-check text-success"></i> Decrypted in-memory. Click 'Download File' to save to your device.`;
        dlBtn.style.display = 'inline-flex';
        dlBtn.onclick = () => {
            closeModal('modal-file-preview');
            downloadCallback();
        };
    } else {
        footerInfo.innerHTML = `<i class="fa-solid fa-lock text-warning"></i> View Only Access (Download Restricted)`;
        dlBtn.style.display = 'none';
    }

    document.getElementById('modal-file-preview').classList.add('active');
}

async function openTokenShareFilePreview() {
    const state = currentShareTokenState;
    if (!state || !state.token) return;

    const fname = state.shareData ? state.shareData.filename : 'Document';
    renderPreviewLoading(fname);

    const pwdParam = state.passwordInput ? `?password=${encodeURIComponent(state.passwordInput)}&otp_verified=true` : `?otp_verified=true`;

    try {
        const res = await fetch(`${API_BASE}/shares/token/${state.token}/preview${pwdParam}`);
        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.detail || 'Failed to load online preview');
        }

        renderPreviewModal(data, fname, () => downloadTokenSharedFile());
    } catch (err) {
        showToast(err.message, 'error');
        closeModal('modal-file-preview');
    }
}

async function downloadTokenSharedFile() {
    const state = currentShareTokenState;
    if (!state || !state.token) return;

    const fname = state.shareData ? state.shareData.filename : 'shared_file';
    showToast(`Downloading and decrypting '${fname}'...`, 'info');

    const pwdParam = state.passwordInput ? `?password=${encodeURIComponent(state.passwordInput)}&otp_verified=true` : `?otp_verified=true`;
    const downloadUrl = `${API_BASE}/shares/token/${state.token}/download${pwdParam}`;

    try {
        const res = await fetch(downloadUrl);
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Download failed');
        }

        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = fname;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        showToast(`'${fname}' downloaded successfully!`, 'success');
    } catch (err) {
        showToast(err.message, 'error');
    }
}

async function previewVaultFile(fileId, filename) {
    renderPreviewLoading(filename);
    try {
        const res = await fetch(`${API_BASE}/files/${fileId}/preview`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed to generate online preview');

        renderPreviewModal(data, filename, () => downloadFile(fileId, filename));
    } catch (err) {
        showToast(err.message, 'error');
        closeModal('modal-file-preview');
    }
}

