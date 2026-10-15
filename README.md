# Rust Serverless Bot Template

Template repository for scheduled Rust bots running on GitHub Actions.

`Cargo.lock` is committed because this is an application. CI and the bot runner use
`--locked`; update the committed lockfile when dependencies change. CI also runs
the harmless placeholder without Telegram credentials.

Dependency updates form one weekly maintenance batch with a seven-day cooldown.
Native auto-merge waits for `ci-gate` and `workflow-security-gate` on the current
commit, with no review approval or merge cron. Derived repositories must require
both gates, keep the branch up to date, and enable native auto-merge.

## Included
- CI workflow with dependency checks (`.github/workflows/ci.yml`)
- GitHub Actions security workflow with actionlint and Zizmor (`.github/workflows/workflow-security.yml`)
- Scheduled bot runner (`.github/workflows/run-bot.yml`)
- Keepalive workflow to maintain repository activity (`.github/workflows/keepalive.yml`)

## Usage
1. Create a repository from this template.
2. Add required secrets used by your bot (for example `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`).
3. Implement bot logic in `src/main.rs`.
4. Adjust cron in `run-bot.yml`.

## Local Commands
- `cargo fmt --all -- --check`
- `cargo check --tests --benches`
- `cargo clippy --all-targets --all-features -- -D warnings`
- `cargo nextest run --no-tests=pass`
- `cargo audit`
- `cargo deny check advisories bans sources`
- `cargo machete`

Before publishing a derived project, choose and declare its license. License
enforcement is intentionally not enabled by the template's `cargo-deny` policy.
