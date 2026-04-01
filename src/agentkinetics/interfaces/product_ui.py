from __future__ import annotations

import json
from html import escape
from typing import Mapping


def _normalize_metrics(metrics: Mapping[str, int]) -> dict[str, int]:
    return {
        "tenants": int(metrics.get("tenants", 0)),
        "users": int(metrics.get("users", 0)),
        "runs": int(metrics.get("runs", 0)),
    }


_STYLE = """
<style>
  :root {
    color-scheme: light;
    --bg: #f4f7fb;
    --card: rgba(255, 255, 255, 0.84);
    --card-strong: rgba(255, 255, 255, 0.94);
    --line: rgba(15, 23, 42, 0.08);
    --line-strong: rgba(15, 23, 42, 0.14);
    --text: #102033;
    --muted: #5f6e84;
    --accent: #0d63ff;
    --accent-strong: #074ac5;
    --accent-soft: rgba(13, 99, 255, 0.10);
    --mint: #0d9b8a;
    --amber: #b66b00;
    --rose: #b63d4b;
    --shadow: 0 28px 72px rgba(20, 35, 65, 0.10);
    --radius-2xl: 30px;
    --radius-xl: 24px;
    --radius-lg: 18px;
    --radius-md: 14px;
    --radius-sm: 12px;
    --font-display: "Segoe UI Variable Display", "SF Pro Display", "Helvetica Neue", sans-serif;
    --font-text: "Segoe UI Variable Text", "SF Pro Text", "Helvetica Neue", sans-serif;
  }

  * { box-sizing: border-box; }

  body {
    margin: 0;
    min-height: 100vh;
    font-family: var(--font-text);
    color: var(--text);
    background:
      radial-gradient(circle at top left, rgba(13, 99, 255, 0.10), transparent 24%),
      radial-gradient(circle at 84% 10%, rgba(13, 155, 138, 0.09), transparent 24%),
      linear-gradient(180deg, #f8fbff 0%, #eef4fb 100%);
  }

  body::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    background-image:
      linear-gradient(rgba(17, 99, 255, 0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(17, 99, 255, 0.03) 1px, transparent 1px);
    background-size: 44px 44px;
    mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.6), transparent 85%);
  }

  button,
  input,
  textarea,
  select {
    font: inherit;
  }

  .shell {
    position: relative;
    display: grid;
    grid-template-columns: 264px minmax(0, 1fr);
    gap: 14px;
    align-items: stretch;
    width: min(1580px, calc(100vw - 24px));
    min-height: calc(100vh - 24px);
    margin: 12px auto;
    padding: 12px;
    border: 1px solid rgba(255, 255, 255, 0.55);
    border-radius: 34px;
    background: rgba(248, 251, 255, 0.78);
    box-shadow: var(--shadow);
    backdrop-filter: blur(20px);
    overflow: hidden;
  }

  .rail {
    position: sticky;
    top: 12px;
    display: grid;
    grid-template-rows: auto auto 1fr auto;
    gap: 14px;
    min-height: calc(100vh - 48px);
    padding: 16px;
    border: 1px solid rgba(255, 255, 255, 0.55);
    border-radius: var(--radius-2xl);
    background: rgba(255, 255, 255, 0.76);
    box-shadow: 0 16px 36px rgba(18, 33, 62, 0.06);
  }

  .rail-header,
  .rail-section,
  .content-shell,
  .surface-stack,
  .helper-list,
  .workspace-shell {
    display: grid;
    gap: 14px;
  }

  .content-shell {
    min-width: 0;
    min-height: calc(100vh - 48px);
    grid-template-rows: auto auto minmax(0, 1fr);
  }

  .rail-brand {
    display: flex;
    gap: 12px;
    align-items: center;
  }

  .rail-brand .brand-mark {
    width: 38px;
    height: 38px;
    border-radius: 14px;
  }

  .rail-title {
    margin: 0;
    font-family: var(--font-display);
    font-size: 1rem;
    font-weight: 650;
    letter-spacing: -0.03em;
  }

  .rail-copy {
    margin: 0;
    color: var(--muted);
    font-size: 0.88rem;
    line-height: 1.55;
  }

  .rail-nav {
    display: grid;
    gap: 8px;
  }

  .rail-item {
    justify-content: flex-start;
    min-height: 46px;
    color: var(--text);
    background: rgba(255, 255, 255, 0.78);
    border: 1px solid transparent;
    box-shadow: none;
  }

  .rail-item.active {
    color: var(--accent);
    background: linear-gradient(135deg, rgba(13, 99, 255, 0.12), rgba(13, 99, 255, 0.07));
    border-color: rgba(13, 99, 255, 0.22);
    box-shadow: inset 0 0 0 1px rgba(13, 99, 255, 0.08);
  }

  .topbar {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
    align-items: flex-start;
    padding: 18px 20px;
    border: 1px solid rgba(255, 255, 255, 0.56);
    border-radius: var(--radius-2xl);
    background: rgba(255, 255, 255, 0.76);
    box-shadow: 0 10px 28px rgba(18, 33, 62, 0.04);
  }

  .brand {
    display: flex;
    gap: 14px;
    align-items: flex-start;
  }

  .brand-mark {
    width: 50px;
    height: 50px;
    border-radius: 18px;
    background: linear-gradient(145deg, #0e5df0, #71b3ff);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.55);
    position: relative;
    overflow: hidden;
  }

  .brand-mark::before,
  .brand-mark::after {
    content: "";
    position: absolute;
    border-radius: 999px;
  }

  .brand-mark::before {
    inset: 10px 20px 10px 12px;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(255, 255, 255, 0.35));
    transform: skew(-14deg);
  }

  .brand-mark::after {
    width: 14px;
    height: 14px;
    right: 9px;
    top: 9px;
    background: rgba(255, 255, 255, 0.78);
  }

  .eyebrow {
    margin: 0 0 8px;
    color: var(--accent);
    font-size: 0.74rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.13em;
  }

  h1,
  h2,
  h3,
  h4 {
    margin: 0;
    font-family: var(--font-display);
    letter-spacing: -0.035em;
    font-weight: 650;
  }

  h1 { font-size: clamp(1.4rem, 2vw, 1.9rem); }
  h2 { font-size: clamp(2.05rem, 4vw, 3.1rem); line-height: 0.98; }
  h3 { font-size: 1.22rem; }
  h4 { font-size: 0.98rem; }

  .lede,
  .muted,
  .section-copy,
  .metric-copy,
  .queue-meta,
  .timeline-copy {
    color: var(--muted);
    line-height: 1.6;
  }

  .header-chips,
  .meta-row,
  .inline-row,
  .tab-row,
  .action-row,
  .button-cluster {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    align-items: center;
  }

  .header-chips {
    justify-content: flex-end;
  }

  .chip,
  .status-pill,
  .meta-pill,
  .tab-button {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    min-height: 38px;
    padding: 9px 13px;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.8);
    color: var(--text);
    font-size: 0.88rem;
  }

  .status-pill[data-tone="success"] { color: #0d6c62; }
  .status-pill[data-tone="warn"] { color: var(--amber); }
  .status-pill[data-tone="error"] { color: var(--rose); }

  .panel,
  .metric-card,
  .queue-item,
  .timeline-item,
  .helper-item,
  .kpi-card {
    border: 1px solid var(--line);
    border-radius: var(--radius-lg);
    background: var(--card);
    box-shadow: 0 10px 28px rgba(18, 33, 62, 0.04);
  }

  .panel {
    display: grid;
    gap: 14px;
    min-width: 0;
    padding: 18px;
  }

  .section-head {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    align-items: flex-start;
  }

  .view {
    display: none;
    min-height: 0;
  }

  .view.active {
    display: grid;
  }

  .view-shell {
    height: min(760px, calc(100vh - 220px));
    overflow: hidden;
  }

  .hero-grid,
  .surface-grid,
  .job-strip,
  .detail-grid,
  .field-grid,
  .control-grid,
  .metric-grid,
  .kpi-strip {
    display: grid;
    gap: 14px;
  }

  .hero-grid {
    grid-template-columns: minmax(0, 1.18fr) minmax(360px, 0.82fr);
    min-height: 0;
  }

  .hero-card {
    padding: 28px;
    border: 1px solid rgba(13, 99, 255, 0.11);
    border-radius: var(--radius-2xl);
    background:
      radial-gradient(circle at 85% 20%, rgba(13, 99, 255, 0.12), transparent 24%),
      linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(255, 255, 255, 0.82));
  }

  .job-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    margin-top: 10px;
  }

  .job-index {
    display: inline-flex;
    width: 28px;
    height: 28px;
    border-radius: 999px;
    align-items: center;
    justify-content: center;
    background: rgba(13, 99, 255, 0.10);
    color: var(--accent);
    font-size: 0.85rem;
    font-weight: 700;
    margin-bottom: 10px;
  }

  .job-card,
  .helper-item,
  .kpi-card {
    padding: 16px;
    background: rgba(255, 255, 255, 0.76);
  }

  .job-copy,
  .helper-copy {
    margin: 0;
    color: var(--muted);
    line-height: 1.55;
  }

  .helper-item {
    display: grid;
    gap: 6px;
  }

  .helper-title {
    margin: 0;
    font-size: 0.95rem;
    font-weight: 650;
    letter-spacing: -0.02em;
  }

  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .metric-card { padding: 16px; }
  .metric-label { margin: 0 0 8px; color: var(--muted); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.12em; }
  .metric-value { font-size: clamp(1.45rem, 2vw, 2rem); font-family: var(--font-display); letter-spacing: -0.04em; }

  .access-grid {
    grid-template-columns: minmax(0, 1.05fr) minmax(360px, 0.95fr);
    min-height: 0;
    height: 100%;
  }

  .kpi-strip {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .kpi-copy {
    margin: 0;
    color: var(--muted);
    line-height: 1.5;
  }

  .runs-grid {
    grid-template-columns: minmax(360px, 0.9fr) minmax(0, 1.1fr);
    min-height: 0;
    height: 100%;
  }

  .inspector-grid {
    grid-template-columns: minmax(0, 1.18fr) minmax(340px, 0.82fr);
    min-height: 0;
    height: 100%;
  }

  .queue-panel,
  .composer-panel,
  .evidence-panel,
  .control-panel,
  .session-panel,
  .access-panel {
    min-height: 0;
  }

  .access-panel,
  .session-panel {
    grid-template-rows: auto auto auto minmax(0, 1fr);
  }

  .composer-panel {
    grid-template-rows: auto auto minmax(0, 1fr);
  }

  .queue-panel,
  .queue-panel {
    grid-template-rows: auto auto minmax(0, 1fr);
  }

  .evidence-panel {
    grid-template-rows: auto auto auto minmax(0, 1fr);
  }

  .control-panel {
    grid-template-rows: auto auto auto minmax(0, 1fr);
  }

  .queue-list,
  .timeline-list,
  .approval-stack,
  .panel-scroll,
  .tab-stage,
  .control-stack {
    min-height: 0;
    overflow: auto;
    scrollbar-gutter: stable;
  }

  .queue-list,
  .timeline-list,
  .approval-stack {
    display: grid;
    gap: 12px;
  }

  .queue-item {
    width: 100%;
    padding: 16px;
    text-align: left;
    cursor: pointer;
    transition: border-color 120ms ease, transform 120ms ease, box-shadow 120ms ease;
    color: var(--text);
    background: rgba(255, 255, 255, 0.82);
    box-shadow: none;
  }

  .queue-item:hover {
    transform: translateY(-1px);
    border-color: rgba(13, 99, 255, 0.24);
    box-shadow: 0 12px 28px rgba(13, 99, 255, 0.08);
  }

  .queue-item.active {
    border-color: rgba(13, 99, 255, 0.30);
    box-shadow: inset 0 0 0 1px rgba(13, 99, 255, 0.16);
  }

  .queue-title { margin: 0 0 10px; font-size: 1rem; line-height: 1.45; }

  .detail-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }

  .detail-block {
    padding: 14px;
    border: 1px solid var(--line);
    border-radius: var(--radius-md);
    background: rgba(255, 255, 255, 0.62);
  }

  .detail-label {
    margin: 0 0 8px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-size: 0.76rem;
  }

  .detail-value { line-height: 1.55; word-break: break-word; }

  .tab-button {
    cursor: pointer;
    background: rgba(255, 255, 255, 0.72);
    box-shadow: none;
    color: var(--text);
  }

  .tab-button.active {
    background: rgba(13, 99, 255, 0.10);
    border-color: rgba(13, 99, 255, 0.24);
    color: var(--accent);
  }

  .tab-stage {
    display: grid;
  }

  .tab-panel {
    display: none;
    min-height: 0;
  }

  .tab-panel.active {
    display: grid;
  }

  .timeline-item { padding: 16px; }
  .timeline-title { margin: 0 0 8px; font-weight: 650; }

  form { display: grid; gap: 12px; }

  .field-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }

  label {
    display: grid;
    gap: 8px;
    font-size: 0.95rem;
  }

  .field-label {
    color: var(--muted);
    font-size: 0.8rem;
    letter-spacing: 0.11em;
    text-transform: uppercase;
  }

  input,
  textarea,
  select {
    width: 100%;
    padding: 13px 14px;
    border-radius: var(--radius-md);
    border: 1px solid var(--line-strong);
    background: rgba(255, 255, 255, 0.9);
    color: var(--text);
    outline: none;
  }

  textarea {
    min-height: 128px;
    resize: vertical;
  }

  input:focus-visible,
  textarea:focus-visible,
  select:focus-visible {
    border-color: rgba(13, 99, 255, 0.46);
    box-shadow: 0 0 0 4px rgba(13, 99, 255, 0.12);
  }

  button {
    min-height: 46px;
    padding: 11px 18px;
    border: 0;
    border-radius: 999px;
    cursor: pointer;
    font-weight: 700;
    color: white;
    background: linear-gradient(135deg, var(--accent), var(--accent-strong));
    box-shadow: 0 16px 30px rgba(17, 99, 255, 0.18);
  }

  button:hover { transform: translateY(-1px); }
  button:focus-visible {
    outline: 3px solid rgba(13, 99, 255, 0.22);
    outline-offset: 2px;
  }
  button:disabled { opacity: 0.45; cursor: not-allowed; transform: none; }

  .secondary-button,
  .ghost-button {
    color: var(--text);
    background: rgba(255, 255, 255, 0.82);
    border: 1px solid var(--line-strong);
    box-shadow: none;
  }

  .banner {
    display: flex;
    align-items: center;
    min-height: 48px;
    padding: 12px 16px;
    border-radius: var(--radius-md);
    border: 1px solid var(--line);
    background: rgba(255, 255, 255, 0.8);
  }

  .banner[data-tone="success"] { border-color: rgba(13, 155, 138, 0.20); color: #0d6c62; }
  .banner[data-tone="warn"] { border-color: rgba(214, 124, 0, 0.22); color: #875309; }
  .banner[data-tone="error"] { border-color: rgba(204, 71, 84, 0.22); color: #9f3141; }

  .meta-pill[data-tone="success"] {
    color: #0d6c62;
    border-color: rgba(13, 155, 138, 0.18);
    background: rgba(13, 155, 138, 0.08);
  }

  .meta-pill[data-tone="warn"] {
    color: #875309;
    border-color: rgba(214, 124, 0, 0.18);
    background: rgba(214, 124, 0, 0.08);
  }

  .meta-pill[data-tone="error"] {
    color: #9f3141;
    border-color: rgba(204, 71, 84, 0.18);
    background: rgba(204, 71, 84, 0.08);
  }

  .meta-pill[data-tone="neutral"] {
    color: var(--muted);
  }

  .success-button {
    background: linear-gradient(135deg, #0d9b8a, #0b7d71);
    box-shadow: 0 16px 30px rgba(13, 155, 138, 0.18);
  }

  .warn-button {
    background: linear-gradient(135deg, #d67c00, #ad6500);
    box-shadow: 0 16px 30px rgba(214, 124, 0, 0.18);
  }

  .danger-button {
    background: linear-gradient(135deg, #cc4754, #a93843);
    box-shadow: 0 16px 30px rgba(204, 71, 84, 0.18);
  }

  .control-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }

  .action-card,
  .approval-card {
    padding: 18px;
    border: 1px solid var(--line);
    border-radius: var(--radius-md);
    background: rgba(255, 255, 255, 0.74);
  }

  .compact-textarea {
    min-height: 92px;
    max-height: 148px;
  }

  .approval-head {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    align-items: flex-start;
    margin-bottom: 10px;
  }

  .approval-copy,
  .approval-meta {
    margin: 0;
    color: var(--muted);
    line-height: 1.6;
  }

  .approval-meta {
    font-size: 0.88rem;
  }

  pre {
    margin: 0;
    padding: 16px;
    overflow: auto;
    border-radius: var(--radius-md);
    border: 1px solid var(--line);
    background: rgba(250, 252, 255, 0.94);
    color: #13304f;
    font-family: "Cascadia Code", "SF Mono", Consolas, monospace;
    font-size: 0.85rem;
    line-height: 1.6;
    max-height: 240px;
  }

  .empty-state {
    padding: 20px;
    border: 1px dashed var(--line-strong);
    border-radius: var(--radius-md);
    background: rgba(255, 255, 255, 0.54);
    color: var(--muted);
    line-height: 1.6;
  }

  .rail-panel {
    padding: 14px;
  }

  .helper-list.compact {
    gap: 10px;
  }

  .queue-actions {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    align-items: center;
  }

  .tab-row {
    border-bottom: 1px solid var(--line);
    padding-bottom: 10px;
  }

  @media (max-width: 1360px) {
    .shell {
      grid-template-columns: 236px minmax(0, 1fr);
    }

    .hero-grid {
      grid-template-columns: 1fr;
    }

    .access-grid,
    .runs-grid,
    .inspector-grid {
      grid-template-columns: 1fr;
    }

    .detail-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 1120px) {
    .rail {
      position: static;
      min-height: auto;
    }

    .shell {
      grid-template-columns: 1fr;
      min-height: auto;
    }

    .content-shell,
    .view-shell {
      min-height: auto;
      height: auto;
    }

    .queue-panel,
    .evidence-panel,
    .control-panel {
      grid-template-rows: auto auto auto;
    }

    .queue-list,
    .timeline-list,
    .approval-stack,
    .panel-scroll,
    .tab-stage,
    .control-stack {
      overflow: visible;
    }
  }

  @media (max-width: 760px) {
    .shell {
      width: min(100vw - 16px, 100%);
      margin: 8px auto;
      padding: 10px;
      border-radius: 24px;
    }

    .topbar,
    .panel,
    .hero-card {
      padding: 18px;
    }

    .job-strip,
    .metric-grid,
    .kpi-strip,
    .field-grid,
    .detail-grid,
    .control-grid {
      grid-template-columns: 1fr;
    }

    .header-chips,
    .queue-actions {
      align-items: stretch;
    }

    h2 { font-size: clamp(1.8rem, 11vw, 2.4rem); }
  }
</style>
"""
_SCRIPT = """
<script>
  const state = {
    metrics: typeof INJECTED_METRICS !== 'undefined' ? INJECTED_METRICS : { tenants: 0, users: 0, runs: 0, approvals: 0 },
    sessionToken: "",
    operatorName: "",
    operatorRole: "",
    selectedRunId: "",
    runView: null,
    inspectorTab: "overview",
    appView: "overview",
    eventSource: null,
  };

  const storageKeys = {
    token: "agentkinetics.session_token",
    operator: "agentkinetics.operator_name",
    role: "agentkinetics.operator_role",
  };

  function byId(id) {
    return document.getElementById(id);
  }

  class ApiError extends Error {
    constructor(message, status, body) {
      super(message);
      this.name = "ApiError";
      this.status = status;
      this.body = body;
    }
  }

  async function requestJson(url, options = {}) {
    const response = await fetch(url, options);
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new ApiError(body.detail || "Request failed.", response.status, body);
    }
    return body;
  }

  function formatJson(value) {
    return JSON.stringify(value || {}, null, 2);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function formatLabel(value) {
    return String(value || "").replaceAll("_", " ");
  }

  function statusTone(status) {
    const value = String(status || "");
    if (["running", "approved", "completed"].includes(value)) {
      return "success";
    }
    if (["pending", "waiting_approval"].includes(value)) {
      return "warn";
    }
    if (["failed", "denied", "canceled"].includes(value)) {
      return "error";
    }
    return "neutral";
  }

  function isUnauthorizedError(error) {
    return error instanceof ApiError && error.status === 401;
  }

  function latestApproval() {
    const approvals = state.runView?.approvals || [];
    return approvals.length ? approvals[approvals.length - 1] : null;
  }

  function approvalSummaryText(approval) {
    if (!approval) {
      return "No approval is active for this run.";
    }
    const decidedAt = approval.decided_at ? ` Decision at ${approval.decided_at}.` : "";
    return `Latest approval is ${formatLabel(approval.status)}. ${approval.reason}.${decidedAt}`;
  }

  function setAppView(view) {
    state.appView = view;
    byId("shell").dataset.view = view;
    document.querySelectorAll("[data-app-view]").forEach((node) => {
      const active = node.getAttribute("data-app-view") === view;
      node.classList.toggle("active", active);
      node.hidden = !active;
    });
    document.querySelectorAll("[data-rail-target]").forEach((node) => {
      const requiresSession = node.getAttribute("data-requires-session") === "true";
      const disabled = requiresSession && !state.sessionToken;
      const active = node.getAttribute("data-rail-target") === view;
      node.disabled = disabled;
      node.classList.toggle("active", active);
      if (active) {
        node.setAttribute("aria-current", "page");
      } else {
        node.removeAttribute("aria-current");
      }
    });
  }

  function updateMetric(name, value) {
    const node = document.querySelector(`[data-metric="${name}"]`);
    if (node) {
      node.textContent = String(value);
    }
  }

  function setBanner(message, tone = "warn") {
    const node = byId("status-banner");
    node.dataset.tone = tone;
    node.textContent = message;
  }

  function updateStreamChip(label, tone) {
    const node = byId("stream-chip");
    node.dataset.tone = tone;
    node.textContent = label;
  }

  function persistSession() {
    if (state.sessionToken) {
      localStorage.setItem(storageKeys.token, state.sessionToken);
      localStorage.setItem(storageKeys.operator, state.operatorName);
      localStorage.setItem(storageKeys.role, state.operatorRole);
    } else {
      localStorage.removeItem(storageKeys.token);
      localStorage.removeItem(storageKeys.operator);
      localStorage.removeItem(storageKeys.role);
    }
  }

  async function fetchSessionContext(token) {
    return await requestJson("/auth/session", {
      headers: { "X-Session-Token": token },
    });
  }

  function syncRunControls() {
    const hasSession = state.sessionToken.length > 0;
    const hasRun = Boolean(state.runView?.run);
    const runStatus = state.runView?.run?.status || "";
    const approval = latestApproval();
    const approvalPending = approval?.status === "pending";
    const approvalApproved = approval?.status === "approved";
    const approvalDenied = approval?.status === "denied";
    const canResume =
      hasSession &&
      hasRun &&
      !["running", "completed", "failed", "canceled"].includes(runStatus) &&
      (!approval || approvalApproved);
    const canInterrupt =
      hasSession &&
      hasRun &&
      !["interrupted", "completed", "failed", "canceled"].includes(runStatus);
    const canRetry =
      hasSession &&
      hasRun &&
      !["running", "completed"].includes(runStatus);
    const canCancel =
      hasSession &&
      hasRun &&
      !["canceled", "completed"].includes(runStatus);
    const canRequestApproval =
      hasSession &&
      hasRun &&
      !["completed", "canceled"].includes(runStatus) &&
      !approvalPending;
    const canDecideApproval =
      hasSession &&
      state.operatorRole === "admin" &&
      hasRun &&
      approvalPending;

    byId("create-run-button").disabled = !hasSession;
    byId("open-selected-run-button").disabled = !hasSession || !state.selectedRunId;
    byId("resume-run-button").disabled = !canResume;
    byId("interrupt-run-button").disabled = !canInterrupt;
    byId("retry-run-button").disabled = !canRetry;
    byId("cancel-run-button").disabled = !canCancel;
    byId("request-approval-button").disabled = !canRequestApproval;
    byId("approve-button").disabled = !canDecideApproval;
    byId("deny-button").disabled = !canDecideApproval;
    byId("approval-decision-row").hidden = !canDecideApproval;
  }

  function closeEventStream() {
    if (state.eventSource) {
      state.eventSource.close();
      state.eventSource = null;
    }
    updateStreamChip(state.sessionToken ? "Live sync paused" : "Live sync offline", "warn");
  }

  function handleLiveEvent(payload) {
    updateStreamChip("Live sync on", "success");
    void loadRuns();
    if (state.selectedRunId && payload.run_id === state.selectedRunId) {
      void loadRun(state.selectedRunId);
    }
  }

  async function openEventStream() {
    if (!state.sessionToken) {
      closeEventStream();
      return;
    }
    closeEventStream();
    updateStreamChip("Connecting live sync", "warn");
    try {
      const ticketResponse = await requestJson("/events/ticket", {
        method: "POST",
        headers: { "X-Session-Token": state.sessionToken },
      });
      const source = new EventSource(`/events/stream?ticket=${encodeURIComponent(ticketResponse.ticket)}`);
      source.addEventListener("ready", () => {
        updateStreamChip("Live sync on", "success");
      });
      source.addEventListener("auth", (event) => {
        const payload = JSON.parse(event.data);
        if (payload.status === "invalid") {
          closeEventStream();
          clearSession("Stored session expired. Start a fresh operator session.", "warn");
        }
      });
      source.addEventListener("audit", (event) => {
        const payload = JSON.parse(event.data);
        handleLiveEvent(payload);
      });
      source.onerror = () => {
        updateStreamChip("Live sync reconnecting", "warn");
      };
      state.eventSource = source;
    } catch (error) {
      updateStreamChip("Live sync offline", "error");
    }
  }

  function applySession(token, operatorName, operatorRole) {
    state.sessionToken = token || "";
    state.operatorName = operatorName || "";
    state.operatorRole = operatorRole || "";
    persistSession();
    const hasSession = state.sessionToken.length > 0;
    const sessionLabel = hasSession ? `Operator: ${state.operatorName || "local session"}` : "No active operator session";
    byId("setup-session-summary").textContent = sessionLabel;
    byId("ops-session-summary").textContent = sessionLabel;
    byId("rail-session-name").textContent = hasSession ? state.operatorName || "Local session" : "No active operator";
    byId("rail-session-copy").textContent = hasSession
      ? `${formatLabel(state.operatorRole || "operator")} session can launch runs, inspect evidence, and act on approvals.`
      : "Create or open a session to unlock run operations.";
    byId("rail-session-role").textContent = hasSession ? formatLabel(state.operatorRole || "operator") : "none";
    byId("session-chip").textContent = hasSession ? "Session live" : "Session required";
    byId("session-role-chip").textContent = hasSession ? `Role: ${formatLabel(state.operatorRole || "operator")}` : "Role: none";
    byId("session-token").textContent = hasSession ? state.sessionToken.slice(0, 20) + "..." : "No active operator session.";
    byId("sign-out-button").disabled = !hasSession;
    if (!hasSession) {
      closeEventStream();
      renderRuns([]);
      resetInspector();
      setBanner("Create an operator, then start a session to unlock the run workspace.", "warn");
      setAppView("access");
    } else {
      openEventStream();
      setBanner("Session established. You can launch runs and inspect evidence.", "success");
      if (state.appView === "overview" || state.appView === "access") {
        setAppView("runs");
      } else {
        setAppView(state.appView);
      }
    }
    syncRunControls();
  }

  function clearSession(message = "", tone = "warn") {
    applySession("", "", "");
    if (message) {
      setBanner(message, tone);
    }
  }

  function resetInspector() {
    state.selectedRunId = "";
    state.runView = null;
    byId("run-headline").textContent = "Select a run to inspect evidence";
    byId("run-created").textContent = "-";
    byId("run-updated").textContent = "-";
    byId("ops-resume-status").textContent = "idle";
    byId("inspector-run-status").textContent = "idle";
    byId("overview-input").textContent = "{}";
    byId("overview-output").textContent = "{}";
    byId("overview-approvals").textContent = "0";
    byId("approval-latest-status").textContent = "none";
    byId("approval-latest-status").dataset.tone = "neutral";
    byId("approval-summary-banner").dataset.tone = "warn";
    byId("approval-summary-banner").textContent = "No approval is active for this run.";
    byId("action-reason").value = "";
    byId("checkpoint-list").innerHTML = '<div class="empty-state">Choose a run from the queue to review checkpoints.</div>';
    byId("audit-list").innerHTML = '<div class="empty-state">Audit evidence appears once a run is selected.</div>';
    byId("approval-list").innerHTML = '<div class="empty-state">Approval requests appear here once a run needs a human decision.</div>';
    updateInspectorTab("overview");
    syncRunControls();
  }

  function updateInspectorTab(tab) {
    state.inspectorTab = tab;
    document.querySelectorAll("[data-tab-target]").forEach((node) => {
      const active = node.getAttribute("data-tab-target") === tab;
      node.classList.toggle("active", active);
      node.setAttribute("aria-selected", active ? "true" : "false");
      node.tabIndex = active ? 0 : -1;
    });
    document.querySelectorAll("[data-tab-panel]").forEach((node) => {
      const active = node.getAttribute("data-tab-panel") === tab;
      node.classList.toggle("active", active);
      node.hidden = !active;
    });
  }

  function renderHealth(status) {
    const tone = status === "ok" ? "success" : "warn";
    byId("health-chip").dataset.tone = tone;
    byId("health-chip").textContent = status === "ok" ? "Core online" : "Degraded";
    byId("health-summary").textContent =
      status === "ok" ? "API, storage, and orchestration are reachable." : "Health probe indicates degraded service.";
  }

  function renderRuns(items) {
    const container = byId("run-queue");
    if (!items.length) {
      container.innerHTML = '<div class="empty-state">No runs yet. Start with a bounded objective, then inspect the evidence trail here.</div>';
      return;
    }
    container.innerHTML = items.map((item) => `
      <button class="queue-item ${item.id === state.selectedRunId ? "active" : ""}" data-run-id="${item.id}" type="button">
        <p class="queue-title">${escapeHtml(item.objective)}</p>
        <div class="meta-row">
          <span class="meta-pill" data-tone="${statusTone(item.status)}">${escapeHtml(formatLabel(item.status))}</span>
          <span class="meta-pill">${escapeHtml(item.updated_at)}</span>
        </div>
      </button>
    `).join("");
    container.querySelectorAll("[data-run-id]").forEach((node) => {
      node.addEventListener("click", () => {
        loadRun(node.getAttribute("data-run-id"));
      });
    });
  }

  function renderTimeline(items, typeKey, textBuilder) {
    if (!items.length) {
      return '<div class="empty-state">No events recorded yet.</div>';
    }
    return items.map((item) => `
      <article class="timeline-item">
        <p class="timeline-title">${escapeHtml(formatLabel(item[typeKey]))}</p>
        <p class="timeline-copy">${escapeHtml(textBuilder(item))}</p>
      </article>
    `).join("");
  }

  function renderApprovals(items) {
    if (!items.length) {
      return '<div class="empty-state">Approval requests appear here once a run needs a human decision.</div>';
    }
    return items.map((item) => `
      <article class="approval-card">
        <div class="approval-head">
          <div>
            <h4>Approval ${escapeHtml(item.id.slice(0, 8))}</h4>
            <p class="approval-copy">${escapeHtml(item.reason)}</p>
          </div>
          <span class="meta-pill" data-tone="${statusTone(item.status)}">${escapeHtml(formatLabel(item.status))}</span>
        </div>
        <p class="approval-meta">Requested by ${escapeHtml(item.requested_by_user_id)} at ${escapeHtml(item.created_at)}</p>
        <p class="approval-meta">${item.decided_at ? `Decided at ${escapeHtml(item.decided_at)} by ${escapeHtml(item.approved_by_user_id || "unknown")}` : "Waiting for an admin decision."}</p>
      </article>
    `).join("");
  }

  function renderRun(runView) {
    state.runView = runView;
    state.selectedRunId = runView.run.id;
    const approval = latestApproval();
    byId("run-headline").textContent = runView.run.objective;
    byId("run-created").textContent = runView.run.created_at;
    byId("run-updated").textContent = runView.run.updated_at;
    byId("ops-resume-status").textContent = runView.run.status;
    byId("inspector-run-status").textContent = runView.run.status;
    byId("overview-input").textContent = formatJson(runView.run.input_payload);
    byId("overview-output").textContent = formatJson(runView.run.output_payload);
    byId("overview-approvals").textContent = String((runView.approvals || []).length);
    byId("checkpoint-list").innerHTML = renderTimeline(runView.checkpoints, "type", (item) => item.created_at);
    byId("audit-list").innerHTML = renderTimeline(
      runView.audit_events,
      "type",
      (item) => item.created_at + (item.operation_id ? ` | ${item.operation_id}` : "")
    );
    byId("approval-latest-status").textContent = approval ? formatLabel(approval.status) : "none";
    byId("approval-latest-status").dataset.tone = statusTone(approval?.status || "");
    byId("approval-summary-banner").dataset.tone = approval?.status === "denied" ? "error" : approval?.status === "approved" ? "success" : "warn";
    byId("approval-summary-banner").textContent = approvalSummaryText(approval);
    byId("approval-list").innerHTML = renderApprovals(runView.approvals || []);
    syncRunControls();
    updateInspectorTab(state.inspectorTab);
    setAppView("inspector");
  }

  async function refreshHealth() {
    try {
      const payload = await requestJson("/health");
      renderHealth(payload.status || "unknown");
    } catch (error) {
      byId("health-chip").dataset.tone = "error";
      byId("health-chip").textContent = "Offline";
      byId("health-summary").textContent = "The browser could not complete the health check.";
    }
  }

  async function loadRuns() {
    if (!state.sessionToken) {
      renderRuns([]);
      return;
    }
    try {
      const payload = await requestJson("/runs?limit=8", {
        headers: { "X-Session-Token": state.sessionToken },
      });
      renderRuns(payload.items || []);
    } catch (error) {
      if (isUnauthorizedError(error)) {
        clearSession("Session expired while loading the run queue. Start a fresh operator session.", "warn");
        return;
      }
      setBanner(`Run queue refresh failed. ${error.message}`, "error");
    }
  }

  async function loadRun(runId) {
    if (!state.sessionToken || !runId) {
      return;
    }
    try {
      const payload = await requestJson(`/runs/${runId}`, {
        headers: { "X-Session-Token": state.sessionToken },
      });
      renderRun(payload);
      await loadRuns();
    } catch (error) {
      if (isUnauthorizedError(error)) {
        clearSession("Session expired while loading run evidence. Start a fresh operator session.", "warn");
        return;
      }
      setBanner(error.message, "error");
    }
  }

  async function restoreSession() {
    const token = localStorage.getItem(storageKeys.token) || "";
    if (!token) {
      clearSession();
      return;
    }
    try {
      const session = await fetchSessionContext(token);
      if (session.authenticated === false) {
        clearSession("Stored session expired. Start a fresh operator session.", "warn");
        return;
      }
      syncMetrics(session.metrics);
      applySession(
        token,
        String(session.display_name || session.username || "operator"),
        String(session.role || "operator")
      );
      await loadRuns();
    } catch (error) {
      clearSession("Stored session could not be restored because the control plane is unavailable.", "error");
    }
  }

  async function handleCreateUser(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form).entries());
    try {
      await requestJson("/auth/local/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      state.metrics.users += 1;
      updateMetric("users", state.metrics.users);
      byId("session-username").value = String(payload.username || "");
      setBanner("Operator created. Start a session to enter the run workspace.", "success");
      form.reset();
    } catch (error) {
      setBanner(error.message, "error");
    }
  }

  async function handleCreateSession(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form).entries());
    try {
      const result = await requestJson("/auth/local/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      applySession(
        result.session_token,
        String(result.display_name || result.username || payload.username || "operator"),
        String(result.role || "operator")
      );
      await loadRuns();
    } catch (error) {
      setBanner(error.message, "error");
    }
  }

  async function handleCreateRun(event) {
    event.preventDefault();
    if (!state.sessionToken) {
      setBanner("Start a session before creating runs.", "warn");
      return;
    }
    const objective = byId("objective").value.trim();
    const payloadText = byId("input-payload").value.trim();
    let inputPayload = {};
    try {
      inputPayload = payloadText ? JSON.parse(payloadText) : {};
    } catch (error) {
      setBanner("Input payload must be valid JSON.", "error");
      return;
    }
    try {
      const result = await requestJson("/runs", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Token": state.sessionToken,
        },
        body: JSON.stringify({ objective, input_payload: inputPayload }),
      });
      state.metrics.runs += 1;
      updateMetric("runs", state.metrics.runs);
      setBanner("Run created. The inspector is ready with live controls for the new workflow.", "success");
      await loadRun(result.run_id);
    } catch (error) {
      if (isUnauthorizedError(error)) {
        clearSession("Session expired while creating a run. Start a fresh operator session.", "warn");
        return;
      }
      setBanner(error.message, "error");
    }
  }

  async function handleOpenSelectedRun() {
    if (!state.sessionToken || !state.selectedRunId) {
      setBanner("Select a run before opening the inspector.", "warn");
      return;
    }
    await loadRun(state.selectedRunId);
  }

  function resolveActionReason(fallback) {
    const value = byId("action-reason").value.trim();
    return value || fallback;
  }

  async function submitRunAction(path, reason, successMessage) {
    if (!state.sessionToken || !state.selectedRunId) {
      setBanner("Select a run before performing operator actions.", "warn");
      return;
    }
    try {
      await requestJson(`/runs/${state.selectedRunId}/${path}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Token": state.sessionToken,
        },
        body: JSON.stringify({ reason }),
      });
      setBanner(successMessage, "success");
      await loadRun(state.selectedRunId);
    } catch (error) {
      if (isUnauthorizedError(error)) {
        clearSession("Session expired while applying a workflow action. Start a fresh operator session.", "warn");
        return;
      }
      setBanner(error.message, "error");
    }
  }

  async function handleResumeRun() {
    await submitRunAction(
      "resume",
      resolveActionReason("Operator approved continuation from the inspector."),
      "Run resumed. Evidence has been refreshed."
    );
  }

  async function handleInterruptRun() {
    await submitRunAction(
      "interrupt",
      resolveActionReason("Operator paused the run for review."),
      "Run interrupted. The inspector now reflects the paused state."
    );
  }

  async function handleRetryRun() {
    await submitRunAction(
      "retry",
      resolveActionReason("Operator requested a clean retry."),
      "Run moved back to pending for a controlled retry."
    );
  }

  async function handleCancelRun() {
    await submitRunAction(
      "cancel",
      resolveActionReason("Operator canceled the run from the workbench."),
      "Run canceled. Audit evidence has been updated."
    );
  }

  async function handleRequestApproval() {
    await submitRunAction(
      "request-approval",
      resolveActionReason("Sensitive action requires explicit approval."),
      "Approval requested. The run is now waiting for a decision."
    );
  }

  async function submitApprovalDecision(approve) {
    const approval = latestApproval();
    if (!state.sessionToken || !approval) {
      setBanner("There is no approval request to decide.", "warn");
      return;
    }
    try {
      await requestJson(`/approvals/${approval.id}/decide`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Session-Token": state.sessionToken,
        },
        body: JSON.stringify({
          approve,
          reason: resolveActionReason(
            approve ? "Admin approved continuation from the inspector." : "Admin denied continuation from the inspector."
          ),
        }),
      });
      setBanner(
        approve ? "Approval granted. The run can now resume." : "Approval denied. Resume is now blocked by policy.",
        approve ? "success" : "warn"
      );
      await loadRun(state.selectedRunId);
    } catch (error) {
      if (isUnauthorizedError(error)) {
        clearSession("Session expired while deciding approval. Start a fresh operator session.", "warn");
        return;
      }
      setBanner(error.message, "error");
    }
  }

  async function handleSignOut() {
    const token = state.sessionToken;
    if (!token) {
      clearSession();
      setAppView("access");
      return;
    }
    try {
      await requestJson("/auth/session/logout", {
        method: "POST",
        headers: { "X-Session-Token": token },
      });
      clearSession("Operator session closed.", "success");
    } catch (error) {
      if (isUnauthorizedError(error)) {
        clearSession("Stored session was already invalid. Local session cleared.", "warn");
      } else {
        clearSession("Local session cleared, but server logout could not be confirmed.", "warn");
      }
    }
    setAppView("access");
  }

  window.addEventListener("DOMContentLoaded", async () => {
    byId("create-user-form").addEventListener("submit", handleCreateUser);
    byId("create-session-form").addEventListener("submit", handleCreateSession);
    byId("create-run-form").addEventListener("submit", handleCreateRun);
    byId("open-selected-run-button").addEventListener("click", handleOpenSelectedRun);
    byId("resume-run-button").addEventListener("click", handleResumeRun);
    byId("interrupt-run-button").addEventListener("click", handleInterruptRun);
    byId("retry-run-button").addEventListener("click", handleRetryRun);
    byId("cancel-run-button").addEventListener("click", handleCancelRun);
    byId("request-approval-button").addEventListener("click", handleRequestApproval);
    byId("approve-button").addEventListener("click", () => {
      void submitApprovalDecision(true);
    });
    byId("deny-button").addEventListener("click", () => {
      void submitApprovalDecision(false);
    });
    byId("sign-out-button").addEventListener("click", () => {
      void handleSignOut();
    });
    byId("back-to-runs-button").addEventListener("click", () => {
      setAppView("runs");
    });
    document.querySelectorAll("[data-tab-target]").forEach((node) => {
      node.addEventListener("click", () => {
        updateInspectorTab(node.getAttribute("data-tab-target"));
      });
    });
    document.querySelectorAll("[data-rail-target]").forEach((node) => {
      node.addEventListener("click", () => {
        const target = node.getAttribute("data-rail-target");
        if (node.disabled) {
          return;
        }
        setAppView(target);
      });
    });
    resetInspector();
    setAppView("overview");
    await refreshHealth();
    await restoreSession();
  });
</script>
"""


def _render_metric_card(key: str, label: str, copy: str, value: int) -> str:
    return (
        '<article class="metric-card">'
        f'<p class="metric-label">{escape(label)}</p>'
        f'<div class="metric-value" data-metric="{escape(key)}">{value}</div>'
        f'<p class="metric-copy">{escape(copy)}</p>'
        "</article>"
    )


def _render_job_card(index: str, title: str, copy: str) -> str:
    return (
        '<article class="job-card">'
        f'<span class="job-index">{escape(index)}</span>'
        f"<h4>{escape(title)}</h4>"
        f'<p class="job-copy">{escape(copy)}</p>'
        "</article>"
    )


def _render_helper_item(title: str, copy: str) -> str:
    return (
        '<article class="helper-item">'
        f'<p class="helper-title">{escape(title)}</p>'
        f'<p class="helper-copy">{escape(copy)}</p>'
        "</article>"
    )


def _render_detail_block(label: str, element_id: str, default_value: str) -> str:
    return (
        '<div class="detail-block">'
        f'<p class="detail-label">{escape(label)}</p>'
        f'<div class="detail-value" id="{escape(element_id)}">{escape(default_value)}</div>'
        "</div>"
    )


def _render_rail() -> str:
    return (
        '<aside class="rail">'
        '<div class="rail-header">'
        '<div class="rail-brand"><div class="brand-mark" aria-hidden="true"></div><div>'
        '<p class="eyebrow">Workspace</p><p class="rail-title">AgentKinetics</p></div></div>'
        '<p class="rail-copy">A desktop workbench for local-first agent operations with visible evidence and explicit approvals.</p>'
        "</div>"
        '<nav class="rail-section" aria-label="Primary">'
        '<p class="metric-label">Navigate</p>'
        '<div class="rail-nav">'
        '<button type="button" class="rail-item active" data-rail-target="overview" aria-current="page">Overview</button>'
        '<button type="button" class="rail-item" data-rail-target="access">Access</button>'
        '<button type="button" class="rail-item" data-rail-target="runs" data-requires-session="true">Runs</button>'
        '<button type="button" class="rail-item" data-rail-target="inspector" data-requires-session="true">Inspector</button>'
        "</div></nav>"
        '<div class="rail-section">'
        '<p class="metric-label">Session</p>'
        '<div class="panel rail-panel">'
        '<p class="rail-title" id="rail-session-name">No active operator</p>'
        '<p class="rail-copy" id="rail-session-copy">Create or open a session to unlock run operations.</p>'
        '<div class="inline-row"><span class="meta-pill" id="rail-session-role" data-tone="neutral">none</span></div>'
        "</div></div>"
        '<div class="rail-section">'
        '<p class="metric-label">Workflow model</p>'
        '<div class="panel rail-panel">'
        '<p class="rail-title">Compose, inspect, approve</p>'
        '<p class="rail-copy">Runs is for composition. Inspector is for evidence and lifecycle decisions. Nothing sensitive advances without context.</p>'
        "</div></div>"
        "</aside>"
    )


def _render_header() -> str:
    return (
        '<header class="topbar">'
        '<div class="brand">'
        '<div class="brand-mark" aria-hidden="true"></div>'
        "<div>"
        '<p class="eyebrow">Private agent operations</p>'
        "<h1>AgentKinetics Workbench</h1>"
        '<p class="lede">Bootstrap an operator, create a bounded run, and control every lifecycle change with evidence in view.</p>'
        "</div></div>"
        '<div class="header-chips">'
        '<span class="status-pill" id="health-chip" data-tone="warn">Checking core</span>'
        '<span class="status-pill" id="stream-chip" data-tone="warn">Live sync offline</span>'
        '<span class="chip" id="session-chip">Session required</span>'
        '<span class="chip" id="session-role-chip">Role: none</span>'
        '<button id="sign-out-button" type="button" class="ghost-button" disabled>Sign out</button>'
        "</div>"
        "</header>"
        '<div class="banner" id="status-banner" data-tone="success" role="status" aria-live="polite">AgentKinetics core is ready for operations.</div>'
    )


def _render_overview_metrics() -> str:
    return (
        '<div class="metric-grid">'
        f'{_render_metric_card("tenants", "Tenants", "Single source of truth across environments.", 0)}'
        f'{_render_metric_card("users", "Operators", "Local identities with explicit sessions.", 0)}'
        f'{_render_metric_card("runs", "Runs", "Durable workflows with checkpoints and replay.", 0)}'
        '<article class="metric-card">'
        '<p class="metric-label">Health</p>'
        '<div class="metric-value">Live</div>'
        '<p class="metric-copy" id="health-summary">The browser is validating the core services now.</p>'
        "</article>"
        "</div>"
    )


def _render_intro() -> str:
    return (
        '<section class="view active view-shell" data-app-view="overview" aria-labelledby="overview-title">'
        '<div class="hero-grid">'
        '<article class="hero-card">'
        '<p class="eyebrow">Product framing</p>'
        '<h2 id="overview-title">Evidence-first orchestration for real operator workflows.</h2>'
        '<p class="section-copy">The workbench is structured around operator jobs, not generic dashboard chrome. Access is separated from execution, runs stay bounded, and the inspector makes state changes legible before they happen.</p>'
        '<div class="job-strip">'
        f'{_render_job_card("1", "Bootstrap access", "Create a local operator and establish a live session.")}'
        f'{_render_job_card("2", "Launch a run", "Submit a bounded objective with structured input payload.")}'
        f'{_render_job_card("3", "Review evidence", "Inspect checkpoints, audit events, inputs, and outputs.")}'
        f'{_render_job_card("4", "Continue safely", "Resume only after an operator reviews the current state.")}'
        "</div>"
        "</article>"
        '<aside class="surface-stack">'
        '<article class="panel">'
        '<div class="section-head"><div><p class="eyebrow">Operator point of view</p><h3>One destination per decision</h3></div><span class="meta-pill">Desktop first</span></div>'
        '<div class="helper-list">'
        f'{_render_helper_item("Overview frames the system", "Explain what the platform does, what is live, and what the operator can trust before any action starts.")}'
        f'{_render_helper_item("Access handles identity only", "Account creation and session start stay isolated from workflow creation so auth is never mixed into the mission composer.")}'
        f'{_render_helper_item("Runs stays focused on composition", "The main operation surface keeps queue monitoring next to run creation without collapsing evidence into the same panel.")}'
        f'{_render_helper_item("Inspector owns decision-making", "Checkpoints, audit history, payloads, and approvals live next to lifecycle controls instead of being buried across the page.")}'
        "</div>"
        "</article>"
        '<article class="panel">'
        '<div class="section-head"><div><p class="eyebrow">Live system</p><h3>State at a glance</h3></div><span class="meta-pill">Responsive</span></div>'
        f"{_render_overview_metrics()}"
        "</article>"
        "</aside>"
        "</div>"
        "</section>"
    )


def _render_setup_view() -> str:
    return (
        '<section class="view view-shell" data-app-view="access" aria-labelledby="access-title">'
        '<div class="surface-grid access-grid">'
        '<article class="panel access-panel">'
        '<div class="section-head"><div><p class="eyebrow">First run</p><h3 id="access-title">Set up local operator access</h3></div>'
        '<span class="meta-pill">Identity first</span></div>'
        '<p class="section-copy">Authentication is a separate job from mission execution. This surface only handles operator identity and the minimum information needed to establish trust locally.</p>'
        '<div class="helper-list compact">'
        f'{_render_helper_item("Why this is separate", "Access work stays isolated so the run composer never becomes a login form in disguise.")}'
        f'{_render_helper_item("What unlocks next", "A valid session activates the Runs and Inspector destinations and starts live state sync.")}'
        "</div>"
        '<div class="panel-scroll"><form id="create-user-form">'
        '<div class="field-grid">'
        '<label><span class="field-label">Username</span><input name="username" minlength="3" maxlength="64" autocomplete="username" placeholder="operator-local" required /></label>'
        '<label><span class="field-label">Display name</span><input name="display_name" minlength="1" maxlength="128" autocomplete="name" placeholder="Local Operator" required /></label>'
        "</div>"
        '<div class="field-grid">'
        '<label><span class="field-label">Password</span><input name="password" type="password" minlength="8" maxlength="256" autocomplete="new-password" placeholder="Create a strong local password" required /></label>'
        '<label><span class="field-label">Role</span><select name="role"><option value="admin" selected>admin</option><option value="operator">operator</option></select></label>'
        "</div>"
        '<div class="action-row"><button type="submit">Create operator</button></div>'
        "</form></div>"
        "</article>"
        '<article class="panel session-panel">'
        '<div class="section-head"><div><p class="eyebrow">Session</p><h3>Enter the run workspace</h3></div>'
        '<span class="meta-pill" id="setup-session-summary">No active operator session</span></div>'
        '<p class="section-copy">Start a local session to move from setup into live workflow operations. Session state is restored quietly when the token is still valid.</p>'
        '<div class="panel-scroll"><form id="create-session-form">'
        '<label><span class="field-label">Username</span><input id="session-username" name="username" autocomplete="username" placeholder="operator-local" required /></label>'
        '<label><span class="field-label">Password</span><input name="password" type="password" autocomplete="current-password" placeholder="Enter the operator password" required /></label>'
        '<div class="action-row"><button type="submit" class="secondary-button">Start session</button></div>'
        "</form>"
        '<div class="banner" data-tone="warn"><strong>Session token:</strong> <span id="session-token">No active operator session.</span></div>'
        f'{_render_helper_item("Live session behavior", "The rail, queue, and inspector react to server state once the session is active. Sign out should revoke the server-side session, not just hide it locally.")}'
        "</div>"
        "</article>"
        "</div>"
        "</section>"
    )


def _render_ops_view() -> str:
    return (
        '<section class="view view-shell workspace-shell" data-app-view="runs" aria-labelledby="runs-title">'
        '<div class="kpi-strip">'
        '<article class="kpi-card"><p class="metric-label">Current session</p><div class="metric-value" id="ops-session-summary">No active operator session</div><p class="kpi-copy">The active operator is remembered locally for this browser.</p></article>'
        '<article class="kpi-card"><p class="metric-label">Selected run state</p><div class="metric-value" id="ops-resume-status">idle</div><p class="kpi-copy">Lifecycle actions move into the inspector once a run is selected.</p></article>'
        '<article class="kpi-card"><p class="metric-label">Trust boundary</p><div class="metric-value">Visible</div><p class="kpi-copy">Inputs, outputs, checkpoints, and audit evidence stay inspectable.</p></article>'
        "</div>"
        '<div class="surface-grid runs-grid">'
        '<article class="panel composer-panel">'
        '<div class="section-head"><div><p class="eyebrow">Launch</p><h3 id="runs-title">Create a bounded run</h3></div>'
        '<span class="meta-pill">Primary job</span></div>'
        f'{_render_helper_item("Bounded composition", "Keep the objective explicit and the payload structured so the resulting run remains inspectable and resumable later.")}'
        '<div class="panel-scroll"><form id="create-run-form">'
        '<label><span class="field-label">Objective</span><textarea id="objective" autocomplete="off" placeholder="Describe the outcome you want from this run." required>Design a resilient offline workflow for a private agent system.</textarea></label>'
        '<label><span class="field-label">Input payload JSON</span><textarea id="input-payload" spellcheck="false" placeholder="{ }">{\n  "priority": "high",\n  "mode": "offline",\n  "owner": "solo-architect"\n}</textarea></label>'
        '<div class="action-row"><button id="create-run-button" type="submit" disabled>Create run</button></div>'
        "</form></div>"
        "</article>"
        '<article class="panel queue-panel">'
        '<div class="section-head"><div><p class="eyebrow">Queue</p><h3>Recent runs</h3></div>'
        '<span class="meta-pill">One click to inspect</span></div>'
        '<div class="queue-actions"><p class="helper-copy">Select a run to move into the dedicated inspector surface.</p><button id="open-selected-run-button" type="button" class="secondary-button" disabled>Open selected run</button></div>'
        '<div class="queue-list" id="run-queue"><div class="empty-state">No runs yet. Start with a bounded objective, then inspect the evidence trail here.</div></div>'
        "</article>"
        "</div>"
        "</section>"
    )


def _render_inspector_view() -> str:
    return (
        '<section class="view view-shell workspace-shell" data-app-view="inspector" aria-labelledby="run-headline">'
        '<div class="surface-grid inspector-grid">'
        '<article class="panel evidence-panel">'
        '<div class="section-head"><div><p class="eyebrow">Inspector</p><h3 id="run-headline">Select a run to inspect evidence</h3></div>'
        '<div class="action-row"><span class="meta-pill">Inputs, outputs, checkpoints, audit</span><button id="back-to-runs-button" type="button" class="ghost-button">Back to runs</button></div></div>'
        '<div class="detail-grid">'
        f'{_render_detail_block("Created", "run-created", "-")}'
        f'{_render_detail_block("Updated", "run-updated", "-")}'
        f'{_render_detail_block("Status", "inspector-run-status", "idle")}'
        f'{_render_detail_block("Approvals", "overview-approvals", "0")}'
        "</div>"
        '<div class="tab-row" role="tablist" aria-label="Run evidence views"><button type="button" class="tab-button active" data-tab-target="overview" role="tab" aria-selected="true">Overview</button><button type="button" class="tab-button" data-tab-target="checkpoints" role="tab" aria-selected="false">Checkpoints</button><button type="button" class="tab-button" data-tab-target="audit" role="tab" aria-selected="false">Audit</button><button type="button" class="tab-button" data-tab-target="approvals" role="tab" aria-selected="false">Approvals</button></div>'
        '<div class="tab-stage">'
        '<div class="tab-panel active" data-tab-panel="overview" role="tabpanel">'
        '<div class="control-grid"><div><p class="field-label">Input payload</p><pre id="overview-input">{}</pre></div><div><p class="field-label">Output payload</p><pre id="overview-output">{}</pre></div></div>'
        "</div>"
        '<div class="tab-panel" data-tab-panel="checkpoints" role="tabpanel"><div class="timeline-list" id="checkpoint-list"><div class="empty-state">Choose a run from the queue to review checkpoints.</div></div></div>'
        '<div class="tab-panel" data-tab-panel="audit" role="tabpanel"><div class="timeline-list" id="audit-list"><div class="empty-state">Audit evidence appears once a run is selected.</div></div></div>'
        '<div class="tab-panel" data-tab-panel="approvals" role="tabpanel"><div class="approval-stack" id="approval-list"><div class="empty-state">Approval requests appear here once a run needs a human decision.</div></div></div>'
        "</div>"
        "</article>"
        '<aside class="panel control-panel">'
        '<div class="section-head"><div><p class="eyebrow">Operator controls</p><h3>Drive the selected workflow</h3></div><span class="meta-pill" id="approval-latest-status" data-tone="neutral">none</span></div>'
        '<p class="section-copy">Actions are scoped to the selected run and require an explicit reason so audit evidence stays readable later.</p>'
        '<div class="banner" id="approval-summary-banner" data-tone="warn">No approval is active for this run.</div>'
        '<div class="control-stack">'
        '<label><span class="field-label">Action reason</span><textarea id="action-reason" class="compact-textarea" placeholder="Add the operator reason for the next lifecycle change or approval decision."></textarea></label>'
        '<div class="button-cluster">'
        '<button id="resume-run-button" type="button">Resume</button>'
        '<button id="interrupt-run-button" type="button" class="secondary-button">Interrupt</button>'
        '<button id="retry-run-button" type="button" class="secondary-button">Retry</button>'
        '<button id="request-approval-button" type="button" class="warn-button">Request approval</button>'
        '<button id="cancel-run-button" type="button" class="danger-button">Cancel</button>'
        "</div>"
        '<div class="button-cluster" id="approval-decision-row" hidden>'
        '<button id="approve-button" type="button" class="success-button">Approve</button>'
        '<button id="deny-button" type="button" class="danger-button">Deny</button>'
        "</div>"
        '<div class="helper-list compact">'
        f'{_render_helper_item("Lifecycle discipline", "Resume, interrupt, retry, cancel, and approval requests all attach an explicit reason so later audit review stays readable.")}'
        f'{_render_helper_item("Approval posture", "Admin decisions stay hidden until an approval request is actually pending, reducing noise during normal run review.")}'
        "</div>"
        "</div>"
        "</aside>"
        "</div>"
        "</section>"
    )


def render_product_shell(initial_metrics: Mapping[str, int] | None = None) -> str:
    metrics_json = json.dumps(_normalize_metrics(initial_metrics or {}))
    return (
        "<!DOCTYPE html>"
        '<html lang="en"><head><meta charset="utf-8" />'
        '<meta name="viewport" content="width=device-width, initial-scale=1" />'
        "<title>AgentKinetics Workbench</title>"
        f"{_STYLE}</head>"
        '<body><div class="shell" id="shell" data-mode="setup">'
        f"{_render_rail()}<main class=\"content-shell\">{_render_header()}{_render_intro()}{_render_setup_view()}{_render_ops_view()}{_render_inspector_view()}</main>"
        f"<script>\n  const INJECTED_METRICS = {metrics_json};\n</script>"
        f"{_SCRIPT}"
        "</div></body></html>"
    )
