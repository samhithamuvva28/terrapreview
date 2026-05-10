import os
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from fastapi import FastAPI, HTTPException
from google.cloud import firestore
from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PreviewEvent(BaseModel):
    preview_id: str = Field(..., description="Preview identifier such as pr-123.")
    status: str = Field(..., description="Preview lifecycle state.")
    pr_number: str | None = None
    git_branch: str | None = None
    git_sha: str | None = None
    preview_url: str | None = None
    image_uri: str | None = None
    environment: str | None = None
    app_name: str | None = None
    event_type: str | None = None
    closure_reason: str | None = None
    updated_at: str | None = None


class PreviewRecord(BaseModel):
    preview_id: str
    status: str
    pr_number: str | None = None
    git_branch: str | None = None
    git_sha: str | None = None
    preview_url: str | None = None
    image_uri: str | None = None
    environment: str | None = None
    app_name: str | None = None
    event_type: str | None = None
    closure_reason: str | None = None
    created_at: str
    updated_at: str


class PreviewStore:
    def list_previews(self) -> list[PreviewRecord]:
        raise NotImplementedError

    def get_preview(self, preview_id: str) -> PreviewRecord | None:
        raise NotImplementedError

    def upsert_preview(self, event: PreviewEvent) -> PreviewRecord:
        raise NotImplementedError


def merge_preview_event(existing: dict[str, Any], event: PreviewEvent) -> dict[str, Any]:
    timestamp = event.updated_at or utc_now()
    destroyed = event.status == "destroyed"

    payload = {
        "preview_id": event.preview_id,
        "status": event.status,
        "pr_number": event.pr_number if event.pr_number is not None else existing.get("pr_number"),
        "git_branch": event.git_branch if event.git_branch is not None else existing.get("git_branch"),
        "git_sha": event.git_sha if event.git_sha is not None else existing.get("git_sha"),
        "preview_url": event.preview_url if event.preview_url is not None else existing.get("preview_url"),
        "image_uri": event.image_uri if event.image_uri is not None else existing.get("image_uri"),
        "environment": event.environment if event.environment is not None else existing.get("environment"),
        "app_name": event.app_name if event.app_name is not None else existing.get("app_name"),
        "event_type": event.event_type if event.event_type is not None else existing.get("event_type"),
        "closure_reason": event.closure_reason if event.closure_reason is not None else existing.get("closure_reason"),
        "created_at": existing.get("created_at", timestamp),
        "updated_at": timestamp,
    }

    if destroyed:
        payload["preview_url"] = None

    return payload


class InMemoryPreviewStore(PreviewStore):
    def __init__(self) -> None:
        self._items: dict[str, PreviewRecord] = {}
        self._lock = Lock()

    def list_previews(self) -> list[PreviewRecord]:
        with self._lock:
            return sorted(self._items.values(), key=lambda item: item.updated_at, reverse=True)

    def get_preview(self, preview_id: str) -> PreviewRecord | None:
        with self._lock:
            return self._items.get(preview_id)

    def upsert_preview(self, event: PreviewEvent) -> PreviewRecord:
        with self._lock:
            existing = self._items.get(event.preview_id)
            existing_data = existing.model_dump() if existing else {}
            record = PreviewRecord(**merge_preview_event(existing_data, event))
            self._items[event.preview_id] = record
            return record


class FirestorePreviewStore(PreviewStore):
    def __init__(self, project_id: str, collection_name: str) -> None:
        self._client = firestore.Client(project=project_id)
        self._collection = self._client.collection(collection_name)

    @staticmethod
    def _to_record(data: dict[str, Any]) -> PreviewRecord:
        return PreviewRecord(**data)

    def list_previews(self) -> list[PreviewRecord]:
        documents = self._collection.order_by("updated_at", direction=firestore.Query.DESCENDING).stream()
        return [self._to_record(document.to_dict()) for document in documents]

    def get_preview(self, preview_id: str) -> PreviewRecord | None:
        document = self._collection.document(preview_id).get()
        if not document.exists:
            return None
        return self._to_record(document.to_dict())

    def upsert_preview(self, event: PreviewEvent) -> PreviewRecord:
        document_ref = self._collection.document(event.preview_id)
        existing_document = document_ref.get()
        existing = existing_document.to_dict() if existing_document.exists else {}
        payload = merge_preview_event(existing, event)
        document_ref.set(payload)
        return self._to_record(payload)


def build_store() -> tuple[PreviewStore, str]:
    backend = os.getenv("TERRAPREVIEW_METADATA_BACKEND", "memory").strip().lower()
    if backend == "firestore":
        project_id = os.getenv("TERRAPREVIEW_GCP_PROJECT", "").strip()
        collection_name = os.getenv("TERRAPREVIEW_FIRESTORE_COLLECTION", "preview_records").strip()
        if not project_id:
            raise RuntimeError("TERRAPREVIEW_GCP_PROJECT must be set when using Firestore metadata backend.")
        return FirestorePreviewStore(project_id=project_id, collection_name=collection_name), backend
    return InMemoryPreviewStore(), backend


store, metadata_backend = build_store()

app = FastAPI(title="TerraPreview Control Plane")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "TerraPreview control plane running"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "metadata_backend": metadata_backend}


@app.get("/previews", response_model=list[PreviewRecord])
def list_previews() -> list[PreviewRecord]:
    return store.list_previews()


@app.get("/previews/{preview_id}", response_model=PreviewRecord)
def get_preview(preview_id: str) -> PreviewRecord:
    preview = store.get_preview(preview_id)
    if preview is None:
        raise HTTPException(status_code=404, detail="Preview not found")
    return preview


@app.post("/previews/events", response_model=PreviewRecord)
def record_preview_event(event: PreviewEvent) -> PreviewRecord:
    return store.upsert_preview(event)
