from src.processors.cleaner import ProjectCleaner
from src.ai.extractor import ProjectExtractor


def main():

    raw_project = {
        "title": "AI Chatbot Development",

        "description": (
            "  Build an AI chatbot using Python, "
            "FastAPI and RAG.  "
        ),

        "source": "Example Source",

        "source_url": "https://example.com/project/123",

        "client_name": "Example Client",

        "budget": 2000,

        "currency": "USD",

        "project_type": "AI Development",

        "skills": [
            "Python",
            "FastAPI",
            "RAG"
        ]
    }

    print("RAW PROJECT")
    print(raw_project)

    cleaner = ProjectCleaner()

    cleaned_project = cleaner.clean(raw_project)

    print("\nCLEANED PROJECT")
    print(cleaned_project)

    extractor = ProjectExtractor()

    extracted_project = extractor.extract(cleaned_project)

    print("\nEXTRACTED PROJECT")
    print(extracted_project)

    print("\nPROJECT TYPE:")
    print(type(extracted_project))

    print("\nPROJECT TITLE:")
    print(extracted_project.title)

    print("\nPROJECT URL:")
    print(extracted_project.source_url)


if __name__ == "__main__":
    main()