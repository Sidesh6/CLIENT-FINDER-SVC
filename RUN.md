# Start the FastAPI server
uvicorn src.api.main:app --reload --port 8000

# Open Web Dashboard in browser:
http://127.0.0.1:8000/

# Open Swagger API Documentation:
http://127.0.0.1:8000/docs
