const API_BASE = (window.location.protocol === 'file:' || (window.location.port && window.location.port !== '8000'))
    ? 'http://127.0.0.1:8000/api/v1'
    : '/api/v1';
let authToken = localStorage.getItem('access_token') || null;
let currentUser = JSON.parse(localStorage.getItem('user_data')) || null;
let currentFolder = '/';

// Initialize App
document.addEventListener('DOMContentLoaded', () => {
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

// Views Navigation
function showAuthView() {
    document.getElementById('view-auth').classList.add('active');
    document.getElementById('view-dashboard').classList.remove('active');
    updateNavActions();
}

function showDashboardView() {
    document.getElementById('view-auth').classList.remove('active');
    document.getElementById('view-dashboard').classList.add('active');
    
    if (currentUser.role === 'ADMIN') {
        document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'block');
    } else {
        document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'none');
    }

    updateUserHeaderUI();
    loadUserFiles();
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
function setExpiryPreset(hours) {
    const input = document.getElementById('share-expiry');
    if (input) input.value = hours !== null ? hours : '';
}

function setDownloadPreset(count) {
    const input = document.getElementById('share-max-downloads');
    if (input) input.value = count !== null ? count : '';
}

function openShareModal(id, name) {
    document.getElementById('share-file-id').value = id;
    document.getElementById('share-file-name').textContent = name;
    document.getElementById('share-recipient').value = '';
    document.getElementById('share-expiry').value = '';
    document.getElementById('share-max-downloads').value = '';
    document.getElementById('modal-share').classList.add('active');
}

async function submitShareForm() {
    const file_id = parseInt(document.getElementById('share-file-id').value);
    const target_user_identifier = document.getElementById('share-recipient').value.trim();
    const permission = document.getElementById('share-permission').value;
    const expiry_hours = document.getElementById('share-expiry').value ? parseInt(document.getElementById('share-expiry').value) : null;
    const max_downloads = document.getElementById('share-max-downloads').value ? parseInt(document.getElementById('share-max-downloads').value) : null;

    if (!target_user_identifier) {
        showToast('Please enter a recipient email or username', 'error');
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/shares`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ file_id, target_user_identifier, permission, expiry_hours, max_downloads })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Share creation failed');

        let validityMsg = 'File shared successfully!';
        if (expiry_hours) validityMsg += ` Valid for ${expiry_hours}h.`;
        if (max_downloads) validityMsg += ` Limited to ${max_downloads} downloads.`;

        showToast(validityMsg, 'success');
        closeModal('modal-share');
        loadSharedFiles();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// Shared With Me Tab
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

            const isExpired = s.is_expired;
            const isLimitReached = s.max_downloads !== null && s.download_count >= s.max_downloads;
            const canDownload = !isExpired && !isLimitReached && s.permission !== 'VIEW';

            // Calculate human-readable validity text
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
                    <td>${safeSharedBy}</td>
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
    tbody.innerHTML = `<tr><td colspan="6" class="text-center">Loading sent shares...</td></tr>`;

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
            tbody.innerHTML = `<tr><td colspan="6" class="text-center subtext">You have not shared any files with others yet.</td></tr>`;
            return;
        }

        tbody.innerHTML = shares.map(s => {
            const safeFilename = escapeHtml(s.filename || 'Shared File');
            const safeRecipient = escapeHtml(s.shared_with_email || 'Unknown User');
            const isRevoked = s.is_revoked;
            const isExpired = s.is_expired;
            const isLimitReached = s.max_downloads !== null && s.download_count >= s.max_downloads;

            let validityBadge = '<span class="badge badge-success"><i class="fa-solid fa-circle-check"></i> Active</span>';
            if (isRevoked) {
                validityBadge = `<span class="badge badge-danger"><i class="fa-solid fa-ban"></i> Revoked</span>`;
            } else if (isExpired) {
                validityBadge = `<span class="badge badge-danger"><i class="fa-solid fa-clock"></i> Expired</span>`;
            } else if (isLimitReached) {
                validityBadge = `<span class="badge badge-warning"><i class="fa-solid fa-ban"></i> Limit Reached</span>`;
            } else if (s.expiry_at) {
                const expiryDate = new Date(s.expiry_at);
                const diffMs = expiryDate - new Date();
                const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
                validityBadge = `<span class="badge badge-success"><i class="fa-solid fa-clock"></i> Expires in ${diffHours}h</span>`;
            }

            return `
                <tr>
                    <td><strong><i class="fa-solid fa-share-nodes text-primary"></i> ${safeFilename}</strong></td>
                    <td>${safeRecipient}</td>
                    <td><span class="badge">${escapeHtml(s.permission)}</span></td>
                    <td>${validityBadge}</td>
                    <td>${s.download_count} / ${s.max_downloads !== null ? s.max_downloads : '∞'}</td>
                    <td>
                        ${!isRevoked ? 
                            `<button class="btn btn-sm btn-danger" onclick="revokeShareAccess(${s.id})"><i class="fa-solid fa-user-xmark"></i> Revoke</button>` : 
                            `<span class="subtext">Revoked</span>`}
                    </td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">${err.message}</td></tr>`;
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

// Admin Tab
async function loadAdminStats() {
    try {
        const res = await fetch(`${API_BASE}/admin/stats`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!res.ok) throw new Error('Admin access denied');
        const stats = await res.json();

        document.getElementById('stat-total-users').textContent = stats.total_users;
        document.getElementById('stat-total-files').textContent = stats.total_files;
        document.getElementById('stat-storage-used').textContent = formatBytes(stats.storage_used_bytes);
        document.getElementById('stat-security-events').textContent = stats.security_events;

        // Load security events table
        const logsRes = await fetch(`${API_BASE}/audit/logs?limit=30`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const logs = await logsRes.json();
        const securityLogs = logs.filter(l => !l.success || l.action.includes('UNAUTHORIZED') || l.action.includes('FAILED'));

        const tbody = document.getElementById('admin-security-table');
        if (securityLogs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" class="text-center subtext">No security violations or failed events detected.</td></tr>`;
        } else {
            tbody.innerHTML = securityLogs.map(l => `
                <tr>
                    <td>${new Date(l.created_at).toLocaleString()}</td>
                    <td>${l.user_email || l.ip_address || 'Unknown'}</td>
                    <td><span class="badge badge-danger">${l.action}</span></td>
                    <td>${l.details || '-'}</td>
                </tr>
            `).join('');
        }
    } catch (err) {
        showToast(err.message, 'error');
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

function updateUserHeaderUI() {
    if (!currentUser) return;

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

function checkPasswordStrength(val) {
    const fill = document.getElementById('strength-bar-fill');
    const label = document.getElementById('strength-label');

    const hasLength = val.length >= 8;
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
