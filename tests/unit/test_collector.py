from src.collectors.example_collector import ExampleCollector


def test_example_collector_returns_projects():
    collector = ExampleCollector()

    projects = collector.collect()

    assert len(projects) > 0


def test_example_collector_returns_required_fields():
    collector = ExampleCollector()

    projects = collector.collect()

    project = projects[0]

    assert "title" in project
    assert "description" in project
    assert "source" in project
    assert "source_url" in project


def test_example_collector_source_name():
    collector = ExampleCollector()

    assert collector.get_source_name() == "Example Source"
