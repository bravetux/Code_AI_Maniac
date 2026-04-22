import json
from tools.openapi_parser import parse
from tools.postman_emitter import build_collection


def _load_petstore():
    with open("tests/fixtures/wave6a/petstore_openapi.yaml", "r", encoding="utf-8") as fh:
        return parse(fh.read())


def test_collection_has_postman_schema():
    spec = _load_petstore()
    col = build_collection(spec)
    assert col["info"]["schema"].startswith("https://schema.getpostman.com/json/collection/v2.1")
    assert col["info"]["name"] == "Petstore"


def test_one_item_per_operation():
    spec = _load_petstore()
    col = build_collection(spec)
    assert len(col["item"]) == 3


def test_path_params_use_postman_variable_syntax():
    spec = _load_petstore()
    col = build_collection(spec)
    get_by_id = next(i for i in col["item"] if i["name"] == "GET /pets/{petId}")
    assert ":petId" in get_by_id["request"]["url"]["raw"]
    names = [v["key"] for v in get_by_id["request"]["url"].get("variable", [])]
    assert "petId" in names


def test_request_body_uses_example_from_spec():
    spec = _load_petstore()
    col = build_collection(spec)
    post = next(i for i in col["item"] if i["name"] == "POST /pets")
    body_raw = post["request"]["body"]["raw"]
    parsed = json.loads(body_raw)
    assert parsed.get("name") == "Rex"
    assert parsed.get("tag") == "dog"


def test_every_item_has_status_2xx_assertion():
    spec = _load_petstore()
    col = build_collection(spec)
    for item in col["item"]:
        scripts = [e for e in item.get("event", []) if e.get("listen") == "test"]
        assert scripts, f"no test script on {item['name']}"
        exec_body = "\n".join(scripts[0]["script"]["exec"])
        assert "pm.test" in exec_body
        assert "2" in exec_body


def test_base_url_overrides_spec_server():
    spec = _load_petstore()
    col = build_collection(spec, base_url="https://override.test")
    variables = {v["key"]: v["value"] for v in col.get("variable", [])}
    assert variables["baseUrl"] == "https://override.test"


def test_empty_spec_returns_empty_collection():
    col = build_collection({"openapi": "3.0.0", "info": {"title": "empty", "version": "0"}, "paths": {}})
    assert col["item"] == []
