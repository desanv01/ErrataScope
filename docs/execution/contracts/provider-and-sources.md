# Provider and source contract — revision 1

## Candidate, not verified access

Candidate model: `nvidia/Nemotron-3.5-Super-VL`.
Candidate Nebius API base: `https://api.tokenfactory.nebius.com/v1/`.
Verify actual current official documentation and account response; do not claim access from a public announcement alone. If absent/unavailable, report candidates to Codex rather than silently changing the model/provider.

References:
- https://docs.tokenfactory.nebius.com/quickstart
- https://docs.tokenfactory.nebius.com/ai-models-inference/json
- https://nebius.com/blog/posts/three-new-open-weight-models-from-us-companies-give-builders-more-choice

Use a directly supplied `NEBIUS_API_KEY` process variable. Accept an explicitly user-supplied alternative variable mapping, recording only its name. Never search for credentials. No signup, purchase, promo-code redemption, or account modification.

## Core source candidates

- https://www.st.com/resource/en/errata_sheet/es0620-stm32n6xxxx-device-errata-stmicroelectronics.pdf
- https://www.nxp.com/pcn/202609010I
- https://community.st.com/stm32-mcus-products-25/stm32n657-revision-b-nrst-workaround-without-an-initial-software-reset-168780

Prior planning observed ES0620 Rev 5, 38 pages. Verify actual downloaded bytes and metadata. Relevant section candidates are 2.2.18 and 2.2.5; locate them by document contents, not assumed page offsets. Record discrepancies instead of rewriting history.

Manufacturer notices/forum clarifications have distinct authority. The NXP notice alone cannot establish full erratum conditions. Download authentic historic versions only from legitimate accessible sources. Otherwise label a controlled change fixture synthetic.

## Processing

Preserve bytes/hash, source metadata, parser provenance, page/text/table/footnote context, and anchor coordinates. Prefer Docling on the bounded source pages; pdfplumber is an allowed recorded fallback. Use a package-local environment. Scanned/vision support is optional until proved.

Model inputs are bounded source passages with anchor IDs and table context. Outputs are draft interpretations. Validate structure and anchor references; semantic fidelity requires review. No model tools or executable generated expressions.

Store exact request/response payloads privately with secrets removed, usage, finish reason, timing, prompt/schema versions, live/cache status. Keep public evidence to metadata and minimal necessary excerpts. Public document URLs do not authorize redistributing full PDFs.

