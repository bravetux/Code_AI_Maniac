CREATE TABLE tenants (
    id INT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE users (
    id INT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    tenant_id INT NOT NULL REFERENCES tenants(id)
);

CREATE TABLE orders (
    id INT PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id),
    tenant_id INT NOT NULL REFERENCES tenants(id),
    total NUMERIC(12,2) NOT NULL,
    placed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE POLICY tenant_isolation ON orders
    FOR SELECT
    USING (tenant_id = current_setting('app.tenant_id')::int);
