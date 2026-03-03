"""
Seed script — creates tables and inserts fake data into MariaDB on Railway.

Tables: invoices, orders, users, products, reports (~10 rows each)

Usage:
    python scripts/seed_mariadb.py
"""

import os
import sys

import mariadb

MARIADB_HOST = os.getenv("MARIADB_HOST", "localhost")
MARIADB_PORT = int(os.getenv("MARIADB_PORT", "3306"))
MARIADB_USER = os.getenv("MARIADB_USER", "root")
MARIADB_PASSWORD = os.getenv("MARIADB_PASSWORD", "")
MARIADB_DATABASE = os.getenv("MARIADB_DATABASE", "agentic_poc")


def get_connection():
    return mariadb.connect(
        host=MARIADB_HOST,
        port=MARIADB_PORT,
        user=MARIADB_USER,
        password=MARIADB_PASSWORD,
        database=MARIADB_DATABASE,
    )


SCHEMA = """
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    department VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    sku VARCHAR(50) UNIQUE NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    category VARCHAR(100),
    stock_qty INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    total DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Invoices table
CREATE TABLE IF NOT EXISTS invoices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    user_id INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) DEFAULT 'unpaid',
    due_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Reports table
CREATE TABLE IF NOT EXISTS reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    report_type VARCHAR(100) NOT NULL,
    content TEXT,
    generated_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

SEED_DATA = """
-- Users
INSERT IGNORE INTO users (id, email, name, role, department) VALUES
(1, 'chris@company.com', 'Chris Hajjar', 'owner', 'Engineering'),
(2, 'user_a@company.com', 'Alice Smith', 'analyst', 'Finance'),
(3, 'user_b@company.com', 'Bob Jones', 'viewer', 'Sales'),
(4, 'carol@company.com', 'Carol White', 'analyst', 'Operations'),
(5, 'dave@company.com', 'Dave Brown', 'admin', 'Engineering'),
(6, 'eve@company.com', 'Eve Davis', 'viewer', 'Marketing'),
(7, 'frank@company.com', 'Frank Miller', 'analyst', 'Finance'),
(8, 'grace@company.com', 'Grace Lee', 'viewer', 'Sales'),
(9, 'hank@company.com', 'Hank Wilson', 'admin', 'Operations'),
(10, 'iris@company.com', 'Iris Taylor', 'analyst', 'Engineering');

-- Products
INSERT IGNORE INTO products (id, name, sku, price, category, stock_qty) VALUES
(1, 'Widget Pro', 'WGT-001', 29.99, 'Widgets', 150),
(2, 'Widget Basic', 'WGT-002', 9.99, 'Widgets', 500),
(3, 'Gadget X', 'GDG-001', 149.99, 'Gadgets', 75),
(4, 'Gadget Mini', 'GDG-002', 49.99, 'Gadgets', 200),
(5, 'Service Plan A', 'SVC-001', 99.00, 'Services', 999),
(6, 'Service Plan B', 'SVC-002', 199.00, 'Services', 999),
(7, 'Accessory Pack', 'ACC-001', 19.99, 'Accessories', 300),
(8, 'Premium Bundle', 'BDL-001', 249.99, 'Bundles', 50),
(9, 'Starter Kit', 'KIT-001', 39.99, 'Kits', 120),
(10, 'Enterprise License', 'LIC-001', 999.00, 'Licenses', 999);

-- Orders
INSERT IGNORE INTO orders (id, user_id, product_id, quantity, total, status) VALUES
(1, 2, 1, 3, 89.97, 'completed'),
(2, 3, 2, 10, 99.90, 'completed'),
(3, 2, 3, 1, 149.99, 'shipped'),
(4, 4, 5, 2, 198.00, 'pending'),
(5, 3, 4, 5, 249.95, 'completed'),
(6, 6, 7, 4, 79.96, 'shipped'),
(7, 7, 8, 1, 249.99, 'pending'),
(8, 2, 10, 1, 999.00, 'completed'),
(9, 8, 9, 3, 119.97, 'shipped'),
(10, 5, 6, 1, 199.00, 'completed');

-- Invoices
INSERT IGNORE INTO invoices (id, order_id, user_id, amount, status, due_date) VALUES
(1, 1, 2, 89.97, 'paid', '2025-02-01'),
(2, 2, 3, 99.90, 'paid', '2025-02-15'),
(3, 3, 2, 149.99, 'unpaid', '2025-03-01'),
(4, 4, 4, 198.00, 'unpaid', '2025-03-15'),
(5, 5, 3, 249.95, 'paid', '2025-01-30'),
(6, 6, 6, 79.96, 'unpaid', '2025-04-01'),
(7, 7, 7, 249.99, 'unpaid', '2025-04-15'),
(8, 8, 2, 999.00, 'paid', '2025-01-15'),
(9, 9, 8, 119.97, 'unpaid', '2025-03-30'),
(10, 10, 5, 199.00, 'paid', '2025-02-28');

-- Reports
INSERT IGNORE INTO reports (id, title, report_type, content, generated_by) VALUES
(1, 'Q4 2024 Revenue Summary', 'financial', 'Total revenue: $2.5M. Growth: 15% QoQ.', 1),
(2, 'Monthly Sales Report - Jan 2025', 'sales', 'Top product: Widget Pro. Units sold: 450.', 2),
(3, 'Inventory Audit - Feb 2025', 'operations', 'Stock levels healthy. 3 SKUs below reorder threshold.', 4),
(4, 'Customer Satisfaction Survey', 'marketing', 'NPS: 72. Top complaint: shipping delays.', 6),
(5, 'Engineering Sprint Retrospective', 'engineering', 'Velocity: 42 points. 2 carry-over stories.', 5),
(6, 'Quarterly Forecast - Q1 2025', 'financial', 'Projected revenue: $2.8M. New customers: 120.', 7),
(7, 'Churn Analysis - Jan 2025', 'analytics', 'Churn rate: 3.2%. Primary reason: pricing.', 2),
(8, 'Product Roadmap Update', 'engineering', 'Gadget X v2 launch: March 2025. Widget redesign: Q2.', 1),
(9, 'Compliance Audit Results', 'legal', 'SOC 2 Type II: passed. 2 minor findings.', 9),
(10, 'Marketing Campaign Results', 'marketing', 'Email campaign CTR: 4.2%. Social reach: 150K.', 6);
"""


def main():
    print(f"Connecting to MariaDB at {MARIADB_HOST}:{MARIADB_PORT}...")
    conn = get_connection()
    cursor = conn.cursor()

    print("Creating tables...")
    for statement in SCHEMA.split(";"):
        statement = statement.strip()
        if statement and not statement.startswith("--"):
            cursor.execute(statement)

    print("Seeding data...")
    for statement in SEED_DATA.split(";"):
        statement = statement.strip()
        if statement and not statement.startswith("--"):
            try:
                cursor.execute(statement)
            except mariadb.IntegrityError:
                pass  # IGNORE duplicates

    conn.commit()
    cursor.close()
    conn.close()
    print("Done! MariaDB seeded successfully.")


if __name__ == "__main__":
    main()
