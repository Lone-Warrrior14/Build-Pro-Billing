import os

with open("services/billing_service.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("InvoiceStatus.PENDING_APPROVAL", "InvoiceStatus.ORDER_REQUESTED")
content = content.replace("InvoiceStatus.DRAFT", "InvoiceStatus.STOCK_READY")
content = content.replace("PENDING_APPROVAL", "ORDER_REQUESTED")

with open("services/billing_service.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated billing_service.py")
