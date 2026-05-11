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
        --bg: #f4efe7;
        --ink: #171510;
        --muted: #6c665d;
        --panel: rgba(255, 250, 243, 0.84);
        --panel-strong: rgba(255, 253, 248, 0.94);
        --line: rgba(92, 74, 48, 0.16);
        --accent: #b64d22;
        --accent-deep: #7f2e10;
        --good: #1f6a46;
        --good-soft: rgba(31, 106, 70, 0.12);
        --bad: #9e3d32;
        --bad-soft: rgba(158, 61, 50, 0.12);
        --gold: #8b6519;
        --shadow: 0 22px 60px rgba(67, 45, 21, 0.14);
        --radius-xl: 28px;
        --radius-lg: 22px;
        --radius-md: 16px;
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        font-family: Georgia, "Times New Roman", serif;
        color: var(--ink);
        background:
          radial-gradient(circle at 12% 8%, rgba(182, 77, 34, 0.18), transparent 26%),
          radial-gradient(circle at 88% 14%, rgba(31, 106, 70, 0.12), transparent 22%),
          radial-gradient(circle at 80% 82%, rgba(139, 101, 25, 0.1), transparent 26%),
          linear-gradient(180deg, #f8f3ea 0%, var(--bg) 100%);
      }

      main {
        width: min(1260px, calc(100% - 32px));
        margin: 0 auto;
        padding: 30px 0 56px;
      }

      .hero {
        display: grid;
        grid-template-columns: minmax(0, 1.25fr) minmax(290px, 0.75fr);
        gap: 18px;
        margin-bottom: 20px;
      }

      .hero-panel,
      .summary-panel,
      .filters-panel,
      .board-panel,
      .metric,
      .preview-card {
        border: 1px solid var(--line);
        background: var(--panel);
        box-shadow: var(--shadow);
        backdrop-filter: blur(10px);
      }

      .hero-panel,
      .summary-panel,
      .filters-panel,
      .board-panel {
        border-radius: var(--radius-xl);
      }

      .hero-panel {
        padding: 26px 28px 28px;
      }

      .summary-panel {
        padding: 22px 22px 24px;
      }

      .eyebrow {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        width: fit-content;
        padding: 8px 13px;
        border-radius: 999px;
        background: rgba(182, 77, 34, 0.12);
        color: var(--accent-deep);
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
      }

      .hero h1 {
        margin: 0;
        font-size: clamp(42px, 7vw, 78px);
        line-height: 0.92;
        letter-spacing: -0.04em;
        max-width: 11ch;
      }

      .lede {
        margin: 16px 0 0;
        max-width: 720px;
        color: var(--muted);
        font-size: 18px;
        line-height: 1.6;
      }

      .hero-strip {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        margin-top: 22px;
      }

      .hero-chip {
        border: 1px solid var(--line);
        border-radius: 999px;
        padding: 10px 14px;
        background: rgba(255, 255, 255, 0.65);
        font-size: 14px;
        color: var(--muted);
      }

      .hero-chip strong {
        color: var(--ink);
        font-size: 15px;
      }

      .summary-title {
        margin: 0 0 14px;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--muted);
      }

      .summary-emphasis {
        font-size: clamp(30px, 5vw, 48px);
        line-height: 0.98;
        margin: 0;
        letter-spacing: -0.04em;
      }

      .summary-copy {
        margin: 12px 0 0;
        color: var(--muted);
        line-height: 1.6;
      }

      .metrics {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 14px;
        margin: 18px 0 20px;
      }

      .metric {
        border-radius: var(--radius-lg);
        padding: 18px 18px 16px;
      }

      .metric-label {
        color: var(--muted);
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }

      .metric-value {
        margin-top: 12px;
        font-size: 38px;
        line-height: 1;
      }

      .metric-note {
        margin-top: 10px;
        color: var(--muted);
        font-size: 13px;
        line-height: 1.4;
      }

      .filters-panel {
        padding: 16px;
        margin-bottom: 18px;
      }

      .toolbar {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        flex-wrap: wrap;
        gap: 12px;
        align-items: center;
      }

      .filters {
        display: grid;
        grid-template-columns: minmax(220px, 1.4fr) repeat(2, minmax(160px, 0.7fr));
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
        border: 1px solid var(--line);
        border-radius: 14px;
        background: var(--panel-strong);
        color: var(--ink);
        padding: 11px 14px;
      }

      .button {
        cursor: pointer;
        background: linear-gradient(180deg, #fff8ef 0%, #f1d7be 100%);
        font-weight: 700;
      }

      .button:hover {
        transform: translateY(-1px);
      }

      .board-panel {
        padding: 18px;
      }

      .board-head {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 12px;
        margin-bottom: 16px;
      }

      .board-title {
        margin: 0;
        font-size: 26px;
        letter-spacing: -0.03em;
      }

      .board-subtitle {
        margin: 6px 0 0;
        color: var(--muted);
        font-size: 15px;
      }

      .board-count {
        color: var(--muted);
        font-size: 14px;
      }

      .preview-grid {
        display: grid;
        gap: 14px;
      }

      .preview-card {
        border-radius: var(--radius-lg);
        padding: 18px;
        display: grid;
        grid-template-columns: minmax(0, 1.2fr) minmax(240px, 0.8fr);
        gap: 16px;
        align-items: start;
      }

      .preview-card-ready {
        border-color: rgba(31, 106, 70, 0.25);
        background: linear-gradient(180deg, rgba(255, 251, 247, 0.95) 0%, rgba(245, 255, 250, 0.94) 100%);
      }

      .preview-card-destroyed {
        border-color: rgba(158, 61, 50, 0.24);
        background: linear-gradient(180deg, rgba(255, 250, 246, 0.95) 0%, rgba(255, 246, 244, 0.94) 100%);
      }

      .preview-topline {
        display: flex;
        gap: 10px;
        align-items: center;
        flex-wrap: wrap;
        margin-bottom: 12px;
      }

      .preview-id {
        font-weight: 700;
        font-size: 22px;
        letter-spacing: -0.03em;
      }

      .preview-pr {
        color: var(--muted);
        font-size: 14px;
      }

      .status {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 7px 11px;
        border-radius: 999px;
        font-size: 12px;
        border: 1px solid transparent;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 700;
      }

      .status-ready {
        color: var(--good);
        background: var(--good-soft);
        border-color: rgba(31, 106, 70, 0.24);
      }

      .status-destroyed {
        color: var(--bad);
        background: var(--bad-soft);
        border-color: rgba(158, 61, 50, 0.22);
      }

      .status-other {
        color: var(--gold);
        background: rgba(139, 101, 25, 0.12);
        border-color: rgba(139, 101, 25, 0.24);
      }

      .preview-copy {
        color: var(--muted);
        font-size: 16px;
        line-height: 1.55;
        margin: 0 0 16px;
      }

      .meta-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px 14px;
      }

      .meta-block {
        border-top: 1px solid rgba(92, 74, 48, 0.12);
        padding-top: 10px;
      }

      .meta-label {
        color: var(--muted);
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }

      .meta-value {
        margin-top: 5px;
        font-size: 15px;
        line-height: 1.45;
        word-break: break-word;
      }

      .preview-side {
        display: grid;
        gap: 12px;
      }

      .side-card {
        border: 1px solid rgba(92, 74, 48, 0.12);
        border-radius: 18px;
        background: rgba(255, 255, 255, 0.58);
        padding: 14px;
      }

      .side-label {
        color: var(--muted);
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }

      .side-value {
        margin-top: 8px;
        font-size: 15px;
        line-height: 1.5;
        word-break: break-word;
      }

      .link {
        color: var(--accent-deep);
        text-decoration: none;
        font-weight: 700;
      }

      .link:hover {
        text-decoration: underline;
      }

      .empty {
        padding: 34px 18px 22px;
        color: var(--muted);
        text-align: center;
        font-size: 16px;
      }

      .footer-note {
        margin-top: 16px;
        color: var(--muted);
        font-size: 14px;
      }

      @media (max-width: 1080px) {
        .hero {
          grid-template-columns: 1fr;
        }

        .metrics {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .toolbar,
        .filters {
          grid-template-columns: 1fr;
        }

        .preview-card {
          grid-template-columns: 1fr;
        }
      }

      @media (max-width: 640px) {
        main {
          width: min(100% - 20px, 1200px);
          padding-top: 24px;
        }

        .metrics,
        .meta-grid {
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
        <article class="hero-panel">
          <span class="eyebrow">TerraPreview Control Plane</span>
          <h1>Preview infrastructure that reads like an operations console.</h1>
          <p class="lede">
            See what is live right now, what has already been torn down, and which pull requests left behind metadata that needs attention. This is the single surface for preview state, not just a JSON endpoint with a prettier wrapper.
          </p>
          <div class="hero-strip">
            <span class="hero-chip"><strong>Live previews</strong> are surfaced with direct entry points.</span>
            <span class="hero-chip"><strong>Destroyed previews</strong> retain closure context for audits.</span>
            <span class="hero-chip"><strong>Filters</strong> make drift easy to spot fast.</span>
          </div>
        </article>
        <aside class="summary-panel">
          <div class="summary-title">Operational Snapshot</div>
          <p class="summary-emphasis">A control plane you can actually scan in seconds.</p>
          <p class="summary-copy">
            TerraPreview now tracks the full lifecycle from ready to destroyed, including whether a preview died because the PR merged or because it was simply closed.
          </p>
        </aside>
      </section>

      <section class="metrics" aria-label="Preview summary">
        <article class="metric">
          <div class="metric-label">Total Records</div>
          <div class="metric-value" id="stat-total">0</div>
          <div class="metric-note">Every known preview state change preserved in the control plane.</div>
        </article>
        <article class="metric">
          <div class="metric-label">Ready</div>
          <div class="metric-value" id="stat-ready">0</div>
          <div class="metric-note">Currently active previews with a live route attached.</div>
        </article>
        <article class="metric">
          <div class="metric-label">Destroyed</div>
          <div class="metric-value" id="stat-destroyed">0</div>
          <div class="metric-note">Previews that have been torn down and recorded cleanly.</div>
        </article>
        <article class="metric">
          <div class="metric-label">Merged Closures</div>
          <div class="metric-value" id="stat-merged">0</div>
          <div class="metric-note">Destroyed previews that ended through a successful merge path.</div>
        </article>
      </section>

      <section class="filters-panel">
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
      </section>

      <section class="board-panel">
        <div class="board-head">
          <div>
            <h2 class="board-title">Preview Ledger</h2>
            <p class="board-subtitle">A readable lifecycle view across active, merged, and manually closed environments.</p>
          </div>
          <div class="board-count" id="board-count">0 records visible</div>
        </div>
        <div class="preview-grid" id="preview-table"></div>
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
        boardCount: document.getElementById("board-count"),
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
        elements.boardCount.textContent = `${previews.length} record${previews.length === 1 ? "" : "s"} visible`;

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
              ? escapeHtml(preview.closure_reason)
              : "active";

            const cardClass = preview.status === "ready" ? "preview-card preview-card-ready" : preview.status === "destroyed" ? "preview-card preview-card-destroyed" : "preview-card";
            const copy = preview.status === "ready"
              ? "This preview is currently active and should be reachable through its live route."
              : "This preview has already been torn down and remains here for historical visibility.";

            return `
              <article class="${cardClass}">
                <div>
                  <div class="preview-topline">
                    <div class="preview-id">${escapeHtml(preview.preview_id)}</div>
                    <div class="preview-pr">PR #${escapeHtml(preview.pr_number || "unknown")}</div>
                  </div>
                  <span class="${statusClass(preview.status)}">${escapeHtml(preview.status)}</span>
                  <p class="preview-copy">${copy}</p>
                  <div class="meta-grid">
                    <div class="meta-block">
                      <div class="meta-label">Branch</div>
                      <div class="meta-value">${escapeHtml(preview.git_branch || "Unknown")}</div>
                    </div>
                    <div class="meta-block">
                      <div class="meta-label">Closure</div>
                      <div class="meta-value">${closureReason}</div>
                    </div>
                    <div class="meta-block">
                      <div class="meta-label">Event Type</div>
                      <div class="meta-value">${escapeHtml(preview.event_type || "No event type")}</div>
                    </div>
                    <div class="meta-block">
                      <div class="meta-label">Git SHA</div>
                      <div class="meta-value">${escapeHtml(preview.git_sha || "Unknown")}</div>
                    </div>
                  </div>
                </div>
                <div class="preview-side">
                  <div class="side-card">
                    <div class="side-label">Preview Route</div>
                    <div class="side-value">${previewUrl}</div>
                  </div>
                  <div class="side-card">
                    <div class="side-label">Container Image</div>
                    <div class="side-value">${escapeHtml(preview.image_uri || "No image recorded")}</div>
                  </div>
                  <div class="side-card">
                    <div class="side-label">Lifecycle Timing</div>
                    <div class="side-value">Updated ${escapeHtml(formatDate(preview.updated_at))}<br />Created ${escapeHtml(formatDate(preview.created_at))}</div>
                  </div>
                </div>
              </article>
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
