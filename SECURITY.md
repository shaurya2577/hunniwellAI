# Security & Data Handling

This repo is **public** on GitHub (`shaurya2577/hunniwellAI`). It touches confidential company decks and live API keys. Read this before committing or pushing.

## Threat model

The actual harm scenarios we care about:

1. **A live API key gets pushed to the public repo.** Even one commit means rotate immediately — GitHub indexes commits within seconds and there are bots that scrape for `sk-ant-…`, `pat…`, etc.
2. **A pitch deck or company financial summary gets pushed.** This is data submitted to Hunniwell in confidence. Even a deletion later doesn't fix it (git history is forever; GitHub may have served copies to scrapers).
3. **A Playwright auth cookie or storage state gets pushed.** Logging anyone into a conference platform with our session is a misuse risk.

## What's blocked by `.gitignore` today

All commits should pass these patterns. The root `.gitignore` blocks (verified):

- `**/.env` and `.env`
- `**/auth.json`, `**/credentials*`, `**/*.pem`, `**/id_rsa*`
- `**/*_browser_profile/`, `**/recordings/`
- `**/.venv/`, `**/venv/`, `**/__pycache__/`, `**/.DS_Store`
- `CompanyFiles/`, `**/downloads/`, `**/test_output/`
- All data-file extensions: `*.csv`, `*.tsv`, `*.xlsx`, `*.xls`, `*.pdf`, `*.docx`, `*.pptx`, `*.pages`
- Ingest operational artifacts: `ai/airtable_ingest/.processed*.json*`, `run_log*.csv`, `*.out`
- IDE / session state: `.idea/`, `.cursor/`, `.claude/`, `.serena/`

## What lives WHERE (not in the repo)

| Thing | Location | Why outside the repo |
|---|---|---|
| Anthropic + Airtable API keys | `ai/airtable_ingest/.env` (gitignored) | Live secrets |
| All company decks / summaries | `~/Documents/Hunniwell/<event>/<company>/` | 18 GB, confidential, doesn't belong in any git repo |
| Playwright session profiles | `scrapers/<platform>/*_browser_profile/` (gitignored) | Logged-in browser state |
| Auth cookies / recordings | `scrapers/<platform>/recordings/` (gitignored) | Codegen-recorded auth flows |

## Pre-push checklist

Run from the repo root before any `git push`:

```bash
# Anything obviously sensitive about to be tracked?
git diff --cached --name-only | grep -Ei "\.(env|csv|pdf|pptx|docx|xlsx|tsv)$" && echo "STOP" || echo "clean"

# Inline secret patterns?
git diff --cached -U0 | grep -Ei "sk-ant-api03-|pat[A-Za-z0-9]{14}|ghp_[A-Za-z0-9]{20}|AKIA[A-Z0-9]{16}|BEGIN.*PRIVATE KEY" && echo "STOP" || echo "clean"
```

If either returns anything, do NOT push. Fix the staging.

## If a key DOES leak

1. **Rotate it immediately.** Anthropic console → revoke the leaked key, generate a new one. Same for Airtable.
2. **Update local `.env`** with the new key.
3. **Don't bother trying to scrub the git history.** It's already public; assume the key was scraped within 60 seconds of push. The only fix is rotation.

## If confidential data leaks

1. Notify the Hunniwell partner whose data was exposed.
2. Take the file out of the latest commit, but understand: the file is still in git history and on GitHub's mirrors. There is no clean "undo." Use this as a forcing function to make the gitignore stricter so it doesn't happen again.
3. If the leak is severe enough to warrant a takedown, GitHub has a private-data DMCA-style process — talk to the partner before going that route.

## When in doubt

The default-deny posture is intentional: `*.csv`, `*.pdf`, `*.docx`, `*.xlsx`, `*.pptx` are all globally ignored. If you have a CSV that legitimately should be tracked (e.g. a small reference fixture for tests), explicitly whitelist it with a `!path/to/specific.csv` line in `.gitignore`. Never weaken the global block.
