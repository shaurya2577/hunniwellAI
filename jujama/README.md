# Jujama Exporters

Standalone Playwright exporters for Jujama company and attendee profiles.

## Setup

From the repository root:

```bash
python3 -m venv jujama/.venv
source jujama/.venv/bin/activate
pip install -r jujama/requirements.txt
playwright install chromium
```

Or from inside `jujama/`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Usage

From the repository root:

```bash
source jujama/.venv/bin/activate
python3 jujama/run_jujama_companies.py --test-one
python3 jujama/run_jujama_attendees.py --test-one
```

Or from inside `jujama/`:

```bash
source .venv/bin/activate
python3 run_jujama_companies.py --test-one
python3 run_jujama_attendees.py --test-one
```

For full runs, remove `--test-one`.

## Output

- `~/Downloads/Jujama/jujama_companies/jujama_companies.csv`
- `~/Downloads/Jujama/jujama_attendees/jujama_attendees.csv`

Both flows open a persistent Chromium profile, let you log in manually, wait for you to navigate to the correct Jujama list page, and then paginate through the live site to collect detail records.
