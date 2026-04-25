# SDK Roadmap

## v1.1 (planned)

- [ ] Expose A2A protocol surface separately as `client.a2a.*` methods,
  even when implementation reuses MCP tool calls. Improves DX for
  A2A-first integrators. Currently all 24 A2A skills are accessible
  via the 67 flat methods (16 shared with MCP + 8 A2A-only), but
  A2A-focused developers expect a namespaced API.

## v1.0 (current)

- [x] 67 tool methods (59 MCP + 8 A2A-only)
- [x] Sync + async clients
- [x] Bearer auth, retry, exponential backoff
- [x] 150 unit tests
- [x] CI: test on push (3.10, 3.11, 3.12)
- [x] CI: publish to PyPI on tag
