from agents.perf_test_generator import run_perf_test_generator


def test_stub_returns_placeholder_markdown(test_db):
    # Now that F6 is filled, with no spec resolvable we still produce SOMETHING.
    # With a truly empty story, the agent should return either an error or a
    # requirements-mode plan; just assert the shape.
    result = run_perf_test_generator(
        conn=test_db,
        job_id="test-job-1",
        file_path="anything.txt",
        content="short",
        file_hash="fakehash-stub",
        language="python",
        custom_prompt=None,
    )
    assert "markdown" in result
    assert "summary" in result
    assert "Perf" in result["markdown"] or "Performance" in result["markdown"] or "error" in result["summary"].lower()


def test_orchestrator_dispatches_perf_test_generator(test_db):
    from db.queries.jobs import create_job, get_job, get_job_results
    from db.queries.job_events import get_events
    from agents.orchestrator import run_analysis
    job_id = create_job(test_db, source_type="local",
                        source_ref="tests/fixtures/wave6a/petstore_openapi.yaml",
                        language="java",
                        features=["perf_test_generator"])
    run_analysis(test_db, job_id)
    job = get_job(test_db, job_id)
    assert job is not None
    assert job["status"] in ("completed", "failed"), f"unexpected status: {job['status']}"
    results = get_job_results(test_db, job_id) or {}
    events = get_events(test_db, job_id)
    assert len(events) > 0, "expected at least one job_events row for the dispatch"
    dispatch_trace = str(results) + " " + " ".join(str(e) for e in events)
    assert "perf_test_generator" in dispatch_trace, \
        f"dispatch did not produce a result for perf_test_generator: results={results!r} events={events!r}"


from agents.perf_test_generator import _detect_mode, _pick_framework


def test_detect_mode_prefix_wins():
    m = _detect_mode(file_path="anything.yaml",
                     content="openapi: 3.0.0\ninfo:{title:t,version:'0.1'}\npaths:{}",
                     custom_prompt="__mode__requirements\nthe story text")
    assert m == "requirements"


def test_detect_mode_yaml_source_is_spec():
    m = _detect_mode(file_path="openapi.yaml",
                     content="openapi: 3.0.0\ninfo:{title:t,version:'0.1'}\npaths:{}",
                     custom_prompt=None)
    assert m == "spec"


def test_detect_mode_plain_txt_is_requirements():
    m = _detect_mode(file_path="story.txt",
                     content="as a user I want to x",
                     custom_prompt=None)
    assert m == "requirements"


def test_detect_mode_openapi_prefix_is_spec():
    m = _detect_mode(file_path="story.txt",
                     content="",
                     custom_prompt="__openapi_spec__\nopenapi: 3.0.0\ninfo:{title:t,version:'0.1'}\npaths:{}")
    assert m == "spec"


def test_pick_framework_gatling_triggers():
    for lang in ("java", "scala", "gatling", "JAVA", " Scala "):
        assert _pick_framework(lang) == "gatling"


def test_pick_framework_default_is_jmeter():
    for lang in (None, "", "python", "typescript", "anything"):
        assert _pick_framework(lang) == "jmeter"


import os as _os_lib
from unittest.mock import patch, MagicMock


_CANNED_JMETER = '''```xml
<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0">
  <hashTree>
    <TestPlan testname="petstore"/>
    <hashTree>
      <Arguments testname="User Defined Variables">
        <elementProp name="baseUrl" elementType="Argument"><stringProp name="Argument.name">baseUrl</stringProp><stringProp name="Argument.value">https://api.example.test</stringProp></elementProp>
      </Arguments>
      <hashTree/>
      <ThreadGroup testname="Load" enabled="true">
        <stringProp name="ThreadGroup.num_threads">50</stringProp>
        <stringProp name="ThreadGroup.ramp_time">60</stringProp>
        <stringProp name="ThreadGroup.duration">300</stringProp>
      </ThreadGroup>
      <hashTree>
        <TransactionController testname="list pets"/>
        <hashTree>
          <HTTPSamplerProxy testname="GET /pets"/>
          <hashTree>
            <ResponseAssertion testname="2xx"/>
            <ConstantTimer><stringProp name="ConstantTimer.delay">500</stringProp></ConstantTimer>
          </hashTree>
        </hashTree>
        <TransactionController testname="create pet"/>
        <hashTree>
          <HTTPSamplerProxy testname="POST /pets"/>
          <hashTree/>
        </hashTree>
        <TransactionController testname="get pet"/>
        <hashTree>
          <HTTPSamplerProxy testname="GET /pets/${petId}"/>
          <hashTree/>
        </hashTree>
      </hashTree>
      <SummaryReport testname="Summary"/>
      <hashTree/>
      <ViewResultsTree testname="View Results Tree"/>
      <hashTree/>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
```'''


_CANNED_GATLING = '''```scala
import io.gatling.core.Predef._
import io.gatling.http.Predef._
import scala.concurrent.duration._

class LoadTest extends Simulation {
  val httpProtocol = http.baseUrl("${baseUrl}")
  val scn = scenario("LoadTest")
    .exec(http("list pets").get("/pets").check(status.in(200 to 299))).pause(500.milliseconds)
    .exec(http("create pet").post("/pets").body(StringBody("""{"name":"Rex"}""")).asJson.check(status.in(200 to 299))).pause(500.milliseconds)
    .exec(http("get pet").get("/pets/1").check(status.in(200 to 299))).pause(500.milliseconds)
  setUp(
    scn.inject(rampUsersPerSec(1) to (50) during (60 seconds))
       .protocols(httpProtocol)
  ).maxDuration(300 seconds)
}
```'''


def _project_root():
    import pathlib
    cur = pathlib.Path(__file__).resolve()
    for parent in cur.parents:
        if (parent / "pytest.ini").exists():
            return parent
    return pathlib.Path.cwd()


def test_spec_mode_jmeter_writes_jmx(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    spec_content = (_project_root() / "tests/fixtures/wave6a/petstore_openapi.yaml").read_text(encoding="utf-8")
    with patch("agents.perf_test_generator.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = _CANNED_JMETER
        mock_cls.return_value = mock_agent
        result = run_perf_test_generator(
            conn=test_db, job_id="j1",
            file_path="openapi.yaml", content=spec_content,
            file_hash="h1", language="python", custom_prompt=None,
        )
    assert result["output_path"].endswith("plan.jmx")
    assert _os_lib.path.isfile(result["output_path"])
    body = open(result["output_path"], "r", encoding="utf-8").read()
    assert "<jmeterTestPlan" in body
    assert "HTTPSamplerProxy" in body


def test_spec_mode_gatling_writes_scala(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    spec_content = (_project_root() / "tests/fixtures/wave6a/petstore_openapi.yaml").read_text(encoding="utf-8")
    with patch("agents.perf_test_generator.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = _CANNED_GATLING
        mock_cls.return_value = mock_agent
        result = run_perf_test_generator(
            conn=test_db, job_id="j2",
            file_path="openapi.yaml", content=spec_content,
            file_hash="h2", language="scala", custom_prompt=None,
        )
    assert result["output_path"].endswith("Simulation.scala")
    body = open(result["output_path"], "r", encoding="utf-8").read()
    assert "class LoadTest" in body
    assert "setUp" in body


def test_requirements_mode_uses_story_text(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    story = (_project_root() / "tests/fixtures/wave6a/order_story.txt").read_text(encoding="utf-8")
    with patch("agents.perf_test_generator.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = _CANNED_JMETER
        mock_cls.return_value = mock_agent
        result = run_perf_test_generator(
            conn=test_db, job_id="j3",
            file_path="order_story.txt", content=story,
            file_hash="h3", language=None,
            custom_prompt="__mode__requirements\n" + story,
        )
    assert result["output_path"].endswith("plan.jmx")
    assert "requirements" in result["summary"].lower() or "story" in result["summary"].lower()


def test_empty_llm_response_returns_error(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    spec_content = (_project_root() / "tests/fixtures/wave6a/petstore_openapi.yaml").read_text(encoding="utf-8")
    with patch("agents.perf_test_generator.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = "I cannot comply."
        mock_cls.return_value = mock_agent
        result = run_perf_test_generator(
            conn=test_db, job_id="j4",
            file_path="openapi.yaml", content=spec_content,
            file_hash="h4", language="python", custom_prompt=None,
        )
    assert result.get("output_path") is None
    low = result["summary"].lower()
    assert "empty" in low or "failed" in low or "error" in low
