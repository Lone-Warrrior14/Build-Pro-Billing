import re
import os

with open("templates/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# Add new nav link for Delivered Orders right after Delivery Requests
nav_addition = """
                    <li class="nav-item">
                        <a class="nav-link text-success fw-semibold" id="nav-delivered-orders" href="#" onclick="switchTab('delivered-orders')">
                            <i class="fa-solid fa-check-double me-1"></i> Delivered Orders
                            <span id="delivered-orders-badge" class="badge bg-success rounded-pill ms-1 d-none">0</span>
                        </a>
                    </li>
"""
html = html.replace('<span id="delivery-requests-badge" class="badge bg-danger rounded-pill ms-1 d-none">0</span>\n                        </a>\n                    </li>', 
                    '<span id="delivery-requests-badge" class="badge bg-danger rounded-pill ms-1 d-none">0</span>\n                        </a>\n                    </li>' + nav_addition)


# Add new tab page for Delivered Orders right after Delivery Requests tab
tab_addition = """
        <!-- DELIVERED ORDERS TAB -->
        <div id="tab-delivered-orders" class="tab-page d-none">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <div>
                    <h3 class="fw-bold mb-1"><i class="fa-solid fa-check-double text-success me-2"></i> Delivered Orders</h3>
                    <p class="text-muted mb-0">Past delivery requests that have been successfully delivered.</p>
                </div>
                <button class="btn btn-outline-light btn-sm" onclick="loadDeliveryRequests()">
                    <i class="fa-solid fa-rotate me-1"></i> Refresh Requests
                </button>
            </div>

            <div class="card card-custom">
                <div class="card-header bg-transparent border-secondary py-3">
                    <h5 class="fw-bold mb-0 text-light"><i class="fa-solid fa-clipboard-check me-2 text-success"></i> Delivered Orders History</h5>
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
                                </tr>
                            </thead>
                            <tbody id="delivered-orders-tbody">
                                <tr><td colspan="7" class="text-center text-muted py-4">Loading delivered orders...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
"""

# Find where tab-delivery-requests ends and insert tab_addition
end_of_delivery_tab = '                    </div>\n                </div>\n            </div>\n        </div>\n'
html = html.replace(end_of_delivery_tab, end_of_delivery_tab + "\n" + tab_addition)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(html)
print("Updated index.html")
