import sqlite3
import os

def migrate():
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'buildpro.db')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("UPDATE invoices SET status = 'ORDER_REQUESTED' WHERE status IN ('PENDING_APPROVAL', 'pending_approval')")
    cursor.execute("UPDATE invoices SET status = 'STOCK_READY' WHERE status IN ('DRAFT', 'draft')")
    
    conn.commit()
    conn.close()
    print("Fixed migration of uppercase enum values.")

if __name__ == "__main__":
    migrate()
