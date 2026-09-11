import os

with open("app_web.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace any remaining DRAFT endpoint stuff just in case.
# We will use regex to remove the draft_orders and approve_to_draft endpoints.
import re

content = re.sub(r'@app\.route\("/api/draft-orders".*?return jsonify\(\{"success": True, "draft_orders": res\}\)\n', '', content, flags=re.DOTALL)
content = re.sub(r'@app\.route\("/api/invoices/<int:invoice_id>/approve-to-draft".*?except Exception as e:\s+return jsonify\(\{"success": False, "error": str\(e\)\}\), 400\n', '', content, flags=re.DOTALL)
content = re.sub(r'@app\.route\("/api/invoices/<int:invoice_id>/approve".*?except Exception as e:\s+return jsonify\(\{"success": False, "error": str\(e\)\}\), 400\n', '', content, flags=re.DOTALL)

content = content.replace("Invoice.status != InvoiceStatus.ORDER_REQUESTED", "Invoice.status.notin_([InvoiceStatus.ORDER_REQUESTED, InvoiceStatus.STOCK_READY, InvoiceStatus.DELIVERED])")
content = content.replace("Invoice.status == InvoiceStatus.ORDER_REQUESTED", "Invoice.status.in_([InvoiceStatus.ORDER_REQUESTED, InvoiceStatus.STOCK_READY, InvoiceStatus.DELIVERED])")
content = content.replace("is_order = inv.status.in_([InvoiceStatus.ORDER_REQUESTED, InvoiceStatus.STOCK_READY, InvoiceStatus.DELIVERED])", "is_order = inv.status in [InvoiceStatus.ORDER_REQUESTED, InvoiceStatus.STOCK_READY, InvoiceStatus.DELIVERED]")

with open("app_web.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Removed draft and approve endpoints")
