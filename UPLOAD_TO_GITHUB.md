# Bash install / Git push guide

The ZIP is an overlay for the existing public repository:

`https://github.com/chiinsurancebrokers/arrow.git`

Recommended: use a branch first, then merge after Railway/test validation.

```bash
cd ~/Downloads

# Inspect the package before applying it
unzip -l arrow-hal-v3-policy-rate-limit.zip | less

# Clone a clean copy (skip this clone if you already have a clean local repo)
git clone https://github.com/chiinsurancebrokers/arrow.git arrow-travel-portal
cd arrow-travel-portal

git switch main
git pull --ff-only origin main
git status --short

# Create a safe working branch
git switch -c hal-v3-policy-rate-limit

# Apply the overlay to the repository root
unzip -o ../arrow-hal-v3-policy-rate-limit.zip

# Check exactly what changed
git status
git diff --stat
git diff -- . ':!data/policy/arrow_2026_full.txt'

# Optional local test environment
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pytest -q

# Commit and push the branch
git add .
git diff --cached --stat
git commit -m "Upgrade HAL with full policy, claims guidance and usage guard"
git push -u origin hal-v3-policy-rate-limit
```

Then open GitHub and merge `hal-v3-policy-rate-limit` into `main` after review.

If you explicitly want to push directly to `main`, after applying/testing the ZIP use:

```bash
git switch main
git pull --ff-only origin main
git add .
git commit -m "Upgrade HAL with full policy, claims guidance and usage guard"
git push origin main
```

## After Git push - Railway

Add/update the environment variables shown in `.env.example`. Do **not** commit real API keys or admin keys.

After Railway redeploys, check:

```bash
curl -s https://YOUR-RAILWAY-DOMAIN/health
```

Then test the employee portal and both administrator pages in a browser.
