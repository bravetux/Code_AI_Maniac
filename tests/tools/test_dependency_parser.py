import pytest
from tools.dependency_parser import parse_dependency_file, detect_dep_files


# ── Python ───────────────────────────────────────────────────────────────────

def test_parse_requirements_txt():
    content = "requests==2.25.1\nflask>=2.0.0\nboto3\nnumpy==1.21.0\n"
    result = parse_dependency_file("requirements.txt", content)
    assert result["ecosystem"] == "PyPI"
    assert len(result["packages"]) == 4
    req = next(p for p in result["packages"] if p["name"] == "requests")
    assert req["version"] == "2.25.1"
    boto = next(p for p in result["packages"] if p["name"] == "boto3")
    assert boto["version"] is None  # unpinned


def test_parse_requirements_txt_with_comments():
    content = "# Core deps\nrequests==2.25.1\n  # another comment\n-e git+https://...\n"
    result = parse_dependency_file("requirements.txt", content)
    assert len(result["packages"]) == 1
    assert result["packages"][0]["name"] == "requests"


def test_parse_pyproject_toml():
    content = '''
[project]
dependencies = [
    "requests>=2.25.1",
    "flask==2.0.0",
]
'''
    result = parse_dependency_file("pyproject.toml", content)
    assert result["ecosystem"] == "PyPI"
    assert len(result["packages"]) == 2


# ── JavaScript ───────────────────────────────────────────────────────────────

def test_parse_package_json():
    content = '''{
  "dependencies": {"express": "^4.18.0", "lodash": "4.17.21"},
  "devDependencies": {"jest": "^29.0.0"}
}'''
    result = parse_dependency_file("package.json", content)
    assert result["ecosystem"] == "npm"
    assert len(result["packages"]) == 3


# ── Java ─────────────────────────────────────────────────────────────────────

def test_parse_pom_xml():
    content = '''<project>
  <dependencies>
    <dependency>
      <groupId>org.springframework</groupId>
      <artifactId>spring-core</artifactId>
      <version>5.3.20</version>
    </dependency>
  </dependencies>
</project>'''
    result = parse_dependency_file("pom.xml", content)
    assert result["ecosystem"] == "Maven"
    assert len(result["packages"]) == 1
    assert result["packages"][0]["name"] == "org.springframework:spring-core"
    assert result["packages"][0]["version"] == "5.3.20"


def test_parse_build_gradle():
    content = """dependencies {
    implementation 'org.springframework:spring-core:5.3.20'
    testImplementation "junit:junit:4.13.2"
}"""
    result = parse_dependency_file("build.gradle", content)
    assert result["ecosystem"] == "Maven"
    assert len(result["packages"]) == 2


# ── C# ───────────────────────────────────────────────────────────────────────

def test_parse_csproj():
    content = '''<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="13.0.1" />
    <PackageReference Include="Serilog" Version="3.0.0" />
  </ItemGroup>
</Project>'''
    result = parse_dependency_file("MyApp.csproj", content)
    assert result["ecosystem"] == "NuGet"
    assert len(result["packages"]) == 2


# ── Go ───────────────────────────────────────────────────────────────────────

def test_parse_go_mod():
    content = """module example.com/myapp

go 1.21

require (
\tgithub.com/gin-gonic/gin v1.9.1
\tgolang.org/x/net v0.15.0
)"""
    result = parse_dependency_file("go.mod", content)
    assert result["ecosystem"] == "Go"
    assert len(result["packages"]) == 2
    gin = next(p for p in result["packages"] if "gin" in p["name"])
    assert gin["version"] == "v1.9.1"


# ── Rust ─────────────────────────────────────────────────────────────────────

def test_parse_cargo_toml():
    content = '''[dependencies]
serde = "1.0"
tokio = { version = "1.32", features = ["full"] }
'''
    result = parse_dependency_file("Cargo.toml", content)
    assert result["ecosystem"] == "crates.io"
    assert len(result["packages"]) == 2


# ── C/C++ ────────────────────────────────────────────────────────────────────

def test_parse_conanfile_txt():
    content = """[requires]
boost/1.82.0
openssl/3.1.1
"""
    result = parse_dependency_file("conanfile.txt", content)
    assert result["ecosystem"] == "conan"
    assert len(result["packages"]) == 2


def test_parse_vcpkg_json():
    content = '''{
  "dependencies": ["zlib", "openssl", "boost-filesystem"]
}'''
    result = parse_dependency_file("vcpkg.json", content)
    assert result["ecosystem"] == "vcpkg"
    assert len(result["packages"]) == 3


# ── Unknown file ─────────────────────────────────────────────────────────────

def test_parse_unknown_file():
    result = parse_dependency_file("unknown.xyz", "something")
    assert result["ecosystem"] == "unknown"
    assert result["packages"] == []


# ── Auto-discovery ───────────────────────────────────────────────────────────

def test_detect_dep_files_in_directory(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests==2.25.1\n")
    (tmp_path / "package.json").write_text('{"dependencies":{}}\n')
    (tmp_path / "main.py").write_text("print('hello')\n")  # not a dep file
    found = detect_dep_files(str(tmp_path))
    filenames = [f.split("/")[-1].split("\\")[-1] for f in found]
    assert "requirements.txt" in filenames
    assert "package.json" in filenames
    assert "main.py" not in filenames


def test_detect_dep_files_empty_dir(tmp_path):
    found = detect_dep_files(str(tmp_path))
    assert found == []
