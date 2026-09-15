# Formal 17897 Model Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent the supervisor from declaring a candidate `ready` when it only passed an isolated probe but fails real model generation through the promoted production listener `127.0.0.1:17897`.

**Architecture:** Keep the existing isolated candidate probe as the non-disruptive first gate. After a candidate is promoted to the formal listener, run the same bounded `agy` real-generation gate through `17897`; only then persist success and attach/start Antigravity. A formal-gate failure restores the exact previous config and listener before the candidate loop continues.

**Tech Stack:** Windows PowerShell 5.1, Mihomo, official local `agy` CLI, repository PowerShell regression tests.

**Spec:** `docs/superpowers/specs/2026-09-15-isolated-proxy-probe-design.md`

## Global Constraints

- Keep daily Clash `127.0.0.1:7897` and its rule mode unchanged.
- Keep Antigravity on dedicated `127.0.0.1:17897`.
- Do not touch credentials, conversations, or the official Antigravity binary.
- Candidate failures must not leave the formal listener on an unverified candidate.
- Never claim live model success from HTTP 204, a ResponseID alone, or a shallow endpoint check.

---

### Task 1: Formal promotion gate regression test

**Files:**
- Create: `tests/formal-model-gate.test.ps1`
- Read: `src/Antigravity-ProxySupervisor.ps1`

**Interfaces:**
- Consumes the supervisor source text.
- Produces a failing regression test until the formal `Test-RealModelGeneration` call is ordered after production start and before candidate success is persisted.

- [x] **Step 1: Write the failing test**

Assert that the candidate promotion block contains `Start-OrReuseMihomo`, then `Test-RealModelGeneration`, and only afterwards assigns `$selectedCandidate` and logs `candidate_preflight_passed`. Also require a distinct `formal_model_gate_failed` event in the rollback path.

- [x] **Step 2: Run the test to verify it fails**

Run from the repository root:

```powershell
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File tests/formal-model-gate.test.ps1
```

Expected: FAIL because the current promotion block only performs `Test-GoogleConnectivity` after `Start-OrReuseMihomo`.

### Task 2: Add the formal 17897 model gate

**Files:**
- Modify: `src/Antigravity-ProxySupervisor.ps1:2425-2457`
- Test: `tests/formal-model-gate.test.ps1`

**Interfaces:**
- Reuses `Test-RealModelGeneration` with the production `$ProxyUrl` and `$ProxyRoot` already bound to `17897`.
- Keeps the existing `previousConfig` rollback transaction and candidate failure classification.

- [x] **Step 1: Add the smallest implementation**

After formal `Start-OrReuseMihomo` and connectivity verification, call `Test-RealModelGeneration`. Log `formal_model_gate_started` before it and `formal_model_gate_passed` after it. In the catch path log `formal_model_gate_failed` before restoring the previous config; then rethrow so the candidate is cooled/retired and the next candidate is tried.

- [x] **Step 2: Run the focused regression test**

```powershell
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File tests/formal-model-gate.test.ps1
```

Expected: PASS.

- [x] **Step 3: Run the PowerShell parse and promotion-order tests**

```powershell
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File tests/windows-powershell-parse.test.ps1
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File tests/proxy-start-order.test.ps1
```

Expected: both PASS with no parser errors.

### Task 3: Update handoff, deploy the verified script, and inspect live evidence

**Files:**
- Modify: `docs/HANDOFF.md`
- Modify: `VERSION` and `CHANGELOG.md` only if the repository release convention requires a versioned change.
- Deploy: installed supervisor and golden rollback copy after tests pass.

**Interfaces:**
- Consumes the tested source script.
- Produces deployment hash evidence and a truthful handoff that distinguishes formal-gate verification from client UI acceptance.

- [x] **Step 1: Run the relevant local regression suite**

Run the focused tests plus `run-failover-policy-tests.ps1`, `seamless-failover.test.ps1`, and `supervisor-state-contract.test.ps1`; record exact pass/fail output.

- [x] **Step 2: Deploy with a recoverable backup**

Back up the installed supervisor and manifest, copy only the verified supervisor to the installed and golden paths, and verify SHA-256 equality. Do not run the full installer.

- [x] **Step 3: Read live logs and process ownership**

Confirm `7897` is unchanged, `17897` is owned by the private Mihomo process, and a formal-gate failure leaves the previous production config/PID in place. A successful `agy` gate is not reported as client UI acceptance unless a fresh client `streamGenerateContent` response is independently observed.

- [x] **Step 4: Update handoff with remaining boundary**

Record that the formal 17897 gate is verified, while dynamic Google location policy and an independent Antigravity client response remain external/ongoing evidence.

### Task 4: Enforce country-neutral latency-first candidate policy

**Files:**
- Modify: `src/Antigravity-ProxySupervisor.ps1:1240-1244,963-992,1485-1494,2305-2309`
- Modify: `tests/seamless-failover.test.ps1`
- Modify: `tests/run-failover-policy-tests.ps1`
- Modify: `tests/candidate-cap-fairness.test.ps1`
- Create: `tests/latency-first-policy.test.ps1`

**Interfaces:**
- Consumes candidate country labels only for diagnostics and balanced pool construction.
- Produces a common US/JP latency pool whose final ordering is based on fresh RTT and real-model qualification.

- [x] **Step 1: Run the policy regression tests against the old behavior**

The updated tests must fail on the old US-first priority and report strings, proving the requested behavior is not already present.

- [x] **Step 2: Remove country weighting and use balanced pool capping**

Keep `RegionRank` as metadata, set candidate priority from the source priority only, sort without a country key, and round-robin region buckets when the candidate cap is reached.

- [x] **Step 3: Run policy tests**

```powershell
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File tests/latency-first-policy.test.ps1
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File tests/candidate-cap-fairness.test.ps1
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File tests/seamless-failover.test.ps1
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File tests/run-failover-policy-tests.ps1
```

Expected: all PASS and the policy JSON reports `region_neutral_order=true`.

## Completion notes

- Source, installed supervisor, golden rollback copy, and current release copy were verified at SHA-256 `D769901AB1BD87960C51B6A6CDF669E97C19CC4D14AAE8677E68DA2B2BF5E774` with BOM preserved.
- The formal gate caught both location and transport failures in live runs; the final cold start passed on `C08400083F1ADCEF` and launched a fresh client through `17897`.
