import re
import os

with open("app_web.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace endpoint for delivery requests
content = content.replace('@app.route("/api/order-requests", methods=["GET"])', '@app.route("/api/delivery-requests", methods=["GET"])')

# Ensure we include all three delivery statuses in the delivery requests endpoint
content = content.replace('Invoice.status == InvoiceStatus.ORDER_REQUESTED', 'Invoice.status.in_([InvoiceStatus.ORDER_REQUESTED, InvoiceStatus.STOCK_READY, InvoiceStatus.DELIVERED])')

# Ensure we EXCLUDE all three delivery statuses from invoices
content = content.replace('Invoice.status.notin_([InvoiceStatus.ORDER_REQUESTED, InvoiceStatus.DELETED])', 'Invoice.status.notin_([InvoiceStatus.ORDER_REQUESTED, InvoiceStatus.STOCK_READY, InvoiceStatus.DELIVERED, InvoiceStatus.DELETED])')
content = content.replace('Invoice.status != InvoiceStatus.ORDER_REQUESTED', 'Invoice.status.notin_([InvoiceStatus.ORDER_REQUESTED, InvoiceStatus.STOCK_READY, InvoiceStatus.DELIVERED])')

# We'll write this back and append the new update endpoint
with open("app_web.py", "w", encoding="utf-8") as f:
    f.write(content)

with open("app_web.py", "a", encoding="utf-8") as f:
    f.write('''
@app.route("/api/delivery-requests/<int:invoice_id>/update-status", methods=["POST"])
def update_delivery_status(invoice_id: int):
    from flask import request, jsonify, session as flask_session
    from database.connection import session_scope
    from database.models import Invoice, InvoiceStatus
    data = request.get_json(silent=True) or {}
    new_status_str = data.get("status")
    
    valid_statuses = {
        "order_requested": InvoiceStatus.ORDER_REQUESTED,
        "stock_ready": InvoiceStatus.STOCK_READY,
        "delivered": InvoiceStatus.DELIVERED
    }
    
    if new_status_str not in valid_statuses:
        return jsonify({"success": False, "error": "Invalid status"}), 400
        
    with session_scope() as session:
        try:
            inv = session.get(Invoice, invoice_id)
            if not inv:
                return jsonify({"success": False, "error": "Delivery request not found"}), 404
            
            inv.status = valid_statuses[new_status_str]
            return jsonify({"success": True, "message": f"Delivery request {inv.invoice_number} updated to {new_status_str}!"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400
''')

print("Refactored app_web.py")
