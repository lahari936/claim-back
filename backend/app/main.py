from fastapi import FastAPI

app = FastAPI(title="ClaimBack")


@app.get("/health")
def health():
    return {"status": "ok"}
