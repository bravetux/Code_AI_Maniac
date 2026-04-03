from db.schema import init_schema, TABLE_NAMES


def test_all_tables_created(test_db):
    result = test_db.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
    ).fetchall()
    created = {row[0] for row in result}
    assert TABLE_NAMES == created


def test_idempotent_init(test_db):
    from db.schema import init_schema
    init_schema(test_db)  # second call should not raise
