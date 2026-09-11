import os

with open("static/app.js", "r", encoding="utf-8") as f:
    js = f.read()

# Replace the inner part of loadDeliveryRequests where it processes the orders
old_processing = """
              if (data.orders.length === 0) {
                  tbody.innerHTML = '<tr><td colspan="8" class="text-center text-secondary py-4 fw-medium">No delivery requests found.</td></tr>';
                  return;
              }
              
              tbody.innerHTML = '';
              data.orders.forEach(ord => {
"""

new_processing = """
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
              
              if (activeOrders.length === 0) {
                  tbody.innerHTML = '<tr><td colspan="8" class="text-center text-secondary py-4 fw-medium">No active delivery requests found.</td></tr>';
              } else {
                  tbody.innerHTML = '';
                  activeOrders.forEach(ord => {
                      appendOrderRow(tbody, ord);
                  });
              }
              
              if (deliveredTbody) {
                  if (deliveredOrders.length === 0) {
                      deliveredTbody.innerHTML = '<tr><td colspan="8" class="text-center text-secondary py-4 fw-medium">No delivered orders found.</td></tr>';
                  } else {
                      deliveredTbody.innerHTML = '';
                      deliveredOrders.forEach(ord => {
                          appendOrderRow(deliveredTbody, ord);
                      });
                  }
              }
"""

js = js.replace("""
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
              data.orders.forEach(ord => {""", new_processing)

# We need to extract the row creation logic into `appendOrderRow(tbody, ord)`
# The existing logic is right below `data.orders.forEach(ord => {` 

row_creation_logic = """function appendOrderRow(targetTbody, ord) {
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
                              ${!isDelivered ? `<button class="btn btn-sm btn-outline-danger" onclick="rejectOrder(${ord.id})" title="Cancel Request"><i class="fa-solid fa-xmark"></i></button>` : ''}
                          </div>
                      </td>
                  `;
                  targetTbody.appendChild(tr);
              }"""

# So we just replace the original `ord => { ... }` with the new structure.
# Actually it's easier to just use string replace for the whole `try { ... }` block of `loadDeliveryRequests`.

full_new_load_delivery_requests = """async function loadDeliveryRequests() {
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
  }"""

import re
js = re.sub(r'async function loadDeliveryRequests\(\) \{.*?updateAdminVisibility\(\);\s*\}\s*\} catch \(e\) \{\s*console\.error\("Error loading delivery requests:", e\);\s*\}\s*\}', full_new_load_delivery_requests, js, flags=re.DOTALL)

with open("static/app.js", "w", encoding="utf-8") as f:
    f.write(js)
print("Updated static/app.js")
