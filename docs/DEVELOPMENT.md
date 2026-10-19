# Development and Operations Protocol

> Proposed baseline; update commands and environment details after the implementation stack is selected.

## Before changing code

Read the root README and architecture decisions. Confirm the behavior, data classification, and acceptance criteria. Keep provider integrations behind explicit adapters and avoid embedding provider assumptions in domain logic.

## Implementation protocol

1. Define or update schemas for requests, persisted records, and queue messages.
2. Validate data at ingress and again after external-provider or model responses.
3. Add deterministic unit tests for normalization, deduplication, and scoring.
4. Add integration tests for persistence, queue recovery, provider timeouts, rate limits, and malformed responses.
5. Include tests for authorization, retention/deletion behavior, and SSRF controls before exposing URL-fetching functionality.
6. Keep retries bounded and make repeated job-stage execution safe.

## Local configuration

Provide a committed `.env.example` containing names and harmless placeholders only. Document each variable's purpose, required/optional status, and secret classification. Never commit real provider tokens, customer datasets, or raw enrichment responses.

## Observability and incident handling

Use a correlation ID across job stages. Record provider name, operation, duration, outcome, and retry count without logging full personal records. A failed stage must be inspectable and replayable only through an authorized, idempotent path. Document provider quota exhaustion, suspected data exposure, and queue backlog response procedures before production use.

## Pull request checklist

- [ ] Behavior and acceptance criteria are documented.
- [ ] Inputs and provider/model outputs are validated.
- [ ] Authorization, privacy, and retention implications are reviewed.
- [ ] Tests cover success, failure, and retry paths.
- [ ] Logs and metrics avoid sensitive data and include useful correlation.
- [ ] Documentation, migrations, and configuration examples match the change.
- [ ] Rollback or recovery steps are clear for stateful changes.
