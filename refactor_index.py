import re

with open("templates/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# 1. Update Navigation
nav_replacement = """
                    <li class="nav-item">
                        <a class="nav-link text-warning fw-semibold" id="nav-delivery-requests" href="#" onclick="switchTab('delivery-requests')">
                            <i class="fa-solid fa-truck-ramp-box me-1"></i> Delivery Requests
                            <span id="delivery-requests-badge" class="badge bg-danger rounded-pill ms-1 d-none">0</span>
                        </a>
                    </li>
"""
# Replace the new-orders nav item
html = re.sub(r'<li class="nav-item">\s*<a class="nav-link text-warning fw-semibold" id="nav-new-orders".*?</li>', nav_replacement.strip(), html, flags=re.DOTALL)

# Remove the draft-orders nav item
html = re.sub(r'<li class="nav-item">\s*<a class="nav-link text-info fw-semibold" id="nav-draft-orders".*?</li>', '', html, flags=re.DOTALL)


# 2. Update the Tab Page Content
tab_replacement = """
        <!-- DELIVERY REQUESTS TAB -->
        <div id="tab-delivery-requests" class="tab-page d-none">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div>
                    <h3 class="fw-bold mb-1"><i class="fa-solid fa-truck-ramp-box text-warning me-2"></i> Delivery Requests</h3>
                    <p class="text-muted mb-0">Track order requests from order to stock ready to delivery.</p>
                </div>
                <button class="btn btn-outline-light btn-sm" onclick="loadDeliveryRequests()">
                    <i class="fa-solid fa-rotate me-1"></i> Refresh Requests
                </button>
            </div>

            <!-- Pending Order Requests Table -->
            <div class="card card-custom">
                <div class="card-header bg-transparent border-secondary py-3">
                    <h5 class="fw-bold mb-0 text-light"><i class="fa-solid fa-clipboard-list me-2 text-info"></i> Delivery Requests List</h5>
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-custom mb-0">
                            <thead>
                                <tr>
                                    <th>Request #</th>
                                    <th>Date</th>
                                    <th>Customer / Shop</th>
                                    <th>Requested Items</th>
                                    <th>Status</th>
                                    <th>Total (₹)</th>
                                    <th class="admin-only">Requested By</th>
                                    <th class="text-center">Actions</th>
                                </tr>
                            </thead>
                            <tbody id="delivery-requests-tbody">
                                <tr><td colspan="8" class="text-center text-muted py-4">Loading delivery requests...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
"""
# Replace the new-orders tab content
html = re.sub(r'<!-- NEW ORDERS TAB.*?<div id="tab-new-orders".*?</div>\s*</div>\s*</div>\s*</div>', tab_replacement.strip(), html, flags=re.DOTALL)

# Remove the draft-orders tab content
html = re.sub(r'<!-- DRAFT ORDERS TAB.*?<div id="tab-draft-orders".*?</div>\s*</div>\s*</div>\s*</div>', '', html, flags=re.DOTALL)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Updated index.html")
