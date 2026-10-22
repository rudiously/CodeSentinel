# Security

Threat model: untrusted PR source/diffs, spoofed/replayed webhooks, leaked tokens, source-based injection, tampered model artifacts, dependency compromise, arbitrary URL/SSRF, CPU/memory/disk/input DoS. This is a single-installation research/demo service, not production multi-tenancy.

| Control | Current status and evidence |
|---|---|
| HMAC-SHA256 before JSON, constant-time comparison | IMPLEMENTED / TESTED: valid/invalid signatures, malformed signed JSON, unsupported-event replay |
| Delivery deduplication | PARTIAL: bounded TTL/locking, duplicate/retry tested; in-memory only, not durable or shared across workers |
| Never execute/import scanned source | IMPLEMENTED / TESTED: AST/static data only; marker-file regression confirms no execution. Action reads Git blobs without running them |
| Fixed scanner argv, temp dirs, no shell, timeout | IMPLEMENTED / MOCK-TESTED: normalization, missing-tool and timeout behavior; real Bandit/cppcheck unavailable |
| Size, file, function, batch, output limits | IMPLEMENTED / PARTLY TESTED: ASGI bytes, code/batch, diff count, source paths; output-file cap is checked after subprocess completion, not a hard disk quota |
| Rate limit and scan time budget | IMPLEMENTED: bounded single-process limiter; API 429 test. Time budget checked between functions; inference/tool timeout bounds individual calls. No distributed limiter or global worker quota |
| Environment secrets; no source/tokens in logs | IMPLEMENTED: metadata-only JSON logs, source-free error schemas, no access logs in container commands, hidden settings input in validation errors. Full third-party logging audit pending |
| Source minimization in DB | TESTED: source and token-importance text removed. External scanner messages reduced to rule/severity descriptions to avoid embedding credentials |
| Artifact SHA256 and safe paths | TESTED: manifests cover all files, symlink/path escape/hash mismatch rejected before loading; actual SMOKE model tampering rejected. Trusted manifest/distribution required; no signature attestation |
| JWT signature, issuer, audience, expiry | TESTED: required claims, expired/invalid tokens, dev-login switch; default auth required |
| Dev login disabled in production | TESTED: settings reject production dev login, weak JWT secret or disabled auth |
| GitHub OAuth CSRF and allowlist | FAKE-HTTP TESTED: HttpOnly SameSite state cookie, signature/expiry, fixed-origin code exchange, fragment session return/no-store. Production requires allowed numeric IDs. Live GitHub unverified |
| Primary Action workload identity | LOCAL CRYPTO/MOCK TESTED: RS256 GitHub issuer/JWKS, expiry/audience, PR subject/event and repo allowlist; /scan only, body repository binding. Real GitHub OIDC run pending |
| Restricted CORS | IMPLEMENTED by configured origin list; production deployment check pending |
| SSRF and HTTPS | IMPLEMENTED: fixed api.github.com/blob SHA paths; ignore payload URLs; fixed GitHub OIDC key URL; configured Action API requires HTTPS except loopback. Redirects disabled; no environment proxies in HTTP clients |
| Stable PR head | IMPLEMENTED: App path checks expected head before collection and before posting; live race verification pending |
| Non-root minimal pinned containers | DEFINED, NOT RUN: image tags/package versions and users set. Docker build/volume/runtime checks blocked |
| Python dependency audit | BLOCKED: pip_audit not installed, package installation unavailable. CI includes pip-audit, no clean audit claimed |
| npm dependency audit and lockfile | BLOCKED: npm install ENOTFOUND/ENOTCACHED; audit ENOLOCK. No lockfile or vulnerability result claimed |
| CI and releases | DEFINED / STATIC YAML CHECKED: no GitHub CI/build/publish run claimed; major action tags are mutable and immutable-SHA pinning remains hardening work |

Known gaps: users table exists but OAuth identity is currently represented in JWT subjects; user/repo ownership and tenant isolation are not enforced. Only allow trusted installation users. All installed repositories share a dashboard. Artifact authenticity, distributed quotas/deduplication, bounded disk quotas and full dependency remediation need work. Do not expose the unfinished demo publicly. Token fragments are stored in sessionStorage and are vulnerable to any same-origin XSS; React escaping and CSP reduce, not eliminate, that risk. Full browser/CSP verification is blocked.

Ethics and limitations (Project.md Document 17): no safety guarantee; false positives/negatives; retain human authority over merges; process source transiently; credit and review data/model licenses; learned non-C performance is unvalidated. Exact deduplication does not guarantee clone/repository separation. Earlier metrics are earlier run, not reproduced. STUB, SMOKE and SYNTHETIC are not trained-model security evidence.

## Selected repository write blocker (2026-10-22)
The user explicitly selected rudiously/CodeSentinel. Repository/account read metadata succeeds but the connected integration's initial contents write returns HTTP 403. No remote mutation or permission expansion occurred; local .git protections were not bypassed. See H11. Evaluation now rejects non-finite scores and ERROR decisions and counts actual safety-floor decisions, avoiding misleading PASS/metric claims.
