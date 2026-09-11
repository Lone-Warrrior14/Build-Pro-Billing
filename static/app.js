let state = {
    customers: [],
    products: [],
    invoices: [],
    kpis: {},
    billLines: [],
    currentRole: 'admin',
    currentUser: null
};

function openLoginOverlay() {
    const overlay = document.getElementById('login-overlay');
    const alertBox = document.getElementById('login-alert');
    if (alertBox) alertBox.classList.add('d-none');
    if (overlay) overlay.classList.remove('d-none');
    document.body.classList.add('login-overlay-active');
}

function closeLoginOverlay() {
    const overlay = document.getElementById('login-overlay');
    if (overlay) overlay.classList.add('d-none');
    document.body.classList.remove('login-overlay-active');
}

async function checkSession() {
    try {
        const res = await fetch('/api/me');
        const data = await res.json();
        const loginBtn = document.getElementById('header-login-btn');
        const logoutBtn = document.getElementById('header-logout-btn');
        const pwBtn = document.getElementById('header-pw-btn');

        if (data.authenticated && data.user) {
            state.currentUser = data.user;
            switchRole(data.user.role);
            closeLoginOverlay();
            if (loginBtn) loginBtn.classList.add('d-none');
            if (logoutBtn) logoutBtn.classList.remove('d-none');
            if (pwBtn) pwBtn.classList.remove('d-none');
            loadAllData();
        } else {
            openLoginOverlay();
            if (loginBtn) loginBtn.classList.remove('d-none');
            if (logoutBtn) logoutBtn.classList.add('d-none');
            if (pwBtn) pwBtn.classList.add('d-none');
        }
    } catch (e) {
        console.error("Session check failed", e);
        openLoginOverlay();
    }
}

async function loadAllData() {
    try {
        if (typeof loadDashboardData === 'function') await loadDashboardData();
        if (typeof loadInvoices === 'function') await loadInvoices();
        if (typeof loadNewOrders === 'function') await loadDeliveryRequests();
        if (typeof loadDraftOrders === 'function') await loadDeliveryRequests();
        if (typeof loadCustomers === 'function') await loadCustomers();
        if (typeof loadClients === 'function') await loadClients();
        if (typeof loadProducts === 'function') await loadProducts();
    } catch (err) {
        console.error("Error refreshing data:", err);
    }
}

async function handleLoginSubmit(e) {
    e.preventDefault();
    const alertBox = document.getElementById('login-alert');
    const submitBtn = document.getElementById('login-submit-btn');
    const usernameInput = document.getElementById('login-username');
    const passwordInput = document.getElementById('login-password');

    alertBox.classList.add('d-none');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i> Verifying...';

    try {
        const res = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: usernameInput.value.trim(),
                password: passwordInput.value
            })
        });
        const data = await res.json();

        if (data.success) {
            state.currentUser = data.user;
            const loginBtn = document.getElementById('header-login-btn');
            const logoutBtn = document.getElementById('header-logout-btn');
            const pwBtn = document.getElementById('header-pw-btn');

            closeLoginOverlay();
            if (loginBtn) loginBtn.classList.add('d-none');
            if (logoutBtn) logoutBtn.classList.remove('d-none');
            if (pwBtn) pwBtn.classList.remove('d-none');
            if (passwordInput) passwordInput.value = '';

            try {
                switchRole(data.user.role);
            } catch (roleErr) {
                console.error("Error in switchRole:", roleErr);
            }

            try {
                loadAllData();
            } catch (dataErr) {
                console.error("Error in loadAllData:", dataErr);
            }
        } else {
            alertBox.innerText = data.error || 'Invalid credentials';
            alertBox.classList.remove('d-none');
        }
    } catch (err) {
        console.error("Login verification fetch error:", err);
        alertBox.innerText = 'Server error during login verification.';
        alertBox.classList.remove('d-none');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fa-solid fa-right-to-bracket"></i> Sign In';
    }
}

async function logout() {
    if (!confirm("Are you sure you want to log out?")) return;
    try {
        await fetch('/api/logout', { method: 'POST' });
    } catch (e) {
        console.error("Logout error:", e);
    }
    state.currentUser = null;
    state.currentRole = null;
    const nameElem = document.getElementById('user-display-name');
    if (nameElem) nameElem.innerText = 'Guest User';
    const badge = document.getElementById('user-role-badge');
    if (badge) {
        badge.className = "badge bg-secondary";
        badge.innerText = "Role: Guest";
    }
    const loginBtn = document.getElementById('header-login-btn');
    if (loginBtn) loginBtn.classList.remove('d-none');
    const logoutBtn = document.getElementById('header-logout-btn');
    if (logoutBtn) logoutBtn.classList.add('d-none');
    const pwBtn = document.getElementById('header-pw-btn');
    if (pwBtn) pwBtn.classList.add('d-none');
    openLoginOverlay();
    window.location.reload();
}

function switchRole(newRole) {
    state.currentRole = newRole;
    let label = state.currentUser ? (state.currentUser.full_name || state.currentUser.username) : 'Guest User';
    const nameElem = document.getElementById('user-display-name');
    if (nameElem) nameElem.innerText = label;

    const badge = document.getElementById('user-role-badge');
    const navNewBill = document.getElementById('nav-new-bill');
    const navRequestOrder = document.getElementById('nav-request-order');
    const dashboardBtn = document.getElementById('dashboard-create-btn');

    if (newRole === 'sales_executive') {
        if (badge) {
            badge.className = "badge bg-warning text-dark px-2 py-1";
            badge.innerText = "Sales Manager";
        }
        if (navNewBill) {
            navNewBill.innerHTML = '<i class="fa-solid fa-file-invoice-dollar me-1"></i> Invoice Generator';
        }
        if (navRequestOrder) {
            navRequestOrder.classList.remove('d-none');
        }
        if (dashboardBtn) {
            dashboardBtn.className = "btn btn-primary fw-bold";
            dashboardBtn.innerHTML = '<i class="fa-solid fa-file-invoice-dollar me-1"></i> Invoice Generator';
        }
        // Hide admin-only nav tabs
        document.querySelectorAll('.admin-only').forEach(el => el.classList.add('d-none'));
        setInvoiceFormMode('order_request');
    } else {
        if (badge) {
            badge.className = newRole === 'admin' ? "badge bg-primary px-2 py-1" : "badge bg-info text-dark px-2 py-1";
            badge.innerText = newRole === 'admin' ? "Administrator" : "Billing User";
        }
        if (navNewBill) {
            navNewBill.innerHTML = '<i class="fa-solid fa-file-invoice-dollar me-1"></i> Invoice Generator';
        }
        if (navRequestOrder) {
            if (newRole === 'billing') {
                navRequestOrder.classList.add('d-none');
            } else {
                navRequestOrder.classList.remove('d-none');
            }
        }
        if (dashboardBtn) {
            dashboardBtn.className = "btn btn-primary";
            dashboardBtn.innerHTML = '<i class="fa-solid fa-plus me-1"></i> Create Invoice';
        }
        if (newRole === 'admin') {
            document.querySelectorAll('.admin-only').forEach(el => el.classList.remove('d-none'));
        } else {
            document.querySelectorAll('.admin-only').forEach(el => el.classList.add('d-none'));
        }
        setInvoiceFormMode('invoice');
    }

    const addProdBtn = document.getElementById('btn-add-new-product');
    if (addProdBtn) {
        if (newRole === 'admin' || newRole === 'sales_executive') {
            addProdBtn.classList.remove('d-none');
        } else {
            addProdBtn.classList.add('d-none');
        }
    }

    renderInvoicesList(state.invoices);
    loadCustomers();
    loadProducts();
}

function setInvoiceFormMode(mode) {
    state.invoiceFormMode = mode;
    const title = document.getElementById('new-bill-title');
    const subtitle = document.getElementById('new-bill-subtitle');
    const btn = document.getElementById('btn-submit-bill');
    const paymentContainer = document.getElementById('bill-payment-container');
    const invNumContainer = document.getElementById('bill-invoice-number-container');

    if (mode === 'order_request') {
        if (title) title.innerText = "Request Sales Order";
        if (subtitle) subtitle.innerText = "Create a draft order for inventory check and draft bill verification";
        if (btn) {
            btn.className = "btn btn-warning btn-lg w-100 py-3 fw-bold";
            btn.innerHTML = '<i class="fa-solid fa-paper-plane me-2"></i> Submit Sales Order Request';
        }
        if (paymentContainer) paymentContainer.classList.add('d-none');
        if (invNumContainer) invNumContainer.classList.add('d-none');
    } else {
        if (title) title.innerText = "Invoice Generator";
        if (subtitle) subtitle.innerText = "Create an official GST Invoice";
        if (btn) {
            btn.className = "btn btn-success btn-lg w-100 py-3 fw-bold";
            btn.innerHTML = '<i class="fa-solid fa-file-invoice-dollar me-2"></i> Generate & Print Invoice';
        }
        if (paymentContainer) paymentContainer.classList.remove('d-none');
        if (invNumContainer) invNumContainer.classList.remove('d-none');
    }
}

function openInvoiceGeneratorForm() {
    if (typeof resetBillForm === 'function') resetBillForm();
    setInvoiceFormMode('invoice');
    switchTab('new-bill');
}

function openRequestOrderForm() {
    if (typeof resetBillForm === 'function') resetBillForm();
    setInvoiceFormMode('order_request');
    switchTab('new-bill');
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    checkSession();
    // Add default initial line item in New Bill
    addBillLine();
});

function switchTab(tabId) {
    if (tabId === 'users' && state.currentRole !== 'admin') {
        alert("Access Denied: User Management is restricted to Administrators only.");
        switchTab('dashboard');
        return;
    }

    // Auto-collapse mobile navbar on mobile view after selecting a menu item
    const navbarCollapse = document.getElementById('navbarNav');
    if (navbarCollapse && navbarCollapse.classList.contains('show') && typeof bootstrap !== 'undefined') {
        try {
            const bsCollapse = bootstrap.Collapse.getInstance(navbarCollapse) || new bootstrap.Collapse(navbarCollapse);
            bsCollapse.hide();
        } catch (e) {
            navbarCollapse.classList.remove('show');
        }
    }

    document.querySelectorAll('.tab-page').forEach(el => el.classList.add('d-none'));
    document.querySelectorAll('.nav-link').forEach(el => el.classList.remove('active'));

    const section = document.getElementById(`tab-${tabId}`);
    if (section) section.classList.remove('d-none');
    
    let navId = `nav-${tabId}`;
    if (tabId === 'new-bill') {
        navId = state.invoiceFormMode === 'order_request' ? 'nav-request-order' : 'nav-new-bill';
    }
    const nav = document.getElementById(navId);
    if (nav) nav.classList.add('active');

    if (tabId === 'dashboard') loadDashboardData();
    if (tabId === 'invoices') loadInvoices();
    if (tabId === 'delivery-requests') loadDeliveryRequests();
    if (tabId === 'invalid-tab') loadDeliveryRequests();
    if (tabId === 'customers') loadCustomers();
    if (tabId === 'clients') loadClients();
    if (tabId === 'products') loadProducts();
    if (tabId === 'sealed-bills') loadSealedBills();
    if (tabId === 'recycle-bin') loadRecycleBin();
    if (tabId === 'users') loadUsers();
    if (tabId === 'construction-bill') initSqftBillingTab();
}

async function loadSealedBills() {
    try {
        const res = await fetch('/api/invoices');
        const data = await res.json();
        if (!data.success) return;

        const tbody = document.getElementById('sealed-bills-tbody');
        tbody.innerHTML = '';

        const sealedInvoices = data.invoices.filter(i => i.status !== 'deleted' && i.is_sealed);

        if (sealedInvoices.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">No sealed bills created yet. Create a new bill with "Apply Official Seal" checked.</td></tr>';
            return;
        }

        sealedInvoices.forEach(inv => {
            const tr = document.createElement('tr');
            let badgeClass = inv.payment_status === 'paid' ? 'badge-paid' : (inv.payment_status === 'partial' ? 'badge-partial' : 'badge-unpaid');

            tr.innerHTML = `
                <td class="fw-bold text-info"><i class="fa-solid fa-stamp me-1"></i>${inv.invoice_number}</td>
                <td>${inv.invoice_date.split('T')[0]}</td>
                <td class="fw-medium">${inv.customer_name}</td>
                <td class="fw-bold">₹${inv.grand_total.toFixed(2)}</td>
                <td><span class="badge-status ${badgeClass}">${inv.payment_status.toUpperCase()}</span></td>
                <td><span class="badge bg-success-subtle text-success border border-success-subtle rounded-pill px-2 py-1"><i class="fa-solid fa-seal me-1"></i>Official Seal Verified</span></td>
                <td class="text-center">
                    <button class="btn btn-sm btn-info me-1 text-white" title="View & Print Sealed Bill PDF" onclick="viewInvoiceDetail(${inv.id})"><i class="fa-solid fa-print me-1"></i> View / PDF</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Failed to load sealed bills", e);
    }
}

// Global Refresh Data
async function loadAllData() {
    await Promise.all([
        loadDashboardData(),
        loadCustomers(),
        loadProducts(),
        loadInvoices(),
        loadUsers()
    ]);
}

// 1. DASHBOARD & KPIS
async function loadDashboardData() {
    try {
        const res = await fetch('/api/dashboard/stats');
        const data = await res.json();
        if (!data.success) return;

        state.kpis = data.kpis;
        state.monthlyOverview = data.monthly_overview || [];

        // Populate Month Filter Select
        const monthSelect = document.getElementById('kpi-month-select');
        if (monthSelect) {
            const currentVal = monthSelect.value || 'all';
            monthSelect.innerHTML = '<option value="all">📅 All Time (Total)</option>';
            state.monthlyOverview.forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.year_month;
                opt.textContent = `📆 ${m.month_name}`;
                monthSelect.appendChild(opt);
            });
            monthSelect.value = currentVal;
        }

        // Apply KPI filter (All Time or selected month)
        updateKpiDisplay(monthSelect ? monthSelect.value : 'all');

        // Update Quick Monthly Stats
        const now = new Date();
        const curYearMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
        const curMonthData = state.monthlyOverview.find(m => m.year_month === curYearMonth);

        document.getElementById('kpi-current-month-sales').innerText = `₹${(curMonthData ? curMonthData.total_sales : 0).toFixed(2)}`;
        document.getElementById('kpi-current-month-paid').innerText = `₹${(curMonthData ? curMonthData.collected : 0).toFixed(2)}`;

        const totalMonths = state.monthlyOverview.length || 1;
        const avgMonthlySales = data.kpis.total_sales / totalMonths;
        document.getElementById('kpi-monthly-avg').innerText = `₹${avgMonthlySales.toFixed(2)} / mo`;

        // Render Recent Invoices
        const tbody = document.getElementById('recent-invoices-tbody');
        tbody.innerHTML = '';
        if (data.recent_invoices.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-4">No invoices issued yet.</td></tr>';
        } else {
            data.recent_invoices.forEach(inv => {
                const tr = document.createElement('tr');
                const badgeClass = inv.payment_status === 'paid' ? 'badge-paid' : (inv.payment_status === 'partial' ? 'badge-partial' : 'badge-unpaid');
                tr.innerHTML = `
                    <td class="fw-bold text-primary">${inv.invoice_number}</td>
                    <td>${inv.invoice_date.split('T')[0]}</td>
                    <td>${inv.customer_name}</td>
                    <td class="fw-bold">₹${inv.grand_total.toFixed(2)}</td>
                    <td><span class="badge-status ${badgeClass}">${inv.payment_status.toUpperCase()}</span></td>
                    <td>
                        <button class="btn btn-sm btn-outline-info me-1" onclick="viewInvoiceDetail(${inv.id})"><i class="fa-solid fa-eye"></i></button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }

        // Render Monthly Overview
        const monthlyTbody = document.getElementById('monthly-overview-tbody');
        if (monthlyTbody) {
            monthlyTbody.innerHTML = '';
            const monthlyRecords = state.monthlyOverview;
            if (monthlyRecords.length === 0) {
                monthlyTbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3">No monthly sales history found.</td></tr>';
            } else {
                monthlyRecords.forEach(m => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td class="fw-bold text-light"><i class="fa-solid fa-calendar-day text-info me-2"></i>${m.month_name}</td>
                        <td><span class="badge bg-secondary">${m.count} bill${m.count > 1 ? 's' : ''}</span></td>
                        <td class="fw-bold text-primary">₹${m.total_sales.toFixed(2)}</td>
                        <td class="text-success fw-bold">₹${m.collected.toFixed(2)}</td>
                        <td class="text-danger fw-bold">${m.outstanding > 0 ? '₹' + m.outstanding.toFixed(2) : '₹0.00'}</td>
                    `;
                    monthlyTbody.appendChild(tr);
                });
            }
        }
    } catch (err) {
        console.error("Error loading dashboard data:", err);
    }
}

function onKpiMonthFilterChange(selectedKey) {
    updateKpiDisplay(selectedKey);
}

function updateKpiDisplay(selectedKey) {
    if (!state.kpis) return;

    if (!selectedKey || selectedKey === 'all') {
        document.getElementById('kpi-label-sales').innerText = "TOTAL SALES";
        document.getElementById('kpi-sub-sales').innerHTML = `<i class="fa-solid fa-arrow-trend-up text-success me-1"></i> All time revenue`;
        document.getElementById('kpi-total-sales').innerText = `₹${state.kpis.total_sales.toFixed(2)}`;

        document.getElementById('kpi-label-paid').innerText = "COLLECTED AMOUNT";
        document.getElementById('kpi-sub-paid').innerHTML = `<i class="fa-solid fa-circle-check text-success me-1"></i> Cleared payments`;
        document.getElementById('kpi-paid').innerText = `₹${state.kpis.collected.toFixed(2)}`;

        document.getElementById('kpi-label-outstanding').innerText = "OUTSTANDING DUES";
        document.getElementById('kpi-sub-outstanding').innerHTML = `<i class="fa-solid fa-clock-history text-warning me-1"></i> Pending receivable`;
        document.getElementById('kpi-outstanding').innerText = `₹${state.kpis.outstanding.toFixed(2)}`;

        document.getElementById('kpi-label-count').innerText = "TOTAL INVOICES";
        document.getElementById('kpi-sub-count').innerHTML = `<i class="fa-solid fa-file-lines me-1"></i> Completed bills`;
        document.getElementById('kpi-invoice-count').innerText = state.kpis.invoice_count;
    } else {
        const m = (state.monthlyOverview || []).find(item => item.year_month === selectedKey);
        if (m) {
            document.getElementById('kpi-label-sales').innerText = `SALES (${m.month_name.toUpperCase()})`;
            document.getElementById('kpi-sub-sales').innerHTML = `<i class="fa-solid fa-calendar me-1 text-info"></i> ${m.month_name} revenue`;
            document.getElementById('kpi-total-sales').innerText = `₹${m.total_sales.toFixed(2)}`;

            document.getElementById('kpi-label-paid').innerText = `COLLECTED (${m.month_name.toUpperCase()})`;
            document.getElementById('kpi-sub-paid').innerHTML = `<i class="fa-solid fa-circle-check text-success me-1"></i> ${m.month_name} cleared`;
            document.getElementById('kpi-paid').innerText = `₹${m.collected.toFixed(2)}`;

            document.getElementById('kpi-label-outstanding').innerText = `DUES (${m.month_name.toUpperCase()})`;
            document.getElementById('kpi-sub-outstanding').innerHTML = `<i class="fa-solid fa-clock-history text-warning me-1"></i> ${m.month_name} pending`;
            document.getElementById('kpi-outstanding').innerText = `₹${m.outstanding.toFixed(2)}`;

            document.getElementById('kpi-label-count').innerText = `BILLS (${m.month_name.toUpperCase()})`;
            document.getElementById('kpi-sub-count').innerHTML = `<i class="fa-solid fa-file-lines me-1"></i> ${m.month_name} count`;
            document.getElementById('kpi-invoice-count').innerText = m.count;
        }
    }
}

// 2. CUSTOMERS & CLIENTS
state.shopsList = [];
state.clientsList = [];

async function loadCustomers() {
    try {
        const res = await fetch('/api/customers?type=shop');
        const data = await res.json();
        if (!data.success) return;

        state.shopsList = data.customers;
        renderCustomersTable(state.shopsList);
        
        // Update New Bill select dropdown
        populateBillCustomerDropdown(state.shopsList);
    } catch (err) {
        console.error("Error loading customers:", err);
    }
}

let billCustomerTomSelect = null;

function populateBillCustomerDropdown(list) {
    const select = document.getElementById('bill-customer-select');
    if (!select) return;

    if (billCustomerTomSelect) {
        billCustomerTomSelect.destroy();
        billCustomerTomSelect = null;
    }

    const selectedVal = select.value;
    select.innerHTML = '<option value="">-- Choose Customer / Shop --</option>';
    list.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.id;
        const gstinText = c.gstin ? `GSTIN: ${c.gstin}` : 'No GSTIN';
        opt.textContent = `${c.shop_name} (${gstinText})`;
        select.appendChild(opt);
    });
    if (selectedVal && list.some(c => c.id === parseInt(selectedVal))) {
        select.value = selectedVal;
    }

    if (typeof TomSelect !== 'undefined') {
        billCustomerTomSelect = new TomSelect('#bill-customer-select', {
            create: false,
            placeholder: "🔍 Type Shop Name or GSTIN to search...",
            onChange: function() {
                onCustomerSelectChange();
            }
        });
    }
}

function renderCustomersTable(list) {
    const tbody = document.getElementById('customers-list-tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    if (list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">No shops/customers found matching search.</td></tr>';
        return;
    }
    list.forEach(c => {
        const tr = document.createElement('tr');
        const mapLink = c.maps_location_link ? `<a href="${c.maps_location_link}" target="_blank" class="btn btn-sm btn-outline-info" title="Open Location Map"><i class="fa-solid fa-map-location-dot me-1"></i> Map</a>` : '<span class="text-muted small">-</span>';
        tr.innerHTML = `
            <td class="fw-bold text-light">${c.shop_name}</td>
            <td>${c.contact_person || '-'}</td>
            <td>${c.phone || '-'}</td>
            <td>${c.gstin || '-'}</td>
            <td>${mapLink}</td>
            <td>₹${c.opening_balance.toFixed(2)}</td>
            <td class="fw-bold text-warning">₹${c.current_balance.toFixed(2)}</td>
            <td>
                <button class="btn btn-sm btn-outline-warning me-1" onclick="viewCustomerLedger(${c.id})"><i class="fa-solid fa-book me-1"></i> Ledger</button>
                <button class="btn btn-sm btn-outline-info me-1" title="Edit Shop Details / Map" onclick="editCustomer(${c.id})"><i class="fa-solid fa-pen"></i></button>
                ${state.currentRole === 'admin' ? `<button class="btn btn-sm btn-outline-danger" title="Remove Shop" onclick="deleteCustomer(${c.id}, '${c.shop_name}')"><i class="fa-solid fa-trash"></i></button>` : ''}
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function editCustomer(id) {
    const cust = state.shopsList.find(c => c.id === id);
    if (!cust) return;

    state.editingCustomerId = id;

    const modalEl = document.getElementById('newCustomerModal');
    if (!modalEl) return;

    const modalTitle = document.getElementById('m-cust-modal-title');
    if (modalTitle) modalTitle.innerText = "Edit Shop / Customer Details";

    document.getElementById('m-cust-shop').value = cust.shop_name || '';
    const personEl = document.getElementById('m-cust-person') || document.getElementById('m-cust-contact');
    if (personEl) personEl.value = cust.contact_person || '';
    if (document.getElementById('m-cust-phone')) document.getElementById('m-cust-phone').value = cust.phone || '';
    if (document.getElementById('m-cust-gstin')) document.getElementById('m-cust-gstin').value = cust.gstin || '';
    if (document.getElementById('m-cust-address')) document.getElementById('m-cust-address').value = cust.address || '';
    if (document.getElementById('m-cust-maps-link')) document.getElementById('m-cust-maps-link').value = cust.maps_location_link || '';
    if (document.getElementById('m-cust-balance')) document.getElementById('m-cust-balance').value = cust.opening_balance || 0;

    const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
    modal.show();
}

function filterCustomersTable() {
    const query = (document.getElementById('search-customers-input')?.value || '').toLowerCase().trim();
    if (!query) {
        renderCustomersTable(state.shopsList);
        return;
    }
    const filtered = state.shopsList.filter(c => 
        (c.shop_name || '').toLowerCase().includes(query) ||
        (c.contact_person || '').toLowerCase().includes(query) ||
        (c.phone || '').toLowerCase().includes(query) ||
        (c.gstin || '').toLowerCase().includes(query)
    );
    renderCustomersTable(filtered);
}

async function loadClients() {
    try {
        const res = await fetch('/api/customers?type=client');
        const data = await res.json();
        if (!data.success) return;

        state.clientsList = data.customers;
        renderClientsTable(state.clientsList);
        populateSqftCustomers();
    } catch (err) {
        console.error("Error loading clients:", err);
    }
}

function renderClientsTable(list) {
    const tbody = document.getElementById('clients-list-tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    if (list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">No construction clients found matching search.</td></tr>';
        return;
    }
    list.forEach(c => {
        const tr = document.createElement('tr');
        const mapLink = c.maps_location_link ? `<a href="${c.maps_location_link}" target="_blank" class="btn btn-sm btn-outline-info" title="Open Location Map"><i class="fa-solid fa-map-location-dot me-1"></i> Site Map</a>` : '<span class="text-muted small">-</span>';
        tr.innerHTML = `
            <td class="fw-bold text-info">${c.shop_name}</td>
            <td>${c.contact_person || '-'}</td>
            <td>${c.phone || '-'}</td>
            <td>${mapLink}</td>
            <td>₹${c.opening_balance.toFixed(2)}</td>
            <td class="fw-bold text-warning">₹${c.current_balance.toFixed(2)}</td>
            <td>
                <button class="btn btn-sm btn-outline-warning me-1" onclick="viewCustomerLedger(${c.id})"><i class="fa-solid fa-book me-1"></i> Ledger</button>
                ${state.currentRole === 'admin' ? `<button class="btn btn-sm btn-outline-danger" title="Remove Client" onclick="deleteCustomer(${c.id}, '${c.shop_name}')"><i class="fa-solid fa-trash"></i></button>` : ''}
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function filterClientsTable() {
    const query = (document.getElementById('search-clients-input')?.value || '').toLowerCase().trim();
    if (!query) {
        renderClientsTable(state.clientsList);
        return;
    }
    const filtered = state.clientsList.filter(c => 
        (c.shop_name || '').toLowerCase().includes(query) ||
        (c.contact_person || '').toLowerCase().includes(query) ||
        (c.phone || '').toLowerCase().includes(query)
    );
    renderClientsTable(filtered);
}

function openAddPartyModal(type) {
    const modalEl = document.getElementById('newCustomerModal');
    const typeSelect = document.getElementById('m-cust-type');

    if (typeSelect) {
        typeSelect.value = type === 'client' ? 'client' : 'shop';
    }
    onModalTypeChange(typeSelect ? typeSelect.value : type);

    const modalInstance = bootstrap.Modal.getOrCreateInstance(modalEl);
    modalInstance.show();
}

function onModalTypeChange(selectedType) {
    const titleEl = document.getElementById('m-cust-modal-title');
    const nameLabel = document.getElementById('m-cust-name-label');
    const saveBtn = document.querySelector('#newCustomerModal .modal-footer .btn-primary');

    if (selectedType === 'client') {
        if (titleEl) titleEl.innerHTML = '<i class="fa-solid fa-user-shield me-2 text-info"></i>Add New Construction Client';
        if (nameLabel) nameLabel.innerText = 'CLIENT / PROJECT NAME *';
        if (saveBtn) saveBtn.innerText = 'Save Construction Client';
    } else {
        if (titleEl) titleEl.innerHTML = '<i class="fa-solid fa-store me-2 text-primary"></i>Add New Customer / Shop';
        if (nameLabel) nameLabel.innerText = 'SHOP NAME *';
        if (saveBtn) saveBtn.innerText = 'Save Shop / Customer';
    }
}

async function viewCustomerLedger(custId) {
    const modalEl = document.getElementById('customerLedgerModal');
    const modalBody = document.getElementById('ledger-modal-body');
    modalBody.innerHTML = '<div class="text-center py-4"><i class="fa-solid fa-spinner fa-spin fa-2x"></i> Loading Ledger...</div>';
    
    let modalInstance = bootstrap.Modal.getInstance(modalEl);
    if (!modalInstance) {
        modalInstance = new bootstrap.Modal(modalEl);
    }
    modalInstance.show();

    try {
        const res = await fetch(`/api/customers/${custId}/ledger`);
        const data = await res.json();
        if (!data.success) {
            modalBody.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
            return;
        }

        const invoicesList = data.invoices || [];
        modalBody.innerHTML = `
            <div class="d-flex justify-content-between align-items-center p-3 rounded mb-4" style="background-color: rgba(15, 23, 42, 0.9); border: 1px solid #334155;">
                <div>
                    <h5 class="fw-bold text-light mb-1">${data.shop_name}</h5>
                    <small class="text-secondary">Opening Balance: ₹${data.opening_balance.toFixed(2)}</small>
                </div>
                <div class="text-end">
                    <small class="text-secondary">Current Balance Due</small>
                    <div class="fs-4 fw-bold text-warning">₹${data.current_balance.toFixed(2)}</div>
                </div>
            </div>

            <ul class="nav nav-tabs nav-fill mb-3" id="ledgerTabs" role="tablist">
                <li class="nav-item" role="presentation">
                    <button class="nav-link active fw-bold text-light" id="ledger-statement-tab" data-bs-toggle="tab" data-bs-target="#ledger-statement-panel" type="button"><i class="fa-solid fa-book-open me-2"></i>Ledger Statement (${data.entries.length})</button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link fw-bold text-light" id="ledger-invoices-tab" data-bs-toggle="tab" data-bs-target="#ledger-invoices-panel" type="button"><i class="fa-solid fa-file-invoice me-2"></i>Invoices Issued (${invoicesList.length})</button>
                </li>
            </ul>

            <div class="tab-content" id="ledgerTabsContent">
                <!-- PANEL 1: LEDGER STATEMENT -->
                <div class="tab-pane fade show active" id="ledger-statement-panel">
                    <div class="table-responsive">
                        <table class="table table-custom">
                            <thead>
                                <tr>
                                    <th>Date</th>
                                    <th>Type</th>
                                    <th>Description</th>
                                    <th>Debit (₹)</th>
                                    <th>Credit (₹)</th>
                                    <th>Balance (₹)</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${data.entries.length === 0 ? '<tr><td colspan="6" class="text-center text-muted py-3">No ledger transactions yet.</td></tr>' : ''}
                                ${data.entries.map(e => `
                                    <tr>
                                        <td>${e.date ? (e.date.includes('T') ? e.date.split('T')[0] : e.date) : '-'}</td>
                                        <td><span class="badge ${e.type === 'invoice' ? 'bg-primary' : 'bg-success'}">${(e.type || '').toUpperCase()}</span></td>
                                        <td>${e.description || ''}</td>
                                        <td class="text-danger">${e.debit > 0 ? '₹' + e.debit.toFixed(2) : '-'}</td>
                                        <td class="text-success">${e.credit > 0 ? '₹' + e.credit.toFixed(2) : '-'}</td>
                                        <td class="fw-bold text-light">₹${(e.balance || 0).toFixed(2)}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- PANEL 2: INVOICES LIST -->
                <div class="tab-pane fade" id="ledger-invoices-panel">
                    <div class="table-responsive">
                        <table class="table table-custom">
                            <thead>
                                <tr>
                                    <th>Invoice #</th>
                                    <th>Date</th>
                                    <th>Grand Total</th>
                                    <th>Paid</th>
                                    <th>Balance</th>
                                    <th>Status</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${invoicesList.length === 0 ? '<tr><td colspan="7" class="text-center text-muted py-3">No invoices issued for this customer yet.</td></tr>' : ''}
                                ${invoicesList.map(inv => `
                                    <tr>
                                        <td class="fw-bold text-primary">${inv.invoice_number || ''}</td>
                                        <td>${inv.invoice_date ? (inv.invoice_date.includes('T') ? inv.invoice_date.split('T')[0] : inv.invoice_date) : '-'}</td>
                                        <td class="fw-bold text-light">₹${(inv.grand_total || 0).toFixed(2)}</td>
                                        <td class="text-success">₹${(inv.amount_paid || 0).toFixed(2)}</td>
                                        <td class="text-danger fw-bold">₹${(inv.balance || 0).toFixed(2)}</td>
                                        <td><span class="badge ${(inv.payment_status || '') === 'paid' ? 'bg-success' : ((inv.payment_status || '') === 'partial' ? 'bg-warning text-dark' : 'bg-danger')}">${(inv.payment_status || '').toUpperCase()}</span></td>
                                        <td>
                                            <button class="btn btn-sm btn-outline-info" title="View Invoice" onclick="viewInvoiceDetail(${inv.id})"><i class="fa-solid fa-eye"></i> View</button>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    } catch (e) {
        modalBody.innerHTML = `<div class="alert alert-danger">Error loading customer ledger.</div>`;
    }
}

async function deleteCustomer(custId, shopName) {
    if (!confirm(`Are you sure you want to remove shop/customer "${shopName}"?`)) return;
    try {
        const res = await fetch(`/api/customers/${custId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            alert(data.message);
            await loadCustomers();
        } else {
            alert(data.error);
        }
    } catch (e) {
        alert("Failed to delete customer.");
    }
}

// 3. PRODUCTS
let productVolumeChartInstance = null;
let productRevenueChartInstance = null;

async function loadProducts() {
    try {
        const res = await fetch('/api/products');
        const data = await res.json();
        if (!data.success) return;

        state.products = data.products;

        // Populate product month filter dropdown
        populateProductMonthFilter();

        // Calculate & Render Product KPIs based on filter
        filterProductKPIsByMonth();

        updateBillItemDropdowns();

    } catch (err) {
        console.error("Error loading products:", err);
    }
}

function populateProductMonthFilter() {
    const select = document.getElementById('product-month-filter');
    if (!select) return;

    const monthsSet = new Set();
    (state.products || []).forEach(p => {
        if (p.monthly_sales) {
            Object.keys(p.monthly_sales).forEach(mKey => monthsSet.add(mKey));
        }
    });

    const sortedMonths = Array.from(monthsSet).sort().reverse();
    const currentSelected = select.value || 'all';

    select.innerHTML = '<option value="all">📅 All Time Stats</option>';
    sortedMonths.forEach(mKey => {
        const [year, monthNum] = mKey.split('-');
        const dateObj = new Date(parseInt(year), intMonth(monthNum) - 1, 1);
        const monthLabel = dateObj.toLocaleString('en-US', { month: 'long', year: 'numeric' });
        select.innerHTML += `<option value="${mKey}">🗓️ ${monthLabel}</option>`;
    });

    select.value = currentSelected;
}

function intMonth(m) {
    return parseInt(m, 10);
}

function filterProductKPIsByMonth() {
    const selectedMonth = document.getElementById('product-month-filter')?.value || 'all';
    const products = state.products || [];

    const totalCount = products.length;
    let totalUnitsSold = 0;
    let totalRev = 0;
    let topSellerName = '-';
    let maxBags = -1;

    const displayProducts = products.map(p => {
        let qty = 0;
        let rev = 0;

        if (selectedMonth === 'all') {
            qty = p.total_bags_sold || 0;
            rev = p.total_revenue || 0;
        } else if (p.monthly_sales && p.monthly_sales[selectedMonth]) {
            qty = p.monthly_sales[selectedMonth].qty || 0;
            rev = p.monthly_sales[selectedMonth].revenue || 0;
        }

        totalUnitsSold += qty;
        totalRev += rev;

        if (qty > maxBags && qty > 0) {
            maxBags = qty;
            topSellerName = `${p.brand} ${p.product_name}`;
        }

        return {
            ...p,
            display_qty: qty,
            display_revenue: rev
        };
    });

    if (document.getElementById('prod-kpi-count')) document.getElementById('prod-kpi-count').innerText = totalCount;
    if (document.getElementById('prod-kpi-units')) document.getElementById('prod-kpi-units').innerText = `${totalUnitsSold.toLocaleString()} units`;
    if (document.getElementById('prod-kpi-revenue')) document.getElementById('prod-kpi-revenue').innerText = `₹${totalRev.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    if (document.getElementById('prod-kpi-top-seller')) document.getElementById('prod-kpi-top-seller').innerText = topSellerName;

    // Render Product Charts with filtered display values
    renderProductCharts(displayProducts);

    // Render Product Table with filtered display values
    const tbody = document.getElementById('products-list-tbody');
    if (tbody) {
        tbody.innerHTML = '';
        displayProducts.forEach(p => {
            const tr = document.createElement('tr');
            const qtySold = p.display_qty || 0;
            const rev = p.display_revenue || 0;
            tr.innerHTML = `
                <td><span class="badge bg-secondary">${p.brand || 'Generic'}</span></td>
                <td class="fw-bold text-light">${p.product_name}</td>
                <td>${p.variant || '-'}</td>
                <td class="fw-bold text-light">₹${p.mrp.toFixed(2)}</td>
                <td>${p.gst_rate}%</td>
                <td class="fw-bold text-info">${qtySold.toLocaleString()} ${p.unit || 'Bag'}s</td>
                <td class="fw-bold text-success">₹${rev.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                <td>
                    ${state.currentRole === 'admin' ? `<button class="btn btn-sm btn-outline-danger" title="Remove Product" onclick="deleteProduct(${p.id}, '${p.product_name}')"><i class="fa-solid fa-trash"></i></button>` : '<span class="text-muted small">View Only</span>'}
                </td>
            `;
            tbody.appendChild(tr);
        });
    }
}

function renderProductCharts(products) {
    if (typeof Chart === 'undefined') return;

    const labels = products.map(p => `${p.brand} ${p.product_name}`);
    const volumeData = products.map(p => p.display_qty !== undefined ? p.display_qty : (p.total_bags_sold || 0));
    const revenueData = products.map(p => p.display_revenue !== undefined ? p.display_revenue : (p.total_revenue || 0));

    const chartColors = [
        '#0dcaf0', '#20c997', '#ffc107', '#fd7e14', '#0d6efd',
        '#6610f2', '#6f42c1', '#d63384', '#dc3545', '#198754'
    ];

    // Chart 1: Sales Volume Bar Chart
    const ctxVol = document.getElementById('productSalesVolumeChart');
    if (ctxVol) {
        if (productVolumeChartInstance) productVolumeChartInstance.destroy();
        productVolumeChartInstance = new Chart(ctxVol, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Units / Bags Sold',
                    data: volumeData,
                    backgroundColor: 'rgba(13, 202, 240, 0.65)',
                    borderColor: '#0dcaf0',
                    borderWidth: 1.5,
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) { return ` Units Sold: ${context.parsed.y.toLocaleString()}`; }
                        }
                    }
                },
                scales: {
                    x: { ticks: { color: '#90a4ae', font: { size: 11 } }, grid: { display: false } },
                    y: { ticks: { color: '#90a4ae', font: { size: 11 } }, grid: { color: 'rgba(255, 255, 255, 0.08)' } }
                }
            }
        });
    }

    // Chart 2: Revenue Doughnut Chart
    const ctxRev = document.getElementById('productRevenueChart');
    if (ctxRev) {
        if (productRevenueChartInstance) productRevenueChartInstance.destroy();
        productRevenueChartInstance = new Chart(ctxRev, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: revenueData,
                    backgroundColor: chartColors.slice(0, labels.length),
                    borderWidth: 2,
                    borderColor: '#1e293b'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { color: '#e2e8f0', font: { size: 11 }, boxWidth: 12 }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const val = context.parsed;
                                return ` ${context.label}: ₹${val.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
                            }
                        }
                    }
                }
            }
        });
    }
}

async function deleteProduct(prodId, prodName) {
    if (!confirm(`Are you sure you want to remove product "${prodName}"?`)) return;
    try {
        const res = await fetch(`/api/products/${prodId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            alert(data.message);
            await loadProducts();
        } else {
            alert(data.error);
        }
    } catch (e) {
        alert("Failed to delete product.");
    }
}

// 4. INVOICES
async function loadInvoices() {
    try {
        const res = await fetch('/api/invoices');
        const data = await res.json();
        if (!data.success) return;

        state.invoices = data.invoices;
        renderInvoicesList(state.invoices);
    } catch (err) {
        console.error("Error loading invoices:", err);
    }
}

function renderInvoicesList(list) {
    const tbody = document.getElementById('invoices-list-tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!list || !Array.isArray(list) || list.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">No invoices found.</td></tr>';
        return;
    }

    list.forEach(inv => {
        const tr = document.createElement('tr');
        let badgeClass = inv.payment_status === 'paid' ? 'badge-paid' : (inv.payment_status === 'partial' ? 'badge-partial' : 'badge-unpaid');
        let statusText = inv.payment_status.toUpperCase();

        if (inv.status === 'pending_approval') {
            badgeClass = 'bg-warning text-dark px-2 py-1 rounded fw-bold';
            statusText = 'PENDING APPROVAL';
        }

        tr.innerHTML = `
            <td class="fw-bold text-primary">${inv.invoice_number} ${inv.is_sealed ? '<span class="badge bg-info-subtle text-info ms-1" title="Sealed Bill"><i class="fa-solid fa-stamp"></i></span>' : ''}</td>
            <td>${inv.invoice_date.split('T')[0]}</td>
            <td class="fw-medium">${inv.customer_name}</td>
            <td class="fw-bold">₹${inv.grand_total.toFixed(2)}</td>
            <td class="text-success">₹${inv.amount_paid.toFixed(2)}</td>
            <td class="text-danger fw-bold">₹${inv.balance.toFixed(2)}</td>
            <td><span class="badge-status ${badgeClass}">${statusText}</span></td>
            ${state.currentRole === 'admin' ? `<td><span class="badge bg-secondary-subtle text-light border border-secondary px-2 py-1"><i class="fa-solid fa-user me-1 text-info"></i>${inv.created_by || 'Admin'}</span></td>` : ''}
            <td class="text-center">
                <button class="btn btn-sm btn-outline-info me-1" title="View Details" onclick="viewInvoiceDetail(${inv.id})"><i class="fa-solid fa-eye"></i></button>
                <button class="btn btn-sm btn-outline-warning me-1" title="Edit Bill" onclick="editInvoice(${inv.id})"><i class="fa-solid fa-pen-to-square"></i></button>
                <button class="btn btn-sm btn-outline-primary me-1" title="Download / Print PDF" onclick="promptPdfType(${inv.id})"><i class="fa-solid fa-file-pdf me-1"></i> PDF</button>
                ${inv.status === 'pending_approval' && state.currentRole === 'admin' ? `<button class="btn btn-sm btn-success me-1" title="Approve Order" onclick="approveOrder(${inv.id})"><i class="fa-solid fa-check me-1"></i> Approve</button>` : ''}
                ${inv.status !== 'pending_approval' && inv.balance > 0 ? `<button class="btn btn-sm btn-outline-success me-1" title="Record Payment" onclick="openRecordPaymentModal(${inv.id}, '${inv.invoice_number}', ${inv.balance})"><i class="fa-solid fa-hand-holding-dollar"></i></button>` : ''}
                ${state.currentRole === 'admin' || state.currentRole === 'billing' ? `<button class="btn btn-sm btn-outline-danger" title="Delete Invoice" onclick="deleteInvoice(${inv.id}, '${inv.invoice_number}')"><i class="fa-solid fa-trash"></i></button>` : ''}
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function deleteInvoice(invId, invNumber) {
    if (!confirm(`Move Invoice "${invNumber}" to Recycle Bin?`)) return;
    try {
        const res = await fetch(`/api/invoices/${invId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            alert(data.message);
            await loadAllData();
        } else {
            alert(data.error);
        }
    } catch (e) {
        alert("Failed to move invoice to recycle bin.");
    }
}

async function loadRecycleBin() {
    try {
        const res = await fetch('/api/recycle-bin/invoices');
        const data = await res.json();
        if (!data.success) return;

        const tbody = document.getElementById('recycle-bin-tbody');
        tbody.innerHTML = '';

        if (data.invoices.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">Recycle bin is empty.</td></tr>';
            return;
        }

        data.invoices.forEach(inv => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="fw-bold text-danger">${inv.invoice_number}</td>
                <td>${inv.invoice_date.split('T')[0]}</td>
                <td class="fw-medium">${inv.customer_name}</td>
                <td class="fw-bold">₹${inv.grand_total.toFixed(2)}</td>
                <td class="text-success">₹${inv.amount_paid.toFixed(2)}</td>
                <td class="text-danger fw-bold">₹${inv.balance.toFixed(2)}</td>
                <td>
                    <button class="btn btn-sm btn-outline-success me-1" title="Restore Invoice" onclick="restoreInvoice(${inv.id})"><i class="fa-solid fa-rotate-left me-1"></i> Restore</button>
                    ${state.currentRole === 'admin' ? `<button class="btn btn-sm btn-danger" title="Permanently Delete" onclick="permanentDeleteInvoice(${inv.id}, '${inv.invoice_number}')"><i class="fa-solid fa-dumpster-fire me-1"></i> Delete Permanently</button>` : ''}
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Error loading recycle bin:", err);
    }
}

async function restoreInvoice(invId) {
    try {
        const res = await fetch(`/api/invoices/${invId}/restore`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            alert(data.message);
            await loadAllData();
            await loadRecycleBin();
        } else {
            alert(data.error);
        }
    } catch (e) {
        alert("Failed to restore invoice.");
    }
}

async function permanentDeleteInvoice(invId, invNumber) {
    if (!confirm(`PERMANENT ACTION: Are you sure you want to PERMANENTLY delete Invoice "${invNumber}"? This cannot be undone.`)) return;
    try {
        const res = await fetch(`/api/invoices/${invId}?permanent=true`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            alert(data.message);
            await loadRecycleBin();
        } else {
            alert(data.error);
        }
    } catch (e) {
        alert("Failed to permanently delete invoice.");
    }
}

async function approveOrder(invId) {
    let manualNum = prompt("Enter the manual Invoice Book Number matching your physical invoice book:");
    if (manualNum === null) return;
    manualNum = manualNum.trim();
    if (!manualNum) {
        alert("Manual Invoice Book Number is required to convert/approve this order into an official invoice!");
        return;
    }
    try {
        const res = await fetch(`/api/invoices/${invId}/approve`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ invoice_number: manualNum })
        });
        const data = await res.json();
        if (data.success) {
            alert(data.message);
            await loadAllData();
        } else {
            alert(data.error);
        }
    } catch (e) {
        alert("Failed to approve order.");
    }
}

function filterInvoices() {
    const query = document.getElementById('invoice-search-input').value.toLowerCase();
    const filtered = state.invoices.filter(i => 
        i.invoice_number.toLowerCase().includes(query) || 
        i.customer_name.toLowerCase().includes(query)
    );
    renderInvoicesList(filtered);
}

// 5. NEW BILL CREATION LOGIC
function onCustomerSelectChange() {
    const custId = parseInt(document.getElementById('bill-customer-select').value);
    const box = document.getElementById('customer-info-box');
    
    if (!custId) {
        box.classList.add('d-none');
        return;
    }

    const customer = state.shopsList.find(c => c.id === custId);
    if (customer) {
        document.getElementById('cbox-name').innerText = customer.shop_name;
        document.getElementById('cbox-details').innerText = `Phone: ${customer.phone || 'N/A'} | GSTIN: ${customer.gstin || 'N/A'}`;
        document.getElementById('cbox-balance').innerText = `₹${(customer.current_balance || 0).toFixed(2)}`;
        box.classList.remove('d-none');

        const mapsInput = document.getElementById('bill-maps-link');
        if (mapsInput && customer.maps_location_link) {
            mapsInput.value = customer.maps_location_link;
        }
    }
}

function addBillLine() {
    const tbody = document.getElementById('bill-items-tbody');
    const rowId = Date.now() + Math.random();

    const tr = document.createElement('tr');
    tr.id = `bill-row-${rowId}`;
    tr.innerHTML = `
        <td>
            <select class="form-select bill-prod-select" onchange="onBillProductChange('${rowId}')">
                <option value="">-- Select Product --</option>
                ${state.products.map(p => `<option value="${p.id}">${p.brand} ${p.product_name} (MRP: ₹${p.mrp})</option>`).join('')}
            </select>
        </td>
        <td>
            <input type="number" class="form-control bill-qty" value="1" min="1" step="1" oninput="recalculateBillTotals()">
        </td>
        <td>
            <input type="number" class="form-control bill-price" value="0" step="0.01" oninput="recalculateBillTotals()">
        </td>
        <td class="fw-bold align-middle bill-line-total">
            ₹0.00
        </td>
        <td class="text-end align-middle">
            <button class="btn btn-sm btn-outline-danger" onclick="removeBillLine('${rowId}')"><i class="fa-solid fa-trash"></i></button>
        </td>
    `;
    tbody.appendChild(tr);
}

function updateBillItemDropdowns() {
    document.querySelectorAll('.bill-prod-select').forEach(select => {
        const val = select.value;
        select.innerHTML = '<option value="">-- Select Product --</option>' + 
            state.products.map(p => `<option value="${p.id}">${p.brand} ${p.product_name} (MRP: ₹${p.mrp})</option>`).join('');
        select.value = val;
    });
}

async function onBillProductChange(rowId) {
    const row = document.getElementById(`bill-row-${rowId}`);
    const prodId = parseInt(row.querySelector('.bill-prod-select').value);
    const custId = parseInt(document.getElementById('bill-customer-select').value);
    
    if (!prodId) return;

    const prod = state.products.find(p => p.id === prodId);
    let priceToSet = prod ? prod.mrp : 0;

    // Check last price memory if customer is selected
    if (custId && prodId) {
        try {
            const res = await fetch(`/api/customer-last-price?customer_id=${custId}&product_id=${prodId}`);
            const data = await res.json();
            if (data.success && data.last_price !== null) {
                priceToSet = data.last_price;
            }
        } catch (e) {
            console.error("Price memory lookup error", e);
        }
    }

    row.querySelector('.bill-price').value = priceToSet;
    recalculateBillTotals();
}

function removeBillLine(rowId) {
    const row = document.getElementById(`bill-row-${rowId}`);
    if (row) row.remove();
    recalculateBillTotals();
}

function recalculateBillTotals() {
    let totalInclusive = 0;
    let totalGstExtracted = 0;

    document.querySelectorAll('#bill-items-tbody tr').forEach(row => {
        const prodSelect = row.querySelector('.bill-prod-select');
        if (!prodSelect) return;
        const prodId = parseInt(prodSelect.value) || 0;
        const qty = parseFloat(row.querySelector('.bill-qty')?.value) || 0;
        const price = parseFloat(row.querySelector('.bill-price')?.value) || 0;

        const prod = state.products.find(p => p.id === prodId);
        const gstRate = prod ? parseFloat(prod.gst_rate) : 18.0;

        // Line total is GST Inclusive
        const lineTotalInclusive = qty * price;
        const lineTotalElem = row.querySelector('.bill-line-total');
        if (lineTotalElem) lineTotalElem.innerText = `₹${lineTotalInclusive.toFixed(2)}`;

        if (prodId && qty > 0) {
            const gstFactor = 1.0 + (gstRate / 100.0);
            const taxableBase = lineTotalInclusive / gstFactor;
            const gstAmount = lineTotalInclusive - taxableBase;

            totalInclusive += lineTotalInclusive;
            totalGstExtracted += gstAmount;
        }
    });

    const discount = parseFloat(document.getElementById('bill-discount')?.value) || 0;
    const hasTransport = document.getElementById('bill-has-transport-checkbox')?.checked || false;
    const transport = hasTransport ? (parseFloat(document.getElementById('bill-transport')?.value) || 0) : 0;
    const hasServiceCharge = document.getElementById('bill-has-service-charge-checkbox')?.checked || false;
    const serviceCharge = hasServiceCharge ? (parseFloat(document.getElementById('bill-service-charge')?.value) || 0) : 0;
    const baseSubtotal = totalInclusive - totalGstExtracted;
    const grandTotal = Math.max(0, totalInclusive - discount + transport + serviceCharge);

    const subtotalElem = document.getElementById('bill-subtotal');
    const gstElem = document.getElementById('bill-gst');
    const grandElem = document.getElementById('bill-grand-total');

    if (subtotalElem) subtotalElem.innerText = `₹${baseSubtotal.toFixed(2)}`;
    if (gstElem) gstElem.innerText = `₹${totalGstExtracted.toFixed(2)}`;
    if (grandElem) grandElem.innerText = `₹${grandTotal.toFixed(2)}`;
}

function toggleTransportInput() {
    const hasTransport = document.getElementById('bill-has-transport-checkbox')?.checked || false;
    const container = document.getElementById('transport-input-container');
    const input = document.getElementById('bill-transport');
    if (hasTransport) {
        if (container) container.classList.remove('d-none');
        if (input) input.focus();
    } else {
        if (container) container.classList.add('d-none');
        if (input) input.value = '0';
    }
    recalculateBillTotals();
}

function toggleServiceChargeInput() {
    const hasServiceCharge = document.getElementById('bill-has-service-charge-checkbox')?.checked || false;
    const container = document.getElementById('service-charge-input-container');
    const input = document.getElementById('bill-service-charge');
    if (hasServiceCharge) {
        if (container) container.classList.remove('d-none');
        if (input) input.focus();
    } else {
        if (container) container.classList.add('d-none');
        if (input) input.value = '0';
    }
    recalculateBillTotals();
}

let currentPendingInvoiceData = null;

async function submitInvoice() {
    const custSelect = document.getElementById('bill-customer-select');
    const customer_id = custSelect ? parseInt(custSelect.value) : 0;
    if (!customer_id) {
        alert("Please select a customer/shop!");
        return;
    }

    const lines = [];
    let hasInvalidLine = false;

    document.querySelectorAll('#bill-items-tbody tr').forEach(row => {
        const prodSelect = row.querySelector('.bill-prod-select');
        const qtyInput = row.querySelector('.bill-qty');
        const priceInput = row.querySelector('.bill-price');

        if (!prodSelect || !qtyInput || !priceInput) return;

        const prodId = parseInt(prodSelect.value) || 0;
        const qty = parseFloat(qtyInput.value) || 0;
        const price = parseFloat(priceInput.value) || 0;

        if (prodId && qty > 0) {
            lines.push({
                product_id: prodId,
                quantity_bags: qty,
                selling_price: price
            });
        } else if (prodId || qty > 0) {
            hasInvalidLine = true;
        }
    });

    if (hasInvalidLine || lines.length === 0) {
        alert("Please select a product and enter a valid quantity (> 0) for each line item!");
        return;
    }

    const discount = parseFloat(document.getElementById('bill-discount')?.value) || 0;
    const hasTransport = document.getElementById('bill-has-transport-checkbox')?.checked || false;
    const transport = hasTransport ? (parseFloat(document.getElementById('bill-transport')?.value) || 0) : 0;
    const hasServiceCharge = document.getElementById('bill-has-service-charge-checkbox')?.checked || false;
    const serviceCharge = hasServiceCharge ? (parseFloat(document.getElementById('bill-service-charge')?.value) || 0) : 0;
    const paymentAmount = parseFloat(document.getElementById('bill-payment-amount')?.value) || 0;
    const paymentMethod = document.getElementById('bill-payment-method')?.value || 'cash';
    const notes = document.getElementById('bill-notes')?.value || "";
    const mapsLocationLink = document.getElementById('bill-maps-link')?.value?.trim() || "";
    const manualInvoiceNumber = document.getElementById('bill-invoice-number')?.value?.trim() || "";
    const isSealed = document.getElementById('bill-is-sealed-checkbox')?.checked || false;

    const isOrderRequest = state.invoiceFormMode === 'order_request';

    if (!isOrderRequest && !manualInvoiceNumber) {
        alert("Invoice Book Number is required! Please enter the manual Invoice Number matching your physical invoice book.");
        document.getElementById('bill-invoice-number')?.focus();
        return;
    }

    if (isOrderRequest) {
        const isEdit = !!state.editingInvoiceId;
        const url = isEdit ? `/api/invoices/${state.editingInvoiceId}` : '/api/invoices';
        const method = isEdit ? 'PUT' : 'POST';

        try {
            const response = await fetch(url, {
                method: method,
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    customer_id: customer_id,
                    invoice_number: manualInvoiceNumber,
                    lines: lines,
                    discount: discount,
                    transport: transport,
                    service_charge: serviceCharge,
                    initial_payment: 0,
                    payment_method: 'cash',
                    notes: notes,
                    maps_location_link: mapsLocationLink,
                    is_order_request: true,
                    is_sealed: false
                })
            });
            const resData = await response.json();
            if (resData.success) {
                alert(resData.message || "Sales Order Request saved successfully!");
                resetBillForm();
                await loadAllData();
                switchTab('new-orders');
            } else {
                alert(`Error submitting order request: ${resData.error}`);
            }
        } catch (err) {
            console.error("Submit order error:", err);
            alert("Failed to submit order request.");
        }
        return;
    }

    currentPendingInvoiceData = {
        customer_id: customer_id,
        invoice_number: manualInvoiceNumber,
        lines: lines,
        discount: discount,
        transport: transport,
        service_charge: serviceCharge,
        initial_payment: paymentAmount,
        payment_method: paymentMethod,
        notes: notes,
        maps_location_link: mapsLocationLink,
        is_sealed: isSealed
    };

    openInvoicePreviewModal();
}

function openInvoicePreviewModal() {
    if (!currentPendingInvoiceData) return;

    const data = currentPendingInvoiceData;
    const customer = state.customers.find(c => c.id === data.customer_id);
    const modalBody = document.getElementById('invoice-preview-modal-body');

    let subtotal = 0;
    let itemsRowsHtml = '';

    data.lines.forEach((line, idx) => {
        const prod = state.products.find(p => p.id === line.product_id);
        const prodName = prod ? prod.product_name : `Product #${line.product_id}`;
        const lineTotal = line.quantity_bags * line.selling_price;
        subtotal += lineTotal;
        itemsRowsHtml += `
            <tr>
                <td>${idx + 1}</td>
                <td class="fw-bold text-light">${prodName}</td>
                <td>${line.quantity_bags}</td>
                <td>₹${line.selling_price.toFixed(2)}</td>
                <td class="fw-bold text-end text-success">₹${lineTotal.toFixed(2)}</td>
            </tr>
        `;
    });

    const grandTotal = subtotal - data.discount + data.transport;
    const balanceDue = grandTotal - data.initial_payment;

    modalBody.innerHTML = `
        <div class="row g-3 mb-3">
            <div class="col-md-6">
                <label class="form-label text-secondary small mb-1 fw-bold">CUSTOMER / SHOP</label>
                <div class="fw-bold fs-5 text-warning">${customer ? customer.shop_name : 'Selected Customer'}</div>
                <div class="small text-muted">${customer ? (customer.phone || 'No phone') : ''}</div>
            </div>
            <div class="col-md-6">
                <label class="form-label text-secondary small mb-1 fw-bold">MANUAL / CUSTOM INVOICE NUMBER</label>
                <input type="text" id="preview-invoice-number" class="form-control bg-secondary text-light fw-bold" value="${data.invoice_number || ''}" placeholder="Leave blank to auto-generate">
            </div>
        </div>

        <div class="table-responsive mb-3">
            <table class="table table-dark table-striped align-middle mb-0">
                <thead>
                    <tr class="text-secondary small">
                        <th>#</th>
                        <th>Product</th>
                        <th>Qty</th>
                        <th>Rate (₹)</th>
                        <th class="text-end">Line Total (₹)</th>
                    </tr>
                </thead>
                <tbody>
                    ${itemsRowsHtml}
                </tbody>
            </table>
        </div>

        <div class="row justify-content-end">
            <div class="col-md-6">
                <div class="p-3 rounded border shadow-sm" style="background-color: #0f172a; border-color: #334155 !important;">
                    <div class="d-flex justify-content-between mb-1">
                        <span class="text-light-50">Subtotal:</span>
                        <span class="fw-bold text-light">₹${subtotal.toFixed(2)}</span>
                    </div>
                    ${data.discount > 0 ? `
                    <div class="d-flex justify-content-between mb-1 text-danger">
                        <span>Discount:</span>
                        <span>- ₹${data.discount.toFixed(2)}</span>
                    </div>
                    ` : ''}
                    ${data.transport > 0 ? `
                    <div class="d-flex justify-content-between mb-1 text-info">
                        <span>Transport:</span>
                        <span>+ ₹${data.transport.toFixed(2)}</span>
                    </div>
                    ` : ''}
                    ${data.service_charge > 0 ? `
                    <div class="d-flex justify-content-between mb-1 text-warning">
                        <span>Service Charge:</span>
                        <span>+ ₹${data.service_charge.toFixed(2)}</span>
                    </div>
                    ` : ''}
                    <hr class="my-2" style="border-color: #334155;">
                    <div class="d-flex justify-content-between fs-5 fw-bold mb-2">
                        <span class="text-light">Grand Total:</span>
                        <span style="color: #34d399;">₹${grandTotal.toFixed(2)}</span>
                    </div>
                    <div class="d-flex justify-content-between text-light small mb-1">
                        <span class="text-light-50">Initial Payment (${data.payment_method.toUpperCase()}):</span>
                        <span class="fw-bold text-light">₹${data.initial_payment.toFixed(2)}</span>
                    </div>
                    <div class="d-flex justify-content-between fw-bold small mt-1" style="color: #fbbf24;">
                        <span>Balance Remaining:</span>
                        <span>₹${balanceDue.toFixed(2)}</span>
                    </div>
                </div>
            </div>
        </div>
    `;

    const modalEl = document.getElementById('invoicePreviewModal');
    const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
    modal.show();
}

async function executeSaveInvoice(asDraft = false) {
    if (!currentPendingInvoiceData) return;

    const previewNumInput = document.getElementById('preview-invoice-number');
    if (previewNumInput) {
        currentPendingInvoiceData.invoice_number = previewNumInput.value.trim();
    }

    const isApproving = state.isApprovingOrder;
    const isDraft = !isApproving && asDraft;

    if (!isDraft && (!currentPendingInvoiceData.invoice_number || !currentPendingInvoiceData.invoice_number.trim())) {
        alert("Invoice Book Number is required! Please enter the manual Invoice Number matching your physical invoice book.");
        if (previewNumInput) previewNumInput.focus();
        return;
    }
    const payload = {
        ...currentPendingInvoiceData,
        is_order_request: !isApproving && asDraft
    };

    const isEdit = !!state.editingInvoiceId;
    const url = isEdit ? `/api/invoices/${state.editingInvoiceId}` : '/api/invoices';
    const method = isEdit ? 'PUT' : 'POST';

    try {
        const response = await fetch(url, {
            method: method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });

        const resData = await response.json();
        if (resData.success) {
            let finalInvId = resData.invoice_id || state.editingInvoiceId;
            let finalInvNum = resData.invoice_number || payload.invoice_number;

            if (isApproving && state.editingInvoiceId) {
                // Call approve endpoint to convert status from PENDING_APPROVAL to COMPLETED
                const appRes = await fetch(`/api/invoices/${state.editingInvoiceId}/approve`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ invoice_number: payload.invoice_number })
                });
                const appData = await appRes.json();
                if (!appData.success) {
                    alert(`Error approving order: ${appData.error}`);
                    return;
                }
                if (appData.invoice_id) finalInvId = appData.invoice_id;
            }

            const modalEl = document.getElementById('invoicePreviewModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();

            state.editingInvoiceId = null;
            state.isApprovingOrder = false;

            if (payload.is_order_request) {
                alert(resData.message || "Order / Draft Request saved successfully!");
                resetBillForm();
                await loadAllData();
                switchTab('new-orders');
            } else {
                alert(resData.message || "Invoice saved successfully!");
                resetBillForm();
                await loadAllData();
                switchTab('invoices');
            }
            currentPendingInvoiceData = null;
        } else {
            alert(`Error saving invoice: ${resData.error}`);
        }
    } catch (err) {
        console.error("Save invoice error:", err);
        alert("Failed to save invoice.");
    }
}

function resetBillForm() {
    state.editingInvoiceId = null;
    const tbody = document.getElementById('bill-items-tbody');
    if (tbody) {
        tbody.innerHTML = '';
        addBillLine();
    }
    if (document.getElementById('bill-customer-select')) {
        document.getElementById('bill-customer-select').value = '';
        if (billCustomerTomSelect) billCustomerTomSelect.clear();
    }
    if (document.getElementById('bill-invoice-number')) document.getElementById('bill-invoice-number').value = '';
    if (document.getElementById('customer-info-box')) document.getElementById('customer-info-box').classList.add('d-none');
    if (document.getElementById('bill-discount')) document.getElementById('bill-discount').value = '0';
    if (document.getElementById('bill-has-transport-checkbox')) {
        document.getElementById('bill-has-transport-checkbox').checked = false;
        if (typeof toggleTransportInput === 'function') toggleTransportInput();
    }
    if (document.getElementById('bill-has-service-charge-checkbox')) {
        document.getElementById('bill-has-service-charge-checkbox').checked = false;
        if (typeof toggleServiceChargeInput === 'function') toggleServiceChargeInput();
    }
    if (document.getElementById('bill-payment-amount')) document.getElementById('bill-payment-amount').value = '0';
    if (document.getElementById('bill-maps-link')) document.getElementById('bill-maps-link').value = '';
    if (document.getElementById('bill-notes')) document.getElementById('bill-notes').value = '';
}

async function editInvoice(invoiceId, isApproving = false) {
    try {
        const res = await fetch(`/api/invoices/${invoiceId}`);
        const data = await res.json();
        if (!data.success) {
            alert(data.error || "Failed to fetch invoice details.");
            return;
        }

        const inv = data.invoice;
        state.editingInvoiceId = inv.id;
        state.isApprovingOrder = isApproving;

        // Open billing tab
        switchTab('new-bill');

        // Set Title & Subtitle & Submit button
        const newBillTitle = document.getElementById('new-bill-title');
        const newBillSubtitle = document.getElementById('new-bill-subtitle');
        const submitBtn = document.getElementById('btn-submit-bill');

        if (isApproving) {
            setInvoiceFormMode('invoice');
            if (newBillTitle) newBillTitle.innerText = `Approve & Issue Invoice for Order Request #${inv.id}`;
            if (newBillSubtitle) newBillSubtitle.innerText = "Verify order details, enter manual invoice number & payment details to generate official bill";
            if (submitBtn) {
                submitBtn.className = "btn btn-success btn-lg w-100 py-3 fw-bold";
                submitBtn.innerHTML = '<i class="fa-solid fa-check-double me-2"></i> Approve & Issue Official Invoice';
            }
        } else if (inv.status === 'pending_approval') {
            setInvoiceFormMode('order_request');
            if (newBillTitle) newBillTitle.innerText = `Edit Order Request #${inv.id}`;
            if (newBillSubtitle) newBillSubtitle.innerText = "Modify items, quantities, or site location link for this pending order request";
            if (submitBtn) {
                submitBtn.className = "btn btn-warning btn-lg w-100 py-3 fw-bold";
                submitBtn.innerHTML = '<i class="fa-solid fa-floppy-disk me-2"></i> Update Order Request';
            }
        } else {
            setInvoiceFormMode('invoice');
            if (newBillTitle) newBillTitle.innerText = `Edit Invoice #${inv.invoice_number}`;
            if (newBillSubtitle) newBillSubtitle.innerText = "Modify customer, items, prices or discount for this bill";
            if (submitBtn) {
                submitBtn.className = "btn btn-success btn-lg w-100 py-3 fw-bold";
                submitBtn.innerHTML = '<i class="fa-solid fa-floppy-disk me-2"></i> Update Invoice';
            }
        }

        // Set customer
        if (!state.customers || state.customers.length === 0) {
            await loadCustomers();
        }
        let targetCustId = inv.customer_id;
        if (!targetCustId && inv.customer_name) {
            const matchedCust = state.customers.find(c => c.name === inv.customer_name);
            if (matchedCust) targetCustId = matchedCust.id;
        }
        const custSelect = document.getElementById('bill-customer-select');
        if (custSelect && targetCustId) {
            custSelect.value = targetCustId;
            if (billCustomerTomSelect) {
                billCustomerTomSelect.setValue(targetCustId);
            }
            onCustomerSelectChange();
        }

        // Set manual invoice number
        const invNumInput = document.getElementById('bill-invoice-number');
        if (invNumInput) {
            invNumInput.value = inv.invoice_number;
        }

        // Set discount, transport, service charge, notes, maps link
        if (document.getElementById('bill-discount')) document.getElementById('bill-discount').value = inv.discount || 0;
        if (document.getElementById('bill-notes')) document.getElementById('bill-notes').value = inv.notes || '';
        if (document.getElementById('bill-maps-link')) document.getElementById('bill-maps-link').value = inv.maps_location_link || '';

        const chkTrans = document.getElementById('bill-has-transport-checkbox');
        if (chkTrans) {
            chkTrans.checked = (inv.transport || 0) > 0;
            if (typeof toggleTransportInput === 'function') toggleTransportInput();
            if (document.getElementById('bill-transport')) document.getElementById('bill-transport').value = inv.transport || 0;
        }

        const chkServ = document.getElementById('bill-has-service-charge-checkbox');
        if (chkServ) {
            chkServ.checked = (inv.service_charge || 0) > 0;
            if (typeof toggleServiceChargeInput === 'function') toggleServiceChargeInput();
            if (document.getElementById('bill-service-charge')) document.getElementById('bill-service-charge').value = inv.service_charge || 0;
        }

        // Populate items
        if (!state.products || state.products.length === 0) {
            await loadProducts();
        }

        const tbody = document.getElementById('bill-items-tbody');
        if (tbody) {
            tbody.innerHTML = '';
            if (inv.items && inv.items.length > 0) {
                inv.items.forEach(item => {
                    let targetProdId = item.product_id;
                    if (!targetProdId) {
                        const matched = state.products.find(p => p.product_name === item.product_name && p.brand === item.brand);
                        if (matched) targetProdId = matched.id;
                    }

                    const rowId = Date.now() + Math.random();
                    const tr = document.createElement('tr');
                    tr.id = `bill-row-${rowId}`;
                    tr.innerHTML = `
                        <td>
                            <select class="form-select bill-prod-select" onchange="onBillProductChange('${rowId}')">
                                <option value="">-- Choose Product --</option>
                                ${state.products.map(p => `<option value="${p.id}" ${p.id === targetProdId ? 'selected' : ''}>${p.brand} - ${p.product_name} (${p.variant || 'Standard'}) [Stock: ${p.stock_bags} ${p.unit}]</option>`).join('')}
                            </select>
                        </td>
                        <td>
                            <input type="number" class="form-control bill-qty" value="${item.quantity}" min="1" step="1" oninput="recalculateBillTotals()">
                        </td>
                        <td>
                            <input type="number" class="form-control bill-price" value="${item.selling_price}" min="0" step="0.01" oninput="recalculateBillTotals()">
                        </td>
                        <td class="fw-bold align-middle bill-line-total text-success">
                            ₹${item.line_total.toFixed(2)}
                        </td>
                        <td class="text-end align-middle">
                            <button class="btn btn-sm btn-outline-danger" onclick="removeBillLine('${rowId}')"><i class="fa-solid fa-trash"></i></button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            } else {
                addBillLine();
            }
        }

        recalculateBillTotals();
    } catch (err) {
        console.error("Error editing invoice:", err);
        alert("Failed to load invoice for editing.");
    }
}

// 4B. CONSTRUCTION SQFT BILLING FUNCTIONS
function initSqftBillingTab() {
    populateSqftCustomers();
    const tbody = document.getElementById('sqft-items-tbody');
    if (tbody && tbody.children.length === 0) {
        addSqftBillLine();
    }
}

let sqftCustomerTomSelect = null;

async function populateSqftCustomers() {
    const select = document.getElementById('sqft-customer-select');
    if (!select) return;

    if (sqftCustomerTomSelect) {
        sqftCustomerTomSelect.destroy();
        sqftCustomerTomSelect = null;
    }

    if (!state.clientsList || state.clientsList.length === 0) {
        try {
            const res = await fetch('/api/customers?type=client');
            const data = await res.json();
            if (data.success) {
                state.clientsList = data.customers;
            }
        } catch (e) {
            console.error("Error fetching clients for dropdown:", e);
        }
    }
    const currentVal = select.value;
    select.innerHTML = '<option value="">-- Choose Construction Client --</option>' + 
        (state.clientsList || []).map(c => {
            const gstinOrPhone = c.gstin ? `GSTIN: ${c.gstin}` : (c.phone ? `Ph: ${c.phone}` : 'Client');
            return `<option value="${c.id}">${c.shop_name} (${gstinOrPhone})</option>`;
        }).join('');
    select.value = currentVal;

    if (typeof TomSelect !== 'undefined') {
        sqftCustomerTomSelect = new TomSelect('#sqft-customer-select', {
            create: false,
            placeholder: "🔍 Type Client or Project Name to search...",
            onChange: function() {
                onSqftCustomerSelectChange();
            }
        });
    }
}

function onSqftCustomerSelectChange() {
    const custId = parseInt(document.getElementById('sqft-customer-select')?.value);
    if (custId && state.clientsList) {
        const client = state.clientsList.find(c => c.id === custId);
        const mapsInput = document.getElementById('sqft-maps-location');
        if (mapsInput && client && client.maps_location_link) {
            mapsInput.value = client.maps_location_link;
        }
    }
    recalculateSqftBillTotals();
}

function toggleSqftTransportInput() {
    const chk = document.getElementById('sqft-has-transport-checkbox');
    const container = document.getElementById('sqft-transport-input-container');
    if (chk && container) {
        if (chk.checked) {
            container.classList.remove('d-none');
        } else {
            container.classList.add('d-none');
            const transportInput = document.getElementById('sqft-transport');
            if (transportInput) transportInput.value = '0';
        }
    }
    recalculateSqftBillTotals();
}

function addSqftBillLine() {
    const tbody = document.getElementById('sqft-items-tbody');
    if (!tbody) return;
    const rowId = Date.now() + Math.random();

    const tr = document.createElement('tr');
    tr.id = `sqft-row-${rowId}`;
    tr.innerHTML = `
        <td>
            <input type="text" class="form-control sqft-desc" placeholder="e.g. Civil Construction Work / Plastering / Tile Work" required>
        </td>
        <td>
            <input type="number" class="form-control sqft-area" value="100" min="0.01" step="0.01" oninput="recalculateSqftBillTotals()">
        </td>
        <td>
            <input type="number" class="form-control sqft-rate" value="0" min="0" step="0.01" oninput="recalculateSqftBillTotals()">
        </td>
        <td class="fw-bold align-middle sqft-line-total text-success">
            ₹0.00
        </td>
        <td class="text-end align-middle">
            <button class="btn btn-sm btn-outline-danger" onclick="removeSqftBillLine('${rowId}')"><i class="fa-solid fa-trash"></i></button>
        </td>
    `;
    tbody.appendChild(tr);
    recalculateSqftBillTotals();
}

function removeSqftBillLine(rowId) {
    const tr = document.getElementById(`sqft-row-${rowId}`);
    if (tr) tr.remove();
    recalculateSqftBillTotals();
}

function recalculateSqftBillTotals() {
    let grossTotal = 0;
    document.querySelectorAll('#sqft-items-tbody tr').forEach(row => {
        const areaInput = row.querySelector('.sqft-area');
        const rateInput = row.querySelector('.sqft-rate');
        const lineTotalCell = row.querySelector('.sqft-line-total');

        const area = parseFloat(areaInput?.value) || 0;
        const rate = parseFloat(rateInput?.value) || 0;
        const lineTotal = area * rate;

        if (lineTotalCell) lineTotalCell.innerText = `₹${lineTotal.toFixed(2)}`;
        grossTotal += lineTotal;
    });

    const includeGst = document.getElementById('sqft-include-gst-checkbox')?.checked || false;
    const gstBreakdownRow = document.getElementById('sqft-gst-breakdown-row');
    
    let subtotal = grossTotal;
    let totalGst = 0;

    if (includeGst) {
        // Total remains fixed; reduce taxable base price so Base + 18% GST = grossTotal
        subtotal = grossTotal / 1.18;
        totalGst = grossTotal - subtotal;
        const cgst = totalGst / 2;
        const sgst = totalGst / 2;
        if (document.getElementById('sqft-sgst-val')) document.getElementById('sqft-sgst-val').innerText = `₹${sgst.toFixed(2)}`;
        if (document.getElementById('sqft-cgst-val')) document.getElementById('sqft-cgst-val').innerText = `₹${cgst.toFixed(2)}`;
        if (gstBreakdownRow) gstBreakdownRow.classList.remove('d-none');
    } else {
        if (gstBreakdownRow) gstBreakdownRow.classList.add('d-none');
    }

    const subtotalEl = document.getElementById('sqft-subtotal');
    if (subtotalEl) subtotalEl.innerText = `₹${subtotal.toFixed(2)}`;

    const hasTransport = document.getElementById('sqft-has-transport-checkbox')?.checked || false;
    const transport = hasTransport ? (parseFloat(document.getElementById('sqft-transport')?.value) || 0) : 0;
    const grandTotal = grossTotal + transport;

    const grandTotalEl = document.getElementById('sqft-grand-total');
    if (grandTotalEl) grandTotalEl.innerText = `₹${grandTotal.toFixed(2)}`;
}

async function submitSqftInvoice(asDraft = false) {
    const customerId = parseInt(document.getElementById('sqft-customer-select')?.value) || 0;
    if (!customerId) {
        alert("Please select a Client/Shop to issue the SqFt Construction Bill!");
        return;
    }

    const includeGst = document.getElementById('sqft-include-gst-checkbox')?.checked || false;

    const lines = [];
    let hasInvalidLine = false;

    document.querySelectorAll('#sqft-items-tbody tr').forEach(row => {
        const descInput = row.querySelector('.sqft-desc');
        const areaInput = row.querySelector('.sqft-area');
        const rateInput = row.querySelector('.sqft-rate');

        const desc = descInput?.value?.trim() || "";
        const area = parseFloat(areaInput?.value) || 0;
        const rate = parseFloat(rateInput?.value) || 0;

        if (desc && area > 0 && rate >= 0) {
            lines.push({
                product_id: 0,
                desc: desc,
                quantity_bags: area,
                selling_price: rate
            });
        } else if (desc || area > 0 || rate > 0) {
            hasInvalidLine = true;
        }
    });

    if (hasInvalidLine || lines.length === 0) {
        alert("Please enter work description, SqFt area (> 0), and rate for each work scope line!");
        return;
    }

    const hasTransport = document.getElementById('sqft-has-transport-checkbox')?.checked || false;
    const transport = hasTransport ? (parseFloat(document.getElementById('sqft-transport')?.value) || 0) : 0;
    const paymentAmount = parseFloat(document.getElementById('sqft-payment-amount')?.value) || 0;
    const paymentMethod = document.getElementById('sqft-payment-method')?.value || 'cash';
    const notes = document.getElementById('sqft-bill-notes')?.value || "";
    const mapsLocationLink = document.getElementById('sqft-maps-location')?.value?.trim() || "";
    const isOrderRequest = asDraft || state.invoiceFormMode === 'order_request';

    if (!isOrderRequest && !manualInvoiceNumber) {
        alert("Invoice Book Number is required! Please enter the manual Invoice Number matching your physical invoice book.");
        document.getElementById('sqft-invoice-number')?.focus();
        return;
    }

    try {
        const response = await fetch('/api/invoices', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                customer_id: customerId,
                invoice_number: manualInvoiceNumber,
                lines: lines,
                discount: 0,
                transport: transport,
                initial_payment: paymentAmount,
                payment_method: paymentMethod,
                notes: notes,
                maps_location_link: mapsLocationLink,
                is_order_request: isOrderRequest,
                is_sealed: false,
                billing_type: 'construction_sqft',
                include_gst: includeGst
            })
        });

        const resData = await response.json();
        if (resData.success) {
            if (isOrderRequest) {
                alert(resData.message || "Sales Order Request submitted for billing approval!");
                document.getElementById('sqft-items-tbody').innerHTML = '';
                addSqftBillLine();
                document.getElementById('sqft-customer-select').value = '';
                if (document.getElementById('sqft-invoice-number')) document.getElementById('sqft-invoice-number').value = '';
                if (document.getElementById('sqft-has-transport-checkbox')) {
                    document.getElementById('sqft-has-transport-checkbox').checked = false;
                    toggleSqftTransportInput();
                }
                document.getElementById('sqft-payment-amount').value = '0';
                if (document.getElementById('sqft-maps-location')) document.getElementById('sqft-maps-location').value = '';
                if (document.getElementById('sqft-bill-notes')) document.getElementById('sqft-bill-notes').value = '';

                await loadAllData();
                switchTab('new-orders');
                return;
            }

            alert(resData.message || `Construction Bill ${resData.invoice_number} issued successfully!`);
            // Reset SqFt Form
            document.getElementById('sqft-items-tbody').innerHTML = '';
            addSqftBillLine();
            document.getElementById('sqft-customer-select').value = '';
            if (document.getElementById('sqft-invoice-number')) document.getElementById('sqft-invoice-number').value = '';
            if (document.getElementById('sqft-has-transport-checkbox')) {
                document.getElementById('sqft-has-transport-checkbox').checked = false;
                toggleSqftTransportInput();
            }
            document.getElementById('sqft-payment-amount').value = '0';
            if (document.getElementById('sqft-maps-location')) document.getElementById('sqft-maps-location').value = '';
            if (document.getElementById('sqft-bill-notes')) document.getElementById('sqft-bill-notes').value = '';

            await loadAllData();
            switchTab('invoices');
        } else {
            alert(`Error creating SqFt bill: ${resData.error}`);
        }
    } catch (err) {
        console.error("Submit SqFt bill error:", err);
        alert("Failed to issue SqFt construction bill.");
    }
}

// 6. MODAL SUBMISSIONS & ACTIONS
async function submitAddCustomer() {
    const shop = document.getElementById('m-cust-shop').value;
    if (!shop) return alert("Shop name is required!");

    const payload = {
        shop_name: shop,
        contact_person: document.getElementById('m-cust-person').value,
        phone: document.getElementById('m-cust-phone').value,
        gstin: document.getElementById('m-cust-gstin').value,
        address: document.getElementById('m-cust-address').value,
        maps_location_link: document.getElementById('m-cust-maps-link')?.value || "",
        customer_type: 'shop',
        opening_balance: parseFloat(document.getElementById('m-cust-balance').value) || 0
    };

    const res = await fetch('/api/customers', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (data.success) {
        bootstrap.Modal.getInstance(document.getElementById('newCustomerModal')).hide();
        document.getElementById('add-customer-form').reset();
        await loadCustomers();
    } else {
        alert(data.error || "Failed to create shop record.");
    }
}

async function submitAddClient() {
    const name = document.getElementById('m-client-name').value;
    if (!name) return alert("Client / Project name is required!");

    const payload = {
        shop_name: name,
        contact_person: document.getElementById('m-client-person').value,
        phone: document.getElementById('m-client-phone').value,
        address: document.getElementById('m-client-address').value,
        maps_location_link: document.getElementById('m-client-maps-link')?.value || "",
        customer_type: 'client',
        opening_balance: parseFloat(document.getElementById('m-client-balance').value) || 0
    };

    const res = await fetch('/api/customers', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (data.success) {
        bootstrap.Modal.getInstance(document.getElementById('newClientModal')).hide();
        document.getElementById('add-client-form').reset();
        await loadClients();
    } else {
        alert(data.error || "Failed to create construction client.");
    }
}

async function submitAddProduct() {
    const brand = document.getElementById('m-prod-brand').value;
    const name = document.getElementById('m-prod-name').value;
    const mrp = parseFloat(document.getElementById('m-prod-mrp').value) || 0;

    if (!brand || !name || mrp <= 0) return alert("Brand, Name and MRP are required!");

    const payload = {
        brand: brand,
        product_name: name,
        variant: document.getElementById('m-prod-variant').value,
        sku: document.getElementById('m-prod-sku').value,
        mrp: mrp,
        gst_rate: parseFloat(document.getElementById('m-prod-gst').value) || 18,
        opening_stock: parseFloat(document.getElementById('m-prod-stock').value) || 0
    };

    const res = await fetch('/api/products', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (data.success) {
        bootstrap.Modal.getInstance(document.getElementById('newProductModal')).hide();
        document.getElementById('add-product-form').reset();
        await loadProducts();
    } else {
        alert(data.error);
    }
}

function openRecordPaymentModal(invId, invNumber, balance) {
    document.getElementById('pay-invoice-id').value = invId;
    document.getElementById('pay-inv-number').value = invNumber;
    document.getElementById('pay-outstanding-balance').value = `₹${balance.toFixed(2)}`;
    document.getElementById('pay-amount').value = balance.toFixed(2);
    
    new bootstrap.Modal(document.getElementById('recordPaymentModal')).show();
}

async function submitRecordPayment() {
    const invId = parseInt(document.getElementById('pay-invoice-id').value);
    const amount = parseFloat(document.getElementById('pay-amount').value);
    const method = document.getElementById('pay-method').value;

    if (!amount || amount <= 0) return alert("Enter valid payment amount!");

    const res = await fetch(`/api/invoices/${invId}/pay`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ amount: amount, method: method })
    });

    const data = await res.json();
    if (data.success) {
        bootstrap.Modal.getInstance(document.getElementById('recordPaymentModal')).hide();
        await loadAllData();
    } else {
        alert(data.error);
    }
}

let currentViewedInvoiceId = null;

async function viewInvoiceDetail(invId) {
    currentViewedInvoiceId = invId;
    const modalBody = document.getElementById('invoice-modal-body');
    modalBody.innerHTML = '<div class="text-center py-4"><i class="fa-solid fa-spinner fa-spin fa-2x"></i> Loading...</div>';
    
    const modal = new bootstrap.Modal(document.getElementById('viewInvoiceModal'));
    modal.show();

    try {
        const res = await fetch(`/api/invoices/${invId}`);
        const data = await res.json();
        if (!data.success) {
            modalBody.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
            return;
        }

        const inv = data.invoice;

        const pdfBtnsContainer = document.getElementById('invoice-modal-pdf-btns');
        if (inv.status === 'pending_approval' || inv.status === 'draft') {
            if (pdfBtnsContainer) pdfBtnsContainer.classList.add('d-none');
        } else {
            if (pdfBtnsContainer) pdfBtnsContainer.classList.remove('d-none');
        }

        const isRequest = inv.status === 'pending_approval' || (inv.invoice_number && inv.invoice_number.startsWith('REQ-'));
        const displayInvNumber = isRequest ? `Order Request #${inv.id}` : inv.invoice_number;

        modalBody.innerHTML = `
            <div class="p-3 rounded border mb-4" style="background-color: rgba(15, 23, 42, 0.9); border-color: #334155 !important;">
                <div class="row">
                    <div class="col-6">
                        <h4 class="fw-bold text-primary mb-1">${displayInvNumber} ${inv.is_sealed ? '<span class="badge bg-success-subtle text-success border border-success-subtle rounded-pill ms-2"><i class="fa-solid fa-stamp me-1"></i>Sealed</span>' : ''}</h4>
                        <div class="text-secondary small">Date: ${inv.invoice_date.split('T')[0]}</div>
                        <div class="text-secondary small">Status: <span class="badge bg-secondary">${inv.status.toUpperCase()}</span></div>
                        ${state.currentRole === 'admin' ? `<div class="text-info small mt-1"><i class="fa-solid fa-user me-1"></i>Issued / Created By: <strong>${inv.created_by || 'Admin'}</strong></div>` : ''}
                    </div>
                    <div class="col-6 text-end">
                        <h5 class="fw-bold text-light">${inv.customer_name}</h5>
                        <div class="text-secondary small">${inv.customer_address || 'No Address'}</div>
                        <div class="text-secondary small">GSTIN: ${inv.customer_gstin || 'N/A'}</div>
                    </div>
                </div>
            </div>

            <h6 class="fw-bold mb-3">Line Items</h6>
            <div class="table-responsive mb-4">
                <table class="table table-custom">
                    <thead>
                        <tr>
                            <th>Item</th>
                            <th>Qty</th>
                            <th>Selling Price</th>
                            <th>GST</th>
                            <th>Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${inv.items.map(item => `
                            <tr>
                                <td>${item.brand} ${item.product_name}</td>
                                <td>${item.quantity} Bags</td>
                                <td>₹${item.selling_price.toFixed(2)}</td>
                                <td>${item.gst_rate}%</td>
                                <td class="fw-bold">₹${item.line_total.toFixed(2)}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>

            <div class="row">
                <div class="col-6">
                    <div class="mb-2"><small class="text-muted">Notes: ${inv.notes || 'None'}</small></div>
                    ${inv.maps_location_link ? `
                        <div class="p-2 rounded bg-dark border border-secondary d-inline-block">
                            <i class="fa-solid fa-map-location-dot text-info me-2"></i>
                            <span class="small text-light me-2">Site Location:</span>
                            <a href="${inv.maps_location_link}" target="_blank" class="btn btn-xs btn-outline-info text-decoration-none shadow-sm">
                                <i class="fa-solid fa-arrow-up-right-from-square me-1"></i> Open Google Maps
                            </a>
                        </div>
                    ` : ''}
                </div>
                <div class="col-6 text-end">
                    <div class="d-flex justify-content-between mb-1">
                        <span class="text-muted">Subtotal (Taxable):</span>
                        <span>₹${inv.subtotal.toFixed(2)}</span>
                    </div>
                    <div class="d-flex justify-content-between mb-1">
                        <span class="text-muted">Total GST:</span>
                        <span>₹${(inv.total_cgst + inv.total_sgst).toFixed(2)}</span>
                    </div>
                    ${inv.transport > 0 ? `
                        <div class="d-flex justify-content-between mb-1">
                            <span class="text-info fw-medium"><i class="fa-solid fa-truck me-1"></i>Transport (Without GST):</span>
                            <span class="text-info fw-bold">₹${inv.transport.toFixed(2)}</span>
                        </div>
                    ` : ''}
                    <div class="d-flex justify-content-between fs-5 fw-bold border-top border-secondary pt-2 mt-2">
                        <span>Grand Total:</span>
                        <span class="text-success">₹${inv.grand_total.toFixed(2)}</span>
                    </div>
                </div>
            </div>
        `;
    } catch (e) {
        modalBody.innerHTML = `<div class="alert alert-danger">Error loading invoice details.</div>`;
    }
}

let targetPdfInvoiceId = null;

function promptPdfType(invId) {
    targetPdfInvoiceId = invId;
    const modalEl = document.getElementById('pdfChoiceModal');
    if (modalEl) {
        const bsModal = new bootstrap.Modal(modalEl);
        bsModal.show();
    } else {
        const choice = confirm("Press 'OK' for Sealed (Stamped) PDF, or 'Cancel' for Standard (Unsealed) PDF.");
        window.open(`/api/invoices/${invId}/pdf?sealed=${choice}`, '_blank');
    }
}

function openChosenPdf(isSealed) {
    if (targetPdfInvoiceId) {
        window.open(`/api/invoices/${targetPdfInvoiceId}/pdf?sealed=${isSealed}`, '_blank');
    }
    const modalEl = document.getElementById('pdfChoiceModal');
    if (modalEl) {
        const bsModal = bootstrap.Modal.getInstance(modalEl);
        if (bsModal) bsModal.hide();
    }
}

function printInvoicePDF(isSealed = false) {
    if (currentViewedInvoiceId) {
        window.open(`/api/invoices/${currentViewedInvoiceId}/pdf?sealed=${isSealed}`, '_blank');
    }
}

async function loadUsers() {
    try {
        const res = await fetch('/api/users');
        const data = await res.json();
        const tbody = document.getElementById('users-list-tbody');
        if (!tbody) return;
        tbody.innerHTML = '';

        if (!data.success) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-center text-danger py-4">Error loading users: ${data.error || 'Access denied'}</td></tr>`;
            return;
        }

        if (data.users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">No users found.</td></tr>';
            return;
        }

        data.users.forEach(u => {
            const tr = document.createElement('tr');
            let roleBadge = 'bg-secondary';
            if (u.role === 'admin') roleBadge = 'bg-danger';
            if (u.role === 'sales_executive') roleBadge = 'bg-warning text-dark';
            if (u.role === 'billing') roleBadge = 'bg-info text-dark';

            let roleLabel = u.role === 'sales_executive' ? 'SALES MANAGER' : (u.role === 'admin' ? 'ADMINISTRATOR' : (u.role === 'billing' ? 'BILLING USER' : u.role.toUpperCase()));

            tr.innerHTML = `
                <td class="fw-bold text-light"><i class="fa-solid fa-user-circle me-2 text-info"></i>${u.username}</td>
                <td>${u.full_name || '-'}</td>
                <td><span class="badge ${roleBadge} px-2 py-1">${roleLabel}</span></td>
                <td><span class="badge bg-primary-subtle text-primary border border-primary px-2 py-1 fw-bold"><i class="fa-solid fa-file-invoice me-1"></i>${u.total_invoices || 0} bills</span></td>
                <td><span class="badge bg-warning-subtle text-warning border border-warning px-2 py-1 fw-bold"><i class="fa-solid fa-paper-plane me-1"></i>${u.orders_requested || 0} orders</span></td>
                <td class="fw-bold text-success">₹${(u.total_sales || 0).toFixed(2)}</td>
                <td class="text-secondary small">${u.created_at ? u.created_at.split('T')[0] : '-'}</td>
                <td class="text-center">
                    ${state.currentRole === 'admin' ? `
                        <div class="btn-group btn-group-sm">
                            <button class="btn btn-info text-white fw-bold" title="View Full Activity Logs" onclick="viewUserLogs(${u.id})">
                                <i class="fa-solid fa-list-check me-1"></i> View Logs
                            </button>
                            <button class="btn btn-outline-warning" title="Reset Password" onclick="openAdminResetPasswordModal(${u.id}, '${u.username}')">
                                <i class="fa-solid fa-key me-1"></i> Reset PW
                            </button>
                            ${u.username !== 'admin' ? `
                                <button class="btn btn-outline-danger" title="Deactivate User" onclick="deleteUser(${u.id}, '${u.username}')">
                                    <i class="fa-solid fa-user-xmark me-1"></i> Deactivate
                                </button>
                            ` : ''}
                        </div>
                    ` : '<span class="text-muted small">Protected</span>'}
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Error loading users:", err);
        const tbody = document.getElementById('users-list-tbody');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-danger py-4">Failed to load user list from server.</td></tr>';
        }
    }
}

async function viewUserLogs(userId) {
    const modalBody = document.getElementById('user-logs-modal-body');
    modalBody.innerHTML = '<div class="text-center py-4"><i class="fa-solid fa-spinner fa-spin fa-2x"></i> Loading logs...</div>';

    const modalEl = document.getElementById('userLogsModal');
    const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
    modal.show();

    try {
        const res = await fetch(`/api/users/${userId}/logs`);
        const data = await res.json();
        if (!data.success) {
            modalBody.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
            return;
        }

        const u = data.user;
        const stats = data.stats;
        const logs = data.logs;

        let logsRowsHtml = '';
        if (logs.length === 0) {
            logsRowsHtml = '<tr><td colspan="7" class="text-center text-muted py-3">No activity logs recorded for this user.</td></tr>';
        } else {
            logs.forEach(l => {
                let statusBadge = 'bg-success';
                if (l.is_order_request || l.status === 'pending_approval') statusBadge = 'bg-warning text-dark';
                else if (l.status === 'deleted') statusBadge = 'bg-danger';

                logsRowsHtml += `
                    <tr>
                        <td class="fw-bold text-light">${l.invoice_number}</td>
                        <td>${l.date ? l.date.split('T')[0] : '-'}</td>
                        <td>${l.customer_name}</td>
                        <td><span class="badge ${l.is_order_request ? 'bg-warning-subtle text-warning border border-warning' : 'bg-primary-subtle text-primary border border-primary'} px-2 py-1">${l.is_order_request ? 'ORDER REQUEST' : 'FINAL INVOICE'}</span></td>
                        <td class="fw-bold text-success">₹${l.grand_total.toFixed(2)}</td>
                        <td><span class="badge ${statusBadge} px-2 py-1">${l.status.toUpperCase()}</span></td>
                        <td>
                            <button class="btn btn-xs btn-outline-info" onclick="viewInvoiceDetail(${l.id})"><i class="fa-solid fa-eye me-1"></i> Inspect</button>
                        </td>
                    </tr>
                `;
            });
        }

        modalBody.innerHTML = `
            <div class="d-flex justify-content-between align-items-center p-3 rounded mb-4" style="background-color: rgba(15, 23, 42, 0.9); border: 1px solid #334155;">
                <div>
                    <h5 class="fw-bold text-light mb-1"><i class="fa-solid fa-user-tag text-info me-2"></i>${u.username} (${u.full_name})</h5>
                    <span class="badge bg-secondary text-uppercase">${u.role === 'sales_executive' ? 'Sales Manager' : u.role}</span>
                </div>
                <div class="text-end">
                    <small class="text-secondary d-block">Total Generated Revenue</small>
                    <span class="fs-4 fw-bold text-success">₹${stats.total_sales.toFixed(2)}</span>
                </div>
            </div>

            <h6 class="fw-bold mb-3"><i class="fa-solid fa-list-check me-2 text-warning"></i>Transaction & Creation History (${logs.length})</h6>
            <div class="table-responsive">
                <table class="table table-custom align-middle mb-0">
                    <thead>
                        <tr>
                            <th>Ref #</th>
                            <th>Date</th>
                            <th>Customer / Shop</th>
                            <th>Type</th>
                            <th>Grand Total</th>
                            <th>Status</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${logsRowsHtml}
                    </tbody>
                </table>
            </div>
        `;
    } catch (e) {
        console.error("View User Logs Error:", e);
        modalBody.innerHTML = `<div class="alert alert-danger">Error loading user activity logs.</div>`;
    }
}

async function submitAddUser() {
    const username = document.getElementById('m-user-username').value.trim();
    const password = document.getElementById('m-user-password').value;
    const fullName = document.getElementById('m-user-fullname').value.trim();
    const role = document.getElementById('m-user-role').value;

    if (!username || !password) return alert("Username and Password are required!");

    try {
        const res = await fetch('/api/users', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                username: username,
                password: password,
                full_name: fullName,
                role: role
            })
        });

        const data = await res.json();
        if (data.success) {
            alert(data.message);
            bootstrap.Modal.getInstance(document.getElementById('newUserModal')).hide();
            document.getElementById('add-user-form').reset();
            await loadUsers();
        } else {
            alert(data.error);
        }
    } catch (e) {
        alert("Failed to create user.");
    }
}

async function deleteUser(userId, username) {
    if (!confirm(`Deactivate user account "${username}"?`)) return;
    try {
        const res = await fetch(`/api/users/${userId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            alert(data.message);
            await loadUsers();
        } else {
            alert(data.error);
        }
    } catch (e) {
        alert("Failed to deactivate user.");
    }
}

async function loadDeliveryRequests() {
      try {
          const res = await fetch('/api/delivery-requests');
          const data = await res.json();
          
          if (data.success) {
              const tbody = document.getElementById('delivery-requests-tbody');
              const badge = document.getElementById('delivery-requests-badge');
              const deliveredTbody = document.getElementById('delivered-orders-tbody');
              const deliveredBadge = document.getElementById('delivered-orders-badge');
              
              let activeOrders = [];
              let deliveredOrders = [];
              
              data.orders.forEach(ord => {
                  if (ord.status === 'delivered') {
                      deliveredOrders.push(ord);
                  } else {
                      activeOrders.push(ord);
                  }
              });

              if (badge) {
                  if (activeOrders.length > 0) {
                      badge.innerText = activeOrders.length;
                      badge.classList.remove('d-none');
                  } else {
                      badge.classList.add('d-none');
                  }
              }
              
              if (deliveredBadge) {
                  if (deliveredOrders.length > 0) {
                      deliveredBadge.innerText = deliveredOrders.length;
                      deliveredBadge.classList.remove('d-none');
                  } else {
                      deliveredBadge.classList.add('d-none');
                  }
              }
              
              const appendRow = (targetTbody, ord) => {
                  const tr = document.createElement('tr');
                  const dateObj = new Date(ord.invoice_date);
                  const isReady = ord.status === 'stock_ready';
                  const isDelivered = ord.status === 'delivered';
                  const isRequested = ord.status === 'order_requested';
                  
                  let statusBadge = `<span class="badge bg-warning text-dark"><i class="fa-solid fa-clock me-1"></i> Requested</span>`;
                  if (isReady) statusBadge = `<span class="badge bg-info text-dark"><i class="fa-solid fa-box me-1"></i> Stock Ready</span>`;
                  if (isDelivered) statusBadge = `<span class="badge bg-success"><i class="fa-solid fa-check me-1"></i> Delivered</span>`;
  
                  tr.innerHTML = `
                      <td class="fw-bold">#${ord.invoice_number}</td>
                      <td>
                          <div class="fw-medium">${dateObj.toLocaleDateString('en-GB')}</div>
                          <small class="text-muted">${dateObj.toLocaleTimeString('en-US', {hour: '2-digit', minute:'2-digit'})}</small>
                      </td>
                      <td>
                          <div class="fw-bold text-info">${ord.customer_name}</div>
                          ${ord.customer_phone ? `<small class="text-muted"><i class="fa-solid fa-phone me-1"></i>${ord.customer_phone}</small>` : ''}
                      </td>
                      <td>
                          <ul class="list-unstyled mb-0 small">
                              ${ord.items.map(i => `<li><i class="fa-solid fa-caret-right text-secondary me-1"></i><span class="fw-semibold">${i.quantity} ${i.unit}</span> ${i.brand} ${i.product_name}</li>`).join('')}
                          </ul>
                      </td>
                      <td>${statusBadge}</td>
                      <td class="fw-bold text-success">₹${ord.grand_total.toFixed(2)}</td>
                      <td class="admin-only text-muted small">${ord.created_by}</td>
                      ${!isDelivered ? `
                      <td class="text-center">
                          <div class="btn-group">
                              ${isRequested ? `<button class="btn btn-sm btn-outline-info" onclick="updateDeliveryStatus(${ord.id}, 'stock_ready')" title="Mark Stock Ready"><i class="fa-solid fa-box"></i> Stock Ready</button>` : ''}
                              ${isReady ? `<button class="btn btn-sm btn-outline-success" onclick="updateDeliveryStatus(${ord.id}, 'delivered')" title="Mark Delivered"><i class="fa-solid fa-truck"></i> Deliver</button>` : ''}
                              <button class="btn btn-sm btn-outline-danger" onclick="rejectOrder(${ord.id})" title="Cancel Request"><i class="fa-solid fa-xmark"></i></button>
                          </div>
                      </td>` : ''}
                  `;
                  targetTbody.appendChild(tr);
              };

              if (activeOrders.length === 0) {
                  tbody.innerHTML = '<tr><td colspan="8" class="text-center text-secondary py-4 fw-medium">No active delivery requests found.</td></tr>';
              } else {
                  tbody.innerHTML = '';
                  activeOrders.forEach(ord => appendRow(tbody, ord));
              }
              
              if (deliveredTbody) {
                  if (deliveredOrders.length === 0) {
                      deliveredTbody.innerHTML = '<tr><td colspan="7" class="text-center text-secondary py-4 fw-medium">No delivered orders found.</td></tr>';
                  } else {
                      deliveredTbody.innerHTML = '';
                      deliveredOrders.forEach(ord => appendRow(deliveredTbody, ord));
                  }
              }
              
              updateAdminVisibility();
          }
      } catch (e) {
          console.error("Error loading delivery requests:", e);
      }
  }

async function updateDeliveryStatus(invId, newStatus) {
    if (!confirm(`Are you sure you want to mark this request as ${newStatus}?`)) return;
    try {
        const res = await fetch(`/api/delivery-requests/${invId}/update-status`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({status: newStatus})
        });
        const data = await res.json();
        if (data.success) {
            await loadDeliveryRequests();
        } else {
            alert(data.error || "Failed to update status.");
        }
    } catch (e) {
        console.error(e);
        alert("Error updating status.");
    }
}

function updateAdminVisibility() {
    if (state && state.currentUser && state.currentUser.role === 'admin') {
        document.querySelectorAll('.admin-only').forEach(el => el.classList.remove('d-none'));
    } else {
        document.querySelectorAll('.admin-only').forEach(el => el.classList.add('d-none'));
    }
}
