import type {
  Anchor,
  CaseContext,
  Coverage,
  Draft,
  Page,
  Project,
  Review,
  ReviewHistory,
  ReviewSummary,
  SubmissionContext,
} from "./types";

export class ApiError extends Error {
  status: number;
  code: string;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

let token = "";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const response = await fetch(path, { ...init, headers });
  if (!response.ok) {
    let code = `HTTP_${response.status}`;
    let message = "The server rejected this request.";
    try {
      const body = (await response.json()) as { error?: { code?: string; message?: string } };
      code = body.error?.code ?? code;
      message = body.error?.message ?? message;
    } catch {
      /* non-JSON failure */
    }
    throw new ApiError(response.status, code, message);
  }
  return (await response.json()) as T;
}

async function allPages<T>(path: string): Promise<T[]> {
  const items: T[] = [];
  let cursor: string | null = null;
  for (let page = 0; page < 20; page += 1) {
    const separator = path.includes("?") ? "&" : "?";
    const suffix: string = cursor ? `${separator}cursor=${encodeURIComponent(cursor)}` : "";
    const result: Page<T> = await request<Page<T>>(`${path}${suffix}`);
    items.push(...result.items);
    cursor = result.next_cursor;
    if (!cursor) break;
  }
  return items;
}

export async function bootstrap(): Promise<void> {
  const session = await request<{ token: string; label: string }>("/api/v1/submission/dev-session");
  token = session.token;
}

export async function listProjects(): Promise<Project[]> {
  return allPages<Project>("/api/v1/projects");
}

export async function submissionContext(projectId: string): Promise<SubmissionContext> {
  return request<SubmissionContext>(`/api/v1/projects/${projectId}/submission-context`);
}

export async function getExtraction(extractionId: string): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/api/v1/extractions/${extractionId}`);
}

export async function getAnchors(extractionId: string): Promise<Anchor[]> {
  return allPages<Anchor>(`/api/v1/extractions/${extractionId}/anchors`);
}

export async function getCoverage(extractionId: string): Promise<Coverage[]> {
  return allPages<Coverage>(`/api/v1/extractions/${extractionId}/coverage`);
}

export async function getDraft(draftId: string): Promise<Draft> {
  return request<Draft>(`/api/v1/drafts/${draftId}`);
}

export async function getReviews(draftId: string): Promise<ReviewHistory> {
  const items: Review[] = [];
  let cursor: string | null = null;
  let current_revision = 0;
  do {
    const result: ReviewHistory = await request<ReviewHistory>(
      `/api/v1/drafts/${draftId}/interpretation-reviews?limit=100${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ""}`,
    );
    items.push(...result.items);
    current_revision = result.current_revision;
    cursor = result.next_cursor;
  } while (cursor);
  return { items, current_revision, next_cursor: null };
}

export async function getSummary(draftId: string): Promise<ReviewSummary> {
  return request<ReviewSummary>(`/api/v1/drafts/${draftId}/review-summary?format=json`);
}

export async function recordReview(
  draftId: string,
  payload: {
    expected_revision: number;
    expected_response_hash: string;
    decision: "reviewed" | "rejected";
    note: string;
  },
): Promise<{ review: Review; current_revision: number }> {
  return request(`/api/v1/drafts/${draftId}/interpretation-reviews`, {
    method: "POST",
    headers: { "Idempotency-Key": crypto.randomUUID().replaceAll("-", "") },
    body: JSON.stringify(payload),
  });
}

export async function downloadSummary(
  draftId: string,
  format: "json" | "markdown",
): Promise<void> {
  const response = await fetch(`/api/v1/drafts/${draftId}/review-summary?format=${format}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    let message = "Export failed.";
    try {
      const body = (await response.json()) as { error?: { message?: string } };
      message = body.error?.message ?? message;
    } catch {
      /* no JSON */
    }
    throw new ApiError(response.status, "EXPORT_FAILED", message);
  }
  const blob = await response.blob();
  const extension = format === "json" ? "json" : "md";
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `erratascope-review-${draftId.slice(0, 8)}.${extension}`;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export type { CaseContext };
