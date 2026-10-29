{
  "schema_version": 1,
  "source_document_id": "<document ID copied from the identity anchor, or null>",
  "source_revision": "<document revision copied from the identity anchor, or null>",
  "claims": [
    {
      "field": "one of: source_identity | affected_device | affected_revision | trigger_condition | exception | consequence | workaround_documented | workaround_restriction | unresolved_field",
      "statement": "<concise paraphrase, quoting register/bit names exactly as in the source>",
      "anchor_ids": ["<one or more supplied anchor IDs>"],
      "status": "supported or unresolved"
    }
  ],
  "unresolved_fields": ["<field names the anchors do not answer; use [] if none>"],
  "limitations": "<short note; must not claim safety or certification>"
}
