"""Paths, fixed source registry, and constants for the W01 feasibility spike.

This module contains no credentials and performs no I/O.
"""

from __future__ import annotations

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
SPIKE_DIR = PACKAGE_DIR.parent
PROJECT_ROOT = SPIKE_DIR.parents[1]

LOCAL_DIR = PROJECT_ROOT / ".local" / "w01"
SOURCE_DIR = LOCAL_DIR / "sources"
PAGE_DIR = LOCAL_DIR / "pages"
RESULT_DIR = LOCAL_DIR / "results"
LOG_DIR = LOCAL_DIR / "logs"
PROVIDER_DIR = RESULT_DIR / "provider"

EVIDENCE_DIR = PROJECT_ROOT / "docs" / "evidence" / "W01"
MANIFEST_DIR = PROJECT_ROOT / "fixtures" / "manifests" / "w01"

MANIFEST_PATH = MANIFEST_DIR / "sources.json"
ENVIRONMENT_PATH = EVIDENCE_DIR / "ENVIRONMENT.json"
REPORT_PATH = EVIDENCE_DIR / "FEASIBILITY_REPORT.md"

PROMPT_DIR = SPIKE_DIR / "prompts"
FIXTURE_DIR = SPIKE_DIR / "fixtures"
SCHEMA_DIR = SPIKE_DIR / "schemas"

DOCS_DIR = PROJECT_ROOT / "docs"

#: Codex-verified public text pricing record for the W01 repair (read-only input).
PRICING_EVIDENCE_PATH = DOCS_DIR / "execution" / "reviews" / "W01-pricing-evidence.json"

#: Repair baseline used for this attempt's protected-hash checks.
REPAIR_BASELINE_PATH = DOCS_DIR / "execution" / "baselines" / "W01-live-v4-baseline.json"

# ---------------------------------------------------------------------------
# Frozen coordinate / schema conventions (documented in spikes/w01/README.md)
# ---------------------------------------------------------------------------
COORDINATE_SYSTEM = "top_left_x_right_y_down_normalized"
ANCHOR_SCHEMA_VERSION = 1
MANIFEST_SCHEMA_VERSION = 1
DRAFT_SCHEMA_VERSION = 1

#: Bounding boxes are normalized to [0, 1] of the rendered page box.
BBOX_EPSILON = 1e-6

# ---------------------------------------------------------------------------
# Approved source candidates. URLs are the contract's public URLs; no
# credentials, query tokens, or account paths are attached.
# ---------------------------------------------------------------------------
ST_ERRATA = {
    "source_key": "st-es0620",
    "url": (
        "https://www.st.com/resource/en/errata_sheet/"
        "es0620-stm32n6xxxx-device-errata-stmicroelectronics.pdf"
    ),
    "manufacturer": "STMicroelectronics",
    "document_id": "ES0620",
    "kind": "manufacturer_document",
    "authority": "Manufacturer errata sheet for STM32N6xxxx devices",
    "local_filename": "st-es0620.pdf",
    "mandatory": True,
}

NXP_NOTICE = {
    "source_key": "nxp-pcn-202609010I",
    "url": "https://www.nxp.com/pcn/202609010I",
    "manufacturer": "NXP",
    "document_id": "202609010I",
    "kind": "manufacturer_notice",
    "authority": "Manufacturer product change notice landing page (metadata only)",
    "local_filename": "nxp-pcn-202609010I.html",
    "mandatory": False,
}

ST_COMMUNITY_THREAD = {
    "source_key": "st-community-nrst-thread",
    "url": (
        "https://community.st.com/stm32-mcus-products-25/"
        "stm32n657-revision-b-nrst-workaround-without-an-initial-software-reset-168780"
    ),
    "manufacturer": "STMicroelectronics community",
    "document_id": "168780",
    "kind": "forum_clarification",
    "authority": "Community thread (clarification only; not manufacturer authority)",
    "local_filename": "st-community-nrst-thread.html",
    "mandatory": False,
}

SOURCE_SPECS = (ST_ERRATA, NXP_NOTICE, ST_COMMUNITY_THREAD)

#: Document IDs of the bounded subset selected for parsing. The section numbers
#: are candidates from the packet; the parser locates them by document content
#: and records the actual page indexes it finds.
SELECTED_SECTIONS = ("2.2.18", "2.2.5")

#: Candidate provider configuration from docs/execution/contracts/provider-and-sources.md.
PROVIDER = {
    "base_url": "https://api.tokenfactory.nebius.com/v1/",
    "model_id": "nvidia/Nemotron-3.5-Super-VL",
    "api_key_env": "NEBIUS_API_KEY",
    "models_path": "models",
    "chat_path": "chat/completions",
    "docs": {
        "quickstart": "https://docs.tokenfactory.nebius.com/quickstart",
        "json": "https://docs.tokenfactory.nebius.com/ai-models-inference/json",
        "models": "https://docs.tokenfactory.nebius.com/public-serverless",
    },
}

#: Documented provider aliases for the configured model. Empty means only the
#: exact configured model ID is accepted; add an entry only with a cited mapping.
MODEL_ALIAS_MAP: dict[str, str] = {}

#: W01 caps; user approved 3 -> 4 lifetime requests on 29 October 2026.
BUDGET = {
    "max_requests": 4,
    "max_input_tokens_per_request": 16_000,
    "max_output_tokens_per_request": 8_192,
    "max_estimated_spend_usd": 0.25,
}

USER_AGENT = "ErrataScope-W01-feasibility/0.1 (local spike; single worker)"
HTTP_TIMEOUT_SECONDS = 60.0

#: Current worker attempt, recorded on command-log entries so reports can
#: distinguish this attempt's evidence from preserved earlier history.
WORKER_ATTEMPT = "W01-attempt-06"
WORKER_ATTEMPT_START_UTC = "2026-10-29T14:59:34Z"
