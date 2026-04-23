from tools.ddl_parser import parse_ddl


def test_parse_create_table_basic():
    ddl = """
    CREATE TABLE users (
        id INT PRIMARY KEY,
        email VARCHAR(255) NOT NULL UNIQUE,
        tenant_id INT NOT NULL
    );
    """
    result = parse_ddl(ddl)
    assert len(result["tables"]) == 1
    tbl = result["tables"][0]
    assert tbl["name"] == "users"
    cols = {c["name"]: c for c in tbl["columns"]}
    assert cols["id"]["pk"] is True
    assert cols["email"]["nullable"] is False
    assert cols["tenant_id"]["type"].upper() == "INT"


def test_parse_foreign_key():
    ddl = """
    CREATE TABLE orders (
        id INT PRIMARY KEY,
        user_id INT REFERENCES users(id)
    );
    """
    result = parse_ddl(ddl)
    tbl = result["tables"][0]
    user_col = next(c for c in tbl["columns"] if c["name"] == "user_id")
    assert user_col.get("fk") == {"ref_table": "users", "ref_col": "id"}


def test_parse_rls_policy():
    ddl = """
    CREATE POLICY tenant_isolation ON orders
        FOR SELECT
        USING (tenant_id = current_setting('app.tenant_id')::int);
    """
    result = parse_ddl(ddl)
    pol = result["policies"][0]
    assert pol["name"] == "tenant_isolation"
    assert pol["table"] == "orders"
    assert pol["command"].upper() == "SELECT"
    assert "tenant_id" in pol["using"]


def test_parse_multiple_tables():
    ddl = """
    CREATE TABLE a (id INT PRIMARY KEY);
    CREATE TABLE b (id INT PRIMARY KEY, a_id INT REFERENCES a(id));
    """
    result = parse_ddl(ddl)
    assert [t["name"] for t in result["tables"]] == ["a", "b"]


def test_parse_unsupported_statements_are_skipped():
    ddl = """
    CREATE TRIGGER audit_insert ...;
    CREATE DOMAIN age_t AS INT CHECK (VALUE >= 0);
    CREATE TABLE ok (id INT PRIMARY KEY);
    """
    result = parse_ddl(ddl)
    assert len(result["tables"]) == 1
    assert result["tables"][0]["name"] == "ok"


def test_parse_empty_input():
    result = parse_ddl("")
    assert result == {"tables": [], "views": [], "policies": []}


def test_parse_partial_on_bad_ddl():
    ddl = """
    CREATE TABLE good (id INT);
    CREATE TABLE bad (
    CREATE TABLE another (id INT);
    """
    result = parse_ddl(ddl)
    assert any(t["name"] == "good" for t in result["tables"])
