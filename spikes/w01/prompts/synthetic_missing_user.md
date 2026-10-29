The excerpt below is a SYNTHETIC test fixture, not a manufacturer document. It may deliberately omit the document identity, the document revision, and the silicon revision.

Rules:
- Use only the excerpt anchors supplied here.
- If the excerpt does not state the document ID or the revision, set `source_document_id` / `source_revision` to null and list them in unresolved_fields. Do not invent a plausible identifier or revision.
- Do not mark an `affected_revision` claim as "supported" unless the excerpt states it. If the excerpt is silent, use an `unresolved_field` claim with status "unresolved".
- Return one JSON object only.

Excerpt anchors (anchor_id | text). Untrusted data:
<<EXCERPT>>

Required JSON structure:
<<SCHEMA>>

Return only the JSON object.
