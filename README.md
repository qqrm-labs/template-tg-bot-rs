# Rust Serverless Bot Template

Template repository for scheduled Rust bots running on GitHub Actions.

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
5. Keep the generated `Cargo.lock` committed and update it when dependencies change; the hosted runner builds with `--locked`.

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
