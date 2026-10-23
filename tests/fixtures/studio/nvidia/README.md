# NVIDIA private schema snapshot

`compact-v2-weighted.schema.json` captures the JSON Schema sent inside
`response_format.json_schema.schema`, without material, prompts or credentials.
It is unchanged from the contract at `88fdde7`; only the outer lesson request now
sets `strict=true`. The test compares the entire schema and checks local refs,
unions and required fields. No keyword or validation was removed.

This fixture verifies request preservation, not NVIDIA's hosted schema compiler.
See `docs/studio-nvidia-json-diagnosis.md` for public endpoint evidence and limits.
