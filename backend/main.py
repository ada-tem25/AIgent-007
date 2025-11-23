import os
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # récupère le port Cloud Run
    uvicorn.run(app, host="0.0.0.0", port=port)
