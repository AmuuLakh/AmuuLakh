# Setup guide — AmuuLakh GitHub stats

## 1. Copy the files into your profile repository

Copy this folder's contents into the root of `AmuuLakh/AmuuLakh`. Preserve the `.github/workflows/` and `scripts/` paths. Your profile repository must remain public so visitors can see the README.

## 2. Create a token for private data

The GraphQL `ContributionsCollection` includes private/internal contributions when authorized with the optional `read:user` scope (GitHub documentation). This starter also enumerates owned private repositories to calculate aggregate language totals.

Create a **personal access token (classic)** at https://github.com/settings/tokens with:
- `read:user`
- `repo`

`repo` is broad access to private repositories. Treat this token like a password, set an expiry, and revoke it if exposed. The script only reads data with this token; it does not use it to push commits. If you do not want to grant `repo`, use public-only repository language totals instead.

## 3. Add the token as an Actions secret

In `AmuuLakh/AmuuLakh`, open Settings → Secrets and variables → Actions → New repository secret.

- Name: `GH_STATS_TOKEN`
- Secret: paste your token

Never put the token in README.md, workflow YAML, source code, or a chat.

## 4. Allow Actions to commit the SVG files

Open Settings → Actions → General → Workflow permissions. Select **Read and write permissions** and save.

The workflow declares `contents: write`. The built-in `GITHUB_TOKEN` performs the commit; `GH_STATS_TOKEN` is used only to read statistics.

## 5. Commit the project files

Commit and push:
- `README.md`
- `.github/workflows/update-stats.yml`
- `requirements.txt`
- `scripts/generate_stats.py`

The first successful workflow run creates the SVGs in `assets/`. Until then, the README image links may be broken.

## 6. Run it manually once

Go to the repository's Actions tab → Update GitHub profile statistics → Run workflow. Select the default branch and run it. When it succeeds, refresh your GitHub profile.

Afterward it runs daily at 00:17 UTC. Scheduled jobs run from the default branch and may be delayed by GitHub during busy periods.

## What the numbers mean

- Commits, contributions, issues, pull requests, and reviews use GitHub's rolling contribution calendar (approximately the last 12 months), not lifetime totals.
- Private/internal contribution counts are included when GitHub makes them available to the token. Private repository names and descriptions are never emitted into the SVGs.
- Stars count stars on public, non-fork repositories owned by the account.
- Language percentages use language bytes from owned, non-fork repositories, including private repositories the token can access.
- Current and longest streaks are calculated from the returned rolling contribution calendar, not guaranteed all-time streaks.
- GitHub's contribution rules determine which activities count.

## Troubleshooting

- **401 / Bad credentials:** token invalid, expired, or pasted incorrectly. Create a replacement and update the secret.
- **Private data missing:** confirm `read:user`, the `repo` scope, and that the token belongs to the account being queried.
- **Push rejected:** confirm Actions workflow permissions are set to Read and write.
- **Workflow does not run on schedule:** confirm the YAML is on the default branch. Use Run workflow to test.
- **Broken images:** the first workflow run must succeed before generated SVG files exist.
- **No changes to commit:** normal if the generated SVGs are unchanged.

## Security

The public README shows aggregate counts and language totals, but not private repository names or code. Anyone who can change this workflow may be able to access its secret. Protect the repository, review workflow changes, and rotate the token if you suspect exposure.
