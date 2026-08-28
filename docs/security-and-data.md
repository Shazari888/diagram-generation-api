# Security and Data

- Buyers must never send private keys or wallet seeds to the API.
- Seller secrets, facilitator credentials, and server secrets remain server-side.
- x402 verifies and settles the buyer’s signed payment through the configured facilitator.
- Prompts, generated source, and rendered outputs may be stored for retrieval and debugging.
- Logs may include request metadata and payment metadata.
- External rendering uses Mermaid-compatible and Kroki-compatible services for supported diagram types.
- Rate limits and abuse controls are enforced on public and paid routes.
- Report vulnerabilities through the GitHub issues tracker.
