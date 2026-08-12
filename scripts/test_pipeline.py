from src.processors.cleaner import ProjectCleaner
from src.ai.extractor import ProjectExtractor


def main():
    raw_project = {
        "title": "AI Chatbot Development",
        "description": "  Build an AI chatbot using Python and LLMs.  ",
        "source": "example",
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


if __name__ == "__main__":
    main()