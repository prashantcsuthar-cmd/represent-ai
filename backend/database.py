import sqlite3
import os

DB_PATH = "represent_ai.db"

def fetch_dispute_context(order_id: str) -> dict:
    """Fetches combined relational data across Orders and Deliveries tables."""
    if not os.path.exists(DB_PATH):
        return None
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = """
    SELECT 
        o.order_id, o.customer_name, o.amount, o.ip_address, o.payment_status,
        d.tracking_number, d.carrier, d.status, d.delivery_timestamp, d.has_signature
    FROM orders o
    LEFT JOIN deliveries d ON o.order_id = d.order_id
    WHERE o.order_id = ?
    """
    
    try:
        cursor.execute(query, (order_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
            
        return {
            "order_id": row[0],
            "customer_name": row[1],
            "amount": row[2],
            "ip_address": row[3],
            "payment_status": row[4],
            "tracking_number": row[5],
            "carrier": row[6],
            "delivery_status": row[7] if row[7] else "UNKNOWN",
            "delivery_timestamp": row[8],
            "has_signature": bool(row[9]) if row[9] is not None else False
        }
    except Exception:
        if conn:
            conn.close()
        return None