from fastapi import FastAPI


app = FastAPI(title="TerraPreview Phase 1")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "TerraPreview Phase 1 running"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
