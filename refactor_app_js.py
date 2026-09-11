import re
import os

with open("static/app.js", "r", encoding="utf-8") as f:
    js = f.read()

# 1. Replace switchTab logic
js = js.replace("tabId === 'new-orders'", "tabId === 'delivery-requests'")
js = js.replace("tabId === 'draft-orders'", "tabId === 'invalid-tab'") # just disable this
js = js.replace("loadNewOrders()", "loadDeliveryRequests()")
js = js.replace("loadDraftOrders()", "loadDeliveryRequests()")

# 2. Add new loadDeliveryRequests and updateDeliveryStatus functions
new_js_functions = """
async function loadDeliveryRequests() {
    try {
        const res = await fetch('/api/delivery-requests');
        const data = await res.json();
        
        if (data.success) {
            const tbody = document.getElementById('delivery-requests-tbody');
            const badge = document.getElementById('delivery-requests-badge');
            
            if (badge) {
                if (data.orders.length > 0) {
                    badge.innerText = data.orders.length;
                    badge.classList.remove('d-none');
                } else {
                    badge.classList.add('d-none');
                }
            }
            
            if (data.orders.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" class="text-center text-secondary py-4 fw-medium">No delivery requests found.</td></tr>';
                return;
            }
            
            tbody.innerHTML = '';
            data.orders.forEach(ord => {
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
                    <td class="text-center">
                        <div class="btn-group">
                            ${isRequested ? `<button class="btn btn-sm btn-outline-info" onclick="updateDeliveryStatus(${ord.id}, 'stock_ready')" title="Mark Stock Ready"><i class="fa-solid fa-box"></i> Stock Ready</button>` : ''}
                            ${isReady ? `<button class="btn btn-sm btn-outline-success" onclick="updateDeliveryStatus(${ord.id}, 'delivered')" title="Mark Delivered"><i class="fa-solid fa-truck"></i> Deliver</button>` : ''}
                            <button class="btn btn-sm btn-outline-danger" onclick="rejectOrder(${ord.id})" title="Cancel Request"><i class="fa-solid fa-xmark"></i></button>
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            });
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
"""

# Append functions to the JS file
js += "\\n" + new_js_functions

# We can optionally remove the old loadNewOrders / loadDraftOrders functions by regex or leave them dead code. We'll try to remove them.
js = re.sub(r'async function loadNewOrders\(\) \{.*?\}(?=\nasync function|\n//)', '', js, flags=re.DOTALL)
js = re.sub(r'async function loadDraftOrders\(\) \{.*?\}(?=\nasync function|\n//)', '', js, flags=re.DOTALL)
js = re.sub(r'async function approveOrder\([^)]*\) \{.*?\}(?=\nasync function|\n//)', '', js, flags=re.DOTALL)
js = re.sub(r'async function approveOrderToDraft\([^)]*\) \{.*?\}(?=\nasync function|\n//)', '', js, flags=re.DOTALL)

with open("static/app.js", "w", encoding="utf-8") as f:
    f.write(js)

print("Updated app.js")
