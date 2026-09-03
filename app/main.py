"""HTTP wrapper around the classifier, delivered to the client as a service."""

from fastapi import FastAPI
from pydantic import BaseModel

from app.classifier import classify

app = FastAPI(title="Strataxis Client Signal Classifier", version="1.0.0")


class Message(BaseModel):
    text: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/classify")
def classify_message(message: Message) -> dict:
    result = classify(message.text)
    return {"input": message.text, **result}
