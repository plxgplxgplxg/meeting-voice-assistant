import importlib.util
from pathlib import Path
from types import ModuleType

import yaml

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = BACKEND_ROOT / "scripts" / "export_openapi.py"


def load_exporter() -> ModuleType:
    spec = importlib.util.spec_from_file_location("export_openapi", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_specification_matches_the_application() -> None:
    exporter = load_exporter()
    committed = yaml.safe_load(exporter.SPEC_PATH.read_text(encoding="utf-8"))
    assert committed == exporter.build_spec(), (
        "docs/04-design/api-specification.yaml is out of date; run "
        "`python scripts/export_openapi.py` in backend-api"
    )


def test_internal_agent_routes_are_not_part_of_the_public_contract() -> None:
    exporter = load_exporter()
    paths = exporter.build_spec()["paths"]
    assert not [path for path in paths if path.startswith("/internal")]
    assert "/api/v1/meetings/{meeting_id}/assistant/turns" in paths
