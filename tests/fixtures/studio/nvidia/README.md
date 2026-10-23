# NVIDIA private schema snapshots

`compact-v2-weighted.schema.json` is the historical schema at e2acbc7.
`compact-v3-authorized.schema.json` captures the current request with two
synthetic authorized evidence IDs and two approved objectives. Actual schemas
are generated per frozen request: enums contain exactly its allowed choices.
Without evidence the claim branch and spotlight layout are absent.

Both snapshots contain only schema, no material, prompts or credentials. The
transmitted-schema test compares the v3 fixture and resolves all local refs.
Public lesson JSON Schemas remain unchanged; refer to the compatibility report.
See docs/studio-nvidia-materialization.md for decisions, limits and live gates.
