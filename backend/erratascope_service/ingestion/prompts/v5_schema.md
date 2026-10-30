{
  "schema_version": 1,
  "source_document_id": "<identity-anchor document ID, or null if absent>",
  "source_revision": "<identity-anchor document revision, or null if absent>",
  "claims": [
    {
      "field": "one of: source_identity | affected_device | affected_revision | trigger_condition | exception | consequence | workaround_documented | workaround_restriction | unresolved_field",
      "value": "<one source-supported statement, preserving qualifiers and section scope>",
      "citations": ["<one or more RELEVANT supplied anchor keys; never empty>"],
      "status": "supported or unresolved"
    }
  ],
  "unresolved_fields": ["<names of fields not established by the supplied evidence>"],
  "limitations": "<source-bounded draft; human review required; no safety/certification claim>"
}

The claims array contains only evidence-backed claims, not one entry for every possible field. If affected_device, exception or another field has no evidence, omit its claim and list its name in unresolved_fields. Do not create a duplicate unresolved_field claim with no citation. Null is JSON null, not the string "null". Retain at least one genuinely supported claim; never manufacture a claim just to fill the array.
