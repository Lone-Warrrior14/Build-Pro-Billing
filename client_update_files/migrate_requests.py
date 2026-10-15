import sqlite3
import os

def migrate():
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'buildpro.db')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("UPDATE invoices SET status = 'ORDER_REQUESTED' WHERE status IN ('PENDING_APPROVAL', 'pending_approval')")
    cursor.execute("UPDATE invoices SET status = 'STOCK_READY' WHERE status IN ('DRAFT', 'draft')")
    
    # Ensure delivered_at column exists
    cursor.execute("PRAGMA table_info(invoices)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'delivered_at' not in columns:
        cursor.execute("ALTER TABLE invoices ADD COLUMN delivered_at DATETIME")
        print("Added delivered_at column to invoices table.")

    conn.commit()
    conn.close()
    print("Migration completed successfully.")

if __name__ == "__main__":
    migrate()
