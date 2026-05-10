import os
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
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
def read_root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard", status_code=302)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    return """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>TerraPreview Dashboard</title>
    <style>
      :root {
        --bg: #f7f3ea;
        --panel: #fffaf2;
        --panel-strong: #fff;
        --border: #d9c9a8;
        --text: #1f1d19;
        --muted: #6c6558;
        --accent: #b8552f;
        --accent-soft: #f3d9c9;
        --good: #2f6b45;
        --warn: #8f5a14;
        --bad: #973b3b;
        --shadow: 0 18px 45px rgba(76, 53, 24, 0.12);
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        font-family: Georgia, "Times New Roman", serif;
        color: var(--text);
        background:
          radial-gradient(circle at top left, rgba(184, 85, 47, 0.15), transparent 30%),
          radial-gradient(circle at bottom right, rgba(47, 107, 69, 0.12), transparent 28%),
          linear-gradient(180deg, #f5efe3 0%, var(--bg) 100%);
      }

      main {
        width: min(1200px, calc(100% - 32px));
        margin: 0 auto;
        padding: 40px 0 56px;
      }

      .hero {
        display: grid;
        gap: 18px;
        margin-bottom: 26px;
      }

      .eyebrow {
        display: inline-flex;
        width: fit-content;
        padding: 7px 12px;
        border-radius: 999px;
        background: var(--accent-soft);
        color: var(--accent);
        font-size: 13px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }

      h1 {
        margin: 0;
        font-size: clamp(40px, 7vw, 76px);
        line-height: 0.94;
        letter-spacing: -0.04em;
      }

      .lede {
        margin: 0;
        max-width: 760px;
        color: var(--muted);
        font-size: 18px;
        line-height: 1.6;
      }

      .stats {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 14px;
        margin: 28px 0 24px;
      }

      .card,
      .stat {
        border: 1px solid var(--border);
        background: rgba(255, 250, 242, 0.92);
        border-radius: 24px;
        box-shadow: var(--shadow);
      }

      .stat {
        padding: 18px 20px;
      }

      .stat-label {
        color: var(--muted);
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }

      .stat-value {
        margin-top: 10px;
        font-size: 34px;
        line-height: 1;
      }

      .toolbar {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 16px;
      }

      .filters {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
      }

      button,
      select,
      input {
        font: inherit;
      }

      .control,
      .button {
        border: 1px solid var(--border);
        border-radius: 14px;
        background: var(--panel-strong);
        color: var(--text);
        padding: 10px 14px;
      }

      .button {
        cursor: pointer;
        background: linear-gradient(180deg, #fff8ef 0%, #f3dfca 100%);
      }

      .button:hover {
        transform: translateY(-1px);
      }

      .table-shell {
        overflow: hidden;
      }

      table {
        width: 100%;
        border-collapse: collapse;
      }

      th,
      td {
        padding: 16px 18px;
        border-top: 1px solid rgba(217, 201, 168, 0.6);
        vertical-align: top;
        text-align: left;
      }

      thead th {
        border-top: 0;
        color: var(--muted);
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }

      tbody tr:hover {
        background: rgba(255, 255, 255, 0.65);
      }

      .preview-id {
        font-weight: 700;
        font-size: 18px;
      }

      .meta {
        color: var(--muted);
        font-size: 13px;
        line-height: 1.5;
      }

      .status {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 10px;
        border-radius: 999px;
        font-size: 13px;
        border: 1px solid transparent;
        text-transform: capitalize;
      }

      .status-ready {
        color: var(--good);
        background: rgba(47, 107, 69, 0.12);
        border-color: rgba(47, 107, 69, 0.24);
      }

      .status-destroyed {
        color: var(--bad);
        background: rgba(151, 59, 59, 0.12);
        border-color: rgba(151, 59, 59, 0.22);
      }

      .status-other {
        color: var(--warn);
        background: rgba(143, 90, 20, 0.12);
        border-color: rgba(143, 90, 20, 0.24);
      }

      .link {
        color: var(--accent);
        text-decoration: none;
      }

      .link:hover {
        text-decoration: underline;
      }

      .empty {
        padding: 28px 24px 34px;
        color: var(--muted);
      }

      .footer-note {
        margin-top: 16px;
        color: var(--muted);
        font-size: 14px;
      }

      @media (max-width: 900px) {
        .stats {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        table,
        thead,
        tbody,
        tr,
        th,
        td {
          display: block;
        }

        thead {
          display: none;
        }

        tbody tr {
          border-top: 1px solid rgba(217, 201, 168, 0.6);
          padding: 6px 0;
        }

        td {
          border-top: 0;
          padding: 10px 18px;
        }

        td::before {
          content: attr(data-label);
          display: block;
          color: var(--muted);
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          margin-bottom: 4px;
        }
      }

      @media (max-width: 640px) {
        main {
          width: min(100% - 20px, 1200px);
          padding-top: 24px;
        }

        .stats {
          grid-template-columns: 1fr;
        }

        h1 {
          font-size: 42px;
        }
      }
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <span class="eyebrow">TerraPreview Control Plane</span>
        <h1>Preview environments with real lifecycle visibility.</h1>
        <p class="lede">
          Track every preview, see which pull requests are still live, and quickly spot records that drift away from real Cloud Run state.
        </p>
      </section>

      <section class="stats" aria-label="Preview summary">
        <article class="stat">
          <div class="stat-label">Total Records</div>
          <div class="stat-value" id="stat-total">0</div>
        </article>
        <article class="stat">
          <div class="stat-label">Ready</div>
          <div class="stat-value" id="stat-ready">0</div>
        </article>
        <article class="stat">
          <div class="stat-label">Destroyed</div>
          <div class="stat-value" id="stat-destroyed">0</div>
        </article>
        <article class="stat">
          <div class="stat-label">Merged Closures</div>
          <div class="stat-value" id="stat-merged">0</div>
        </article>
      </section>

      <section class="card table-shell">
        <div class="toolbar">
          <div class="filters">
            <input class="control" id="search" type="search" placeholder="Filter by preview, branch, PR, or SHA" />
            <select class="control" id="status-filter">
              <option value="all">All statuses</option>
              <option value="ready">Ready</option>
              <option value="destroyed">Destroyed</option>
            </select>
            <select class="control" id="closure-filter">
              <option value="all">All closures</option>
              <option value="merged">Merged</option>
              <option value="closed">Closed without merge</option>
              <option value="active">Active only</option>
            </select>
          </div>
          <button class="button" id="refresh-button" type="button">Refresh</button>
        </div>

        <table>
          <thead>
            <tr>
              <th>Preview</th>
              <th>Status</th>
              <th>Branch</th>
              <th>Updated</th>
              <th>Preview URL</th>
            </tr>
          </thead>
          <tbody id="preview-table"></tbody>
        </table>
        <div class="empty" id="empty-state" hidden>No previews match the current filters.</div>
      </section>

      <p class="footer-note" id="footer-note">Loading latest preview records…</p>
    </main>

    <script>
      const state = {
        previews: [],
      };

      const elements = {
        table: document.getElementById("preview-table"),
        empty: document.getElementById("empty-state"),
        footer: document.getElementById("footer-note"),
        search: document.getElementById("search"),
        statusFilter: document.getElementById("status-filter"),
        closureFilter: document.getElementById("closure-filter"),
        refreshButton: document.getElementById("refresh-button"),
        statTotal: document.getElementById("stat-total"),
        statReady: document.getElementById("stat-ready"),
        statDestroyed: document.getElementById("stat-destroyed"),
        statMerged: document.getElementById("stat-merged"),
      };

      function escapeHtml(value) {
        return String(value ?? "")
          .replaceAll("&", "&amp;")
          .replaceAll("<", "&lt;")
          .replaceAll(">", "&gt;")
          .replaceAll('"', "&quot;")
          .replaceAll("'", "&#39;");
      }

      function formatDate(value) {
        if (!value) return "Unknown";
        const parsed = new Date(value);
        if (Number.isNaN(parsed.getTime())) return value;
        return parsed.toLocaleString();
      }

      function statusClass(status) {
        if (status === "ready") return "status status-ready";
        if (status === "destroyed") return "status status-destroyed";
        return "status status-other";
      }

      function computeVisiblePreviews() {
        const query = elements.search.value.trim().toLowerCase();
        const status = elements.statusFilter.value;
        const closure = elements.closureFilter.value;

        return state.previews.filter((preview) => {
          if (status !== "all" && preview.status !== status) {
            return false;
          }

          if (closure === "merged" && preview.closure_reason !== "merged") {
            return false;
          }

          if (closure === "closed" && preview.closure_reason !== "closed") {
            return false;
          }

          if (closure === "active" && preview.status !== "ready") {
            return false;
          }

          if (!query) {
            return true;
          }

          const haystack = [
            preview.preview_id,
            preview.pr_number,
            preview.git_branch,
            preview.git_sha,
            preview.status,
            preview.closure_reason,
          ]
            .filter(Boolean)
            .join(" ")
            .toLowerCase();

          return haystack.includes(query);
        });
      }

      function renderStats(previews) {
        const total = previews.length;
        const ready = previews.filter((preview) => preview.status === "ready").length;
        const destroyed = previews.filter((preview) => preview.status === "destroyed").length;
        const merged = previews.filter((preview) => preview.closure_reason === "merged").length;

        elements.statTotal.textContent = String(total);
        elements.statReady.textContent = String(ready);
        elements.statDestroyed.textContent = String(destroyed);
        elements.statMerged.textContent = String(merged);
      }

      function renderTable() {
        const previews = computeVisiblePreviews();
        renderStats(state.previews);

        if (previews.length === 0) {
          elements.table.innerHTML = "";
          elements.empty.hidden = false;
          return;
        }

        elements.empty.hidden = true;
        elements.table.innerHTML = previews
          .map((preview) => {
            const previewUrl = preview.preview_url
              ? `<a class="link" href="${escapeHtml(preview.preview_url)}" target="_blank" rel="noreferrer">Open preview</a>`
              : `<span class="meta">No live URL</span>`;

            const closureReason = preview.closure_reason
              ? `<div class="meta">Closure: ${escapeHtml(preview.closure_reason)}</div>`
              : `<div class="meta">Closure: active</div>`;

            return `
              <tr>
                <td data-label="Preview">
                  <div class="preview-id">${escapeHtml(preview.preview_id)}</div>
                  <div class="meta">PR #${escapeHtml(preview.pr_number || "unknown")}</div>
                  <div class="meta">SHA ${escapeHtml((preview.git_sha || "unknown").slice(0, 7))}</div>
                </td>
                <td data-label="Status">
                  <span class="${statusClass(preview.status)}">${escapeHtml(preview.status)}</span>
                  ${closureReason}
                </td>
                <td data-label="Branch">
                  <div>${escapeHtml(preview.git_branch || "Unknown")}</div>
                  <div class="meta">${escapeHtml(preview.event_type || "No event type")}</div>
                </td>
                <td data-label="Updated">
                  <div>${escapeHtml(formatDate(preview.updated_at))}</div>
                  <div class="meta">Created ${escapeHtml(formatDate(preview.created_at))}</div>
                </td>
                <td data-label="Preview URL">
                  ${previewUrl}
                  <div class="meta">${escapeHtml(preview.image_uri || "No image recorded")}</div>
                </td>
              </tr>
            `;
          })
          .join("");
      }

      async function loadPreviews() {
        elements.footer.textContent = "Refreshing preview records…";
        elements.refreshButton.disabled = true;

        try {
          const response = await fetch("/previews", { headers: { Accept: "application/json" } });
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }

          state.previews = await response.json();
          renderTable();
          elements.footer.textContent = `Showing ${state.previews.length} preview records. Last refreshed ${new Date().toLocaleTimeString()}.`;
        } catch (error) {
          elements.table.innerHTML = "";
          elements.empty.hidden = false;
          elements.footer.textContent = `Unable to load previews right now: ${error.message}`;
        } finally {
          elements.refreshButton.disabled = false;
        }
      }

      elements.search.addEventListener("input", renderTable);
      elements.statusFilter.addEventListener("change", renderTable);
      elements.closureFilter.addEventListener("change", renderTable);
      elements.refreshButton.addEventListener("click", loadPreviews);

      loadPreviews();
    </script>
  </body>
</html>
"""


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
