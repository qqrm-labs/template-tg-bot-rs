# Repository Agent Instructions

## Core Principles
- Keep automation simple and deterministic.
- Favor standard crates and clear error handling.
- Treat schedules as production jobs and monitor failures.

## Validation Loop
- `cargo fmt --all -- --check`
- `cargo check --locked --tests --benches`
- `cargo clippy --locked --all-targets --all-features -- -D warnings`
- `cargo nextest run --locked --no-tests=pass` (empty scaffold only)

## Workflow Rules
- Never bypass failing checks on `main`.
- Keep secrets only in GitHub Actions secrets.

## Test Design and Evidence
- The current application is a credential-free placeholder with no application
  tests. Its successful run is a scaffold smoke check. When adding bot behavior,
  add behavioral tests and remove `--no-tests=pass` from both CI and these commands.
  Zero selected tests must then fail the required test job.
- Start from observable contracts: request/response handling, message contents,
  duplicate delivery, retry limits, and persisted state. Derive expected results
  independently of the production implementation and test the real entry points.
- Use injected clocks and local/fake transports for deterministic failure cases.
  Exercise the production request builder, response parser, and retry/state logic;
  a mock that returns the final expected answer does not test those components.
  Never send Telegram messages or use production credentials from tests.
- For a behavior change, cover the relevant success and failure cases. Consider
  `proptest` for parsers, normalization, deduplication, and state transitions when
  an invariant spans many inputs. Generate meaningful valid/invalid classes,
  preserve minimized failures, and record seed/replay data.
- When strengthening tests or changing critical behavior, run a clean baseline,
  inject a plausible production defect in an isolated copy, run the same tests,
  restore the code, and rerun. Check the intended assertion, not just a nonzero
  process exit. Prefer a reviewer-selected defect when auditing test quality.
- Use targeted `cargo-mutants` where it can expose weak assertions. Report raw
  outcomes, scope, survivors, and equivalence justifications. Keep compilation
  errors, timeouts, crashes, and unrelated failures separate from assertion kills.
  Do not exclude a difficult case just to obtain a green report.
- Report the revision, commands, versions, selected tests/features, counts, and
  limitations. Builds, skipped jobs, missing tools, and zero tests are not passing
  behavioral validation. Avoid artificial tests for documentation-only changes.

## Rust Bot Tool Selection
- Keep normal tests fast and credential-free. Include doctests with
  `cargo test --locked --doc` if the project adds executable library examples;
  nextest does not execute them. Validate supported targets and feature sets.
- Add `cargo-fuzz` for complex/untrusted parsing if ordinary/property tests leave
  a useful search space; save the corpus and failures and set a finite time budget.
- Use Miri for applicable unsafe Rust and native sanitizers plus real ABI tests
  for foreign code. Use Loom only for synchronization modeled with its primitives.
- Consider Kani only for small critical functions with a precise contract. Record
  assumptions, reachable cases, and bounds; check that the proof is not vacuous.
- These advanced tools are not installed or required by the scaffold. Enable a
  tool only with a compatible pinned setup, reproducible command, meaningful
  detection control, and clear CI cost/trigger. Required checks must expose missing
  execution as failure; optional checks must report skips explicitly.

References: [Proptest](https://proptest-rs.github.io/proptest/intro.html),
[cargo-mutants outcomes](https://mutants.rs/using-results.html),
[Rust Fuzz Book](https://rust-fuzz.github.io/book/cargo-fuzz.html),
[Miri](https://github.com/rust-lang/miri), [Loom](https://github.com/tokio-rs/loom),
[Kani results](https://model-checking.github.io/kani/verification-results.html).
