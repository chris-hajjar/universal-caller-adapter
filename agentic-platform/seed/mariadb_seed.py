"""
Seed script for MariaDB on Railway.

Creates and populates the business data tables:
  - invoices
  - orders
  - users
  - products
  - reports

~10 fake rows each, enough surface area to make permission
differences meaningful across the three test users.

Usage:
    python -m seed.mariadb_seed
"""

from __future__ import annotations

import os
import sys

import mariadb

# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def get_connection():
    """Connect to MariaDB using environment variables."""
    return mariadb.connect(
        host=os.getenv("MARIADB_HOST", "localhost"),
        port=int(os.getenv("MARIADB_PORT", "3306")),
        user=os.getenv("MARIADB_USER", "root"),
        password=os.getenv("MARIADB_PASSWORD", ""),
        database=os.getenv("MARIADB_DATABASE", "agentic_platform"),
    )


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    role VARCHAR(50) DEFAULT 'member',
    department VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    sku VARCHAR(50) UNIQUE NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    category VARCHAR(50),
    stock_quantity INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(30) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS invoices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(30) DEFAULT 'unpaid',
    due_date DATE,
    paid_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

CREATE TABLE IF NOT EXISTS reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    report_type VARCHAR(50) NOT NULL,
    generated_by INT NOT NULL,
    content TEXT,
    is_confidential BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (generated_by) REFERENCES users(id)
);
"""

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

USERS = [
    ("Alice Johnson", "alice@company.com", "admin", "Engineering"),
    ("Bob Smith", "bob@company.com", "manager", "Sales"),
    ("Carol Williams", "carol@company.com", "member", "Marketing"),
    ("Dave Brown", "dave@company.com", "member", "Engineering"),
    ("Eve Davis", "eve@company.com", "manager", "Finance"),
    ("Frank Miller", "frank@company.com", "member", "Sales"),
    ("Grace Wilson", "grace@company.com", "admin", "Operations"),
    ("Henry Taylor", "henry@company.com", "member", "Marketing"),
    ("Ivy Anderson", "ivy@company.com", "member", "Engineering"),
    ("Jack Thomas", "jack@company.com", "manager", "Finance"),
]

PRODUCTS = [
    ("Widget Pro", "WGT-001", 29.99, "Hardware", 150),
    ("Data Connector", "DCN-002", 149.99, "Software", 500),
    ("Analytics Suite", "ANL-003", 299.99, "Software", 200),
    ("Sensor Array", "SNS-004", 79.99, "Hardware", 75),
    ("Cloud Storage 1TB", "CLD-005", 9.99, "Cloud", 9999),
    ("API Gateway License", "API-006", 499.99, "Software", 100),
    ("IoT Hub", "IOT-007", 199.99, "Hardware", 50),
    ("ML Pipeline Starter", "MLP-008", 399.99, "Software", 300),
    ("Edge Compute Node", "ECN-009", 599.99, "Hardware", 25),
    ("Support Plan Premium", "SPT-010", 99.99, "Services", 9999),
]

ORDERS = [
    (1, 1, 2, 59.98, "completed"),
    (2, 3, 1, 299.99, "completed"),
    (3, 5, 5, 49.95, "shipped"),
    (4, 2, 1, 149.99, "pending"),
    (5, 6, 3, 1499.97, "completed"),
    (1, 8, 1, 399.99, "processing"),
    (6, 4, 2, 159.98, "completed"),
    (7, 10, 1, 99.99, "pending"),
    (8, 1, 4, 119.96, "shipped"),
    (9, 7, 1, 199.99, "completed"),
]

INVOICES = [
    (1, "INV-2024-001", 59.98, "paid", "2024-02-15"),
    (2, "INV-2024-002", 299.99, "paid", "2024-02-20"),
    (3, "INV-2024-003", 49.95, "unpaid", "2024-03-15"),
    (4, "INV-2024-004", 149.99, "unpaid", "2024-03-20"),
    (5, "INV-2024-005", 1499.97, "paid", "2024-01-30"),
    (6, "INV-2024-006", 399.99, "unpaid", "2024-04-01"),
    (7, "INV-2024-007", 159.98, "paid", "2024-02-28"),
    (8, "INV-2024-008", 99.99, "unpaid", "2024-04-15"),
    (9, "INV-2024-009", 119.96, "unpaid", "2024-03-30"),
    (10, "INV-2024-010", 199.99, "paid", "2024-02-10"),
]

REPORTS = [
    ("Q1 Revenue Summary", "financial", 5, "Total revenue: $2.3M...", True),
    ("Monthly Active Users", "analytics", 1, "MAU increased 12%...", False),
    ("Product Performance", "sales", 2, "Top seller: Widget Pro...", False),
    ("Infrastructure Costs", "operations", 7, "AWS spend: $45K...", True),
    ("Customer Satisfaction", "support", 6, "NPS score: 72...", False),
    ("Engineering Velocity", "engineering", 1, "Sprint velocity: 42 pts...", False),
    ("Security Audit Q1", "security", 7, "3 critical issues found...", True),
    ("Marketing ROI", "marketing", 3, "CAC decreased 8%...", False),
    ("Quarterly Forecast", "financial", 10, "Projected growth: 15%...", True),
    ("Inventory Status", "operations", 7, "Low stock: SNS-004...", False),
]


# ---------------------------------------------------------------------------
# Seed runner
# ---------------------------------------------------------------------------

def seed():
    """Create tables and insert seed data."""
    conn = get_connection()
    cur = conn.cursor()

    print("Creating tables...")
    for statement in SCHEMA.strip().split(";"):
        statement = statement.strip()
        if statement:
            cur.execute(statement)
    conn.commit()

    print("Seeding users...")
    cur.executemany(
        "INSERT IGNORE INTO users (name, email, role, department) VALUES (?, ?, ?, ?)",
        USERS,
    )

    print("Seeding products...")
    cur.executemany(
        "INSERT IGNORE INTO products (name, sku, price, category, stock_quantity) "
        "VALUES (?, ?, ?, ?, ?)",
        PRODUCTS,
    )
    conn.commit()

    print("Seeding orders...")
    cur.executemany(
        "INSERT IGNORE INTO orders (user_id, product_id, quantity, total_amount, status) "
        "VALUES (?, ?, ?, ?, ?)",
        ORDERS,
    )
    conn.commit()

    print("Seeding invoices...")
    cur.executemany(
        "INSERT IGNORE INTO invoices (order_id, invoice_number, amount, status, due_date) "
        "VALUES (?, ?, ?, ?, ?)",
        INVOICES,
    )

    print("Seeding reports...")
    cur.executemany(
        "INSERT IGNORE INTO reports (title, report_type, generated_by, content, is_confidential) "
        "VALUES (?, ?, ?, ?, ?)",
        REPORTS,
    )

    conn.commit()
    print("Done! Seed data inserted.")

    # Verify counts
    for table in ["users", "products", "orders", "invoices", "reports"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"  {table}: {count} rows")

    cur.close()
    conn.close()


if __name__ == "__main__":
    try:
        seed()
    except mariadb.Error as e:
        print(f"MariaDB error: {e}", file=sys.stderr)
        sys.exit(1)
