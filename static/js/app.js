const API_BASE = '/api/v1';
let authToken = localStorage.getItem('access_token') || null;
let currentUser = JSON.parse(localStorage.getItem('user_data')) || null;

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
    
    document.getElementById('user-display-name').textContent = currentUser.name;
    const rolePill = document.getElementById('user-display-role');
    rolePill.textContent = currentUser.role;
    
    if (currentUser.role === 'ADMIN') {
        document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'block');
    } else {
        document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'none');
    }

    updateNavActions();
    loadUserFiles();
}

function updateNavActions() {
    const container = document.getElementById('nav-actions');
    if (currentUser) {
        container.innerHTML = `
            <span class="user-email-text"><i class="fa-solid fa-user-lock"></i> ${currentUser.email}</span>
        `;
    } else {
        container.innerHTML = ``;
    }
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
        showToast(err.message, 'error');
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
        showToast(err.message, 'error');
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
    if (tab === 'admin') loadAdminStats();
}

// Files Operations
async function loadUserFiles() {
    const searchInput = document.getElementById('file-search');
    const sortSelect = document.getElementById('file-sort');
    const search = searchInput ? searchInput.value : '';
    const sortBy = sortSelect ? sortSelect.value : 'date_desc';
    const tbody = document.getElementById('files-table-body');
    if (!tbody) return;

    tbody.innerHTML = `<tr><td colspan="5" class="text-center">Loading encrypted files...</td></tr>`;

    try {
        const url = new URL(`${window.location.origin}${API_BASE}/files`);
        if (search) url.searchParams.append('search', search);
        if (sortBy) url.searchParams.append('sort_by', sortBy);

        const res = await fetch(url, {
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

        if (!files || files.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="text-center subtext">No encrypted files uploaded yet. Upload one above!</td></tr>`;
            return;
        }

        tbody.innerHTML = files.map(file => {
            const safeName = escapeHtml(file.original_name || 'Unnamed File');
            const safeMime = escapeHtml((file.mime_type || '').split('/')[1] || 'binary');
            const jsEscapedName = (file.original_name || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
            return `
                <tr>
                    <td><strong><i class="fa-solid fa-file-shield text-primary"></i> ${safeName}</strong></td>
                    <td>${formatBytes(file.file_size)}</td>
                    <td><span class="badge">${safeMime}</span></td>
                    <td>${new Date(file.created_at).toLocaleString()}</td>
                    <td>
                        <div class="demo-btn-group">
                            <button class="btn btn-sm btn-outline" onclick="downloadFile(${file.id}, '${jsEscapedName}')" title="Download & Decrypt"><i class="fa-solid fa-download"></i></button>
                            <button class="btn btn-sm btn-outline" onclick="openShareModal(${file.id}, '${jsEscapedName}')" title="Share Access"><i class="fa-solid fa-share-nodes"></i></button>
                            <button class="btn btn-sm btn-outline" onclick="openRenameModal(${file.id}, '${jsEscapedName}')" title="Rename"><i class="fa-solid fa-pen"></i></button>
                            <button class="btn btn-sm btn-danger" onclick="deleteFile(${file.id})" title="Delete"><i class="fa-solid fa-trash"></i></button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center text-danger">${err.message}</td></tr>`;
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
    showToast(`Encrypting & uploading '${file.name}'...`, 'info');
    const formData = new FormData();
    formData.append('file', file);
    formData.append('folder', '/');

    try {
        const res = await fetch(`${API_BASE}/files/upload`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` },
            body: formData
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Upload failed');

        showToast(`File '${file.name}' uploaded and AES-256 encrypted successfully!`, 'success');
        document.getElementById('file-input').value = '';
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
    if (!confirm('Are you sure you want to delete this encrypted file?')) return;
    try {
        const res = await fetch(`${API_BASE}/files/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!res.ok) throw new Error('Failed to delete file');
        showToast('File deleted successfully', 'success');
        loadUserFiles();
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

        if (!res.ok) throw new Error('Failed to load sent shares');
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

        if (!res.ok) throw new Error('Failed to load audit logs');
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
