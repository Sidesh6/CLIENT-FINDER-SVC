from src.ai.extractor import ProjectExtractor
from src.collectors.example_collector import ExampleCollector
from src.processors.cleaner import ProjectCleaner


def main():

    # 1. Collect
    collector = ExampleCollector()

    raw_projects = collector.collect()

    print(f"Collected {len(raw_projects)} projects")

    # 2. Clean
    cleaner = ProjectCleaner()

    cleaned_projects = cleaner.clean_many(raw_projects)

    print(f"Cleaned {len(cleaned_projects)} projects")

    # 3. Extract and validate
    extractor = ProjectExtractor()

    projects = []

    for project in cleaned_projects:
        extracted_project = extractor.extract(project)
        projects.append(extracted_project)

    # 4. Display
    print("\nVALIDATED PROJECTS")

    for project in projects:

        print("\n------------------------------")

        print(f"Title: {project.title}")
        print(f"Source: {project.source}")
        print(f"Budget: {project.budget} {project.currency}")
        print(f"Skills: {project.skills}")
        print(f"URL: {project.source_url}")


if __name__ == "__main__":
    main()