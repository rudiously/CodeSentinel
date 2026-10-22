from pathlib import Path


def test_source_documents_exist() -> None:
    assert Path("Project.md").is_file()
    assert Path("Work.md").is_file()
