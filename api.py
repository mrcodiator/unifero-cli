"""FastAPI server wrapper for the Unifero CLI tools.

Expose a small HTTP API that accepts the same JSON body shapes as the CLI
and delegates to `tools.unifero.UniferoTool.process_request`.

Endpoints:
- GET /health -> basic liveness
- POST /process -> accept JSON body and return the same output as the CLI

Run with: uvicorn api:app --reload
"""
from typing import Any, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

from tools.unifero import UniferoTool

app = FastAPI(title="unifero-cli API")


class ProcessRequest(BaseModel):
    mode: str
    # allow arbitrary extra fields - we'll accept whatever UniferoTool expects
    model_config = ConfigDict(extra="allow")


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok"}


@app.post("/process")
def process(request: ProcessRequest) -> Any:
    params = request.dict()
    try:
        tool = UniferoTool()
        out = tool.process_request(params)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # for unexpected errors, return 500 with message
        raise HTTPException(status_code=500, detail=str(e))
    return out
