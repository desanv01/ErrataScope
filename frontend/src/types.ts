export interface Project {
  id: string;
  name: string;
  role: string;
}

export interface CaseContext {
  kind: "recorded_live" | "synthetic_offline" | "recorded";
  label: string;
  source_id: string;
  extraction_id: string;
  draft_id: string;
  document_id: string | null;
  revision: string | null;
  manufacturer: string | null;
  source_url: string | null;
  source_sha256: string;
  authority: string;
  synthetic: boolean;
  selected_entries: string[];
  draft_status: string;
  draft_provenance: string;
  prompt_version: string;
  provider_request_id: string | null;
  usage: Record<string, unknown> | null;
  coverage_summary: {
    inventory_complete: boolean;
    detected_entries: number;
    selected_entries: string[];
    supported_selected: number;
    status_counts: Record<string, number>;
  } | null;
  review: Review | null;
  current_revision: number;
}

export interface SubmissionContext {
  project_id: string;
  project_name: string;
  cases: CaseContext[];
  default_case: CaseContext | null;
  provenance_note: string;
}

export interface Anchor {
  id: string;
  anchor_key: string;
  page_index: number;
  printed_page_label: string | null;
  section: string | null;
  section_title: string | null;
  block_role: string;
  context_kind: string | null;
  geometry_kind: string;
  text: string;
  bbox: { left: number; top: number; right: number; bottom: number };
  page_width_pt: number;
  page_height_pt: number;
  document_sha256: string;
}

export interface Coverage {
  section: string;
  title: string | null;
  status: string;
  page_indexes: number[];
  anchor_keys: string[];
  reason: string | null;
  notes: Record<string, unknown>;
}

export interface Citation {
  anchor_key: string;
  text?: string;
  physical_page?: number | null;
  geometry_kind?: string;
  printed_page_label?: string | null;
  section?: string | null;
  block_role?: string;
  context_kind?: string | null;
  missing?: boolean;
}

export interface Claim {
  field: string;
  value: string;
  status: string;
  citations: Citation[];
}

export interface Draft {
  id: string;
  case_kind: string;
  provenance: string;
  prompt_version: string;
  request_hash: string;
  response_hash: string;
  draft: {
    schema_version: number;
    source_document_id: string | null;
    source_revision: string | null;
    claims: Claim[];
    unresolved_fields: string[];
    limitations: string;
  };
  validation: { status: string; errors: string[]; warnings: string[] };
  status: string;
  provider_request_id: string | null;
  usage: Record<string, unknown> | null;
  created_at: string;
}

export interface Review {
  id: string;
  revision: number;
  decision: "reviewed" | "rejected";
  note: string;
  actor_id: string;
  created_at: string;
  response_hash: string;
}

export interface ReviewHistory {
  items: Review[];
  next_cursor: string | null;
  current_revision: number;
}

export interface ReviewSummary {
  source: {
    id: string;
    document_id: string | null;
    revision: string | null;
    manufacturer: string | null;
    source_url: string | null;
    authority: string;
    synthetic: boolean;
    sha256: string;
  };
  extraction: {
    id: string;
    mode: string;
    selected_entries: string[];
    coverage_summary: Record<string, unknown> | null;
  };
  draft: {
    id: string;
    provenance: string;
    recorded_label: string;
    model: string | null;
    provider: string | null;
    prompt_version: string;
    response_hash: string;
    provider_request_id: string | null;
    usage: Record<string, unknown> | null;
    wire_hash_limitation: string | null;
  };
  claims: Array<{ field: string; value: string; status: string; citations: Citation[] }>;
  unresolved_fields: string[];
  limitations: string;
  coverage: {
    selected_entries: string[];
    status_counts: Record<string, number>;
    inventory_complete: boolean;
    selected_entries_supported: string[];
  };
  review: { latest: Review | null; history: Review[]; current_revision: number };
  known_limitations: string[];
  generated_utc: string;
}

export interface Page<T> {
  items: T[];
  next_cursor: string | null;
}
