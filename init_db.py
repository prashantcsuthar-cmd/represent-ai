import sqlite3

conn = sqlite3.connect("represent_ai.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    customer_name TEXT,
    amount REAL,
    dispute_type TEXT,
    gateway TEXT
)
""")

seed_data = [
    ("ORD-1001", "Rahul Sharma", 12500.00, "Product Delivered - OTP Verified", "Razorpay"),
    ("ORD-1002", "Priya Patel", 4200.00, "Digital Goods - IP Log Matched", "Stripe"),
    ("ORD-1003", "Aniket Verma", 8900.00, "Wrong Delivery Address", "Cashfree"),
    ("ORD-1004", "Sneha Kulkarni", 15400.00, "Friendly Fraud - Cardholder Signature On File", "Razorpay"),
    ("ORD-1005", "Vikram Singh", 3100.00, "Duplicate Charge Claim", "PayU")
]

cursor.executemany("INSERT OR REPLACE INTO orders VALUES (?, ?, ?, ?, ?)", seed_data)
conn.commit()
conn.close()
print("Database successfully updated with 5 real dispute cases.")