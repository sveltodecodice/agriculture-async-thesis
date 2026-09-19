from pathlib import Path


SERVICES = (
    "ambient_sensor",
    "terrain_sensor",
    "plantation_sensor",
    "seeder",
    "irrigator",
    "harvester",
    "camp_manager",
    "dashboard",
)


def test_every_service_uses_standard_dockerfile_name():
    for service in SERVICES:
        assert (Path(service) / "Dockerfile").is_file()
        assert not (Path(service) / "dockerfile").exists()


def test_runtime_dependencies_do_not_include_unused_paho_client():
    for service in SERVICES:
        requirements = (Path(service) / "requirements.txt").read_text(encoding="utf-8").lower()
        assert "paho-mqtt" not in requirements


def test_every_pytest_file_can_import_src_using_project_convention():
    for service in SERVICES:
        for test_file in (Path(service) / "tests").glob("test_*.py"):
            source = test_file.read_text(encoding="utf-8")
            assert 'sys.path.append("src")' in source, test_file
