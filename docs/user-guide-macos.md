# macOS User Guide

This guide walks through setting up the SquirrelOps orchestration workspace on macOS from scratch. By the end, you will have the orchestration repository and both managed runtime repositories (PingTing and ClownPeanuts) cloned locally, and the smoke test will pass to confirm everything is in order.

## 1. Prerequisites

### Xcode Command Line Tools

The Xcode command line tools provide the base development toolchain on macOS, including a system Git binary and essential build utilities. If you have never installed them, run:

```bash
xcode-select --install
```

A dialog will appear asking you to confirm the installation. This download can take a few minutes depending on your connection.

### Git

While macOS ships a Git binary as part of the Xcode tools, it is often an older version. Installing Git through Homebrew gives you a more recent release with better defaults:

```bash
brew install git
```

After installing, confirm the Homebrew-managed Git is on your path:

```bash
git --version
```

### GNU Coreutils (Optional but Recommended)

The bootstrap and update scripts can wrap long-running Git operations in hard timeouts to prevent them from hanging indefinitely. On Linux, the `timeout` command is part of the standard coreutils package. On macOS, this command is not available by default, but you can install the GNU coreutils package to get an equivalent called `gtimeout`:

```bash
brew install coreutils
```

If you skip this step, the scripts will still work — they will simply run Git operations without a hard timeout and print a warning to let you know.

### GitHub Access

The managed runtime repositories (`mattmacrocket/pingting` and `mattmacrocket/clownpeanuts`) may be private. You need Git-level read access to both of them. There are two ways to authenticate (you will choose one in Step 3 below):

- **SSH key** — Your SSH key must be added to your GitHub account and loaded into your SSH agent.
- **Personal access token** — A GitHub token with `repo` read access, used with HTTPS cloning.

If the repositories are public, no special authentication setup is needed.

## 2. Clone SquirrelOps

Create the base directory (if it does not already exist) and clone this orchestration repository:

```bash
mkdir -p /Users/matt/code
cd /Users/matt/code
git clone git@github.com:mattmacrocket/squirrelops.git
cd squirrelops
```

All subsequent commands in this guide assume you are inside the `squirrelops` directory.

## 3. Choose an Authentication Mode for Runtime Repos

The bootstrap script needs to clone two runtime repositories from GitHub. How it authenticates depends on the `CLONE_PROTOCOL` setting. When running locally (outside of CI), the default is SSH.

### Option A: SSH (Default)

This is the simplest path if you already have SSH keys set up with GitHub.

First, confirm that your SSH key is loaded and that GitHub recognizes it:

```bash
ssh -T git@github.com
```

You should see a message like `Hi <username>! You've successfully authenticated`. If you see a permission denied error, make sure your SSH key is added to your GitHub account and loaded into the agent (`ssh-add`).

Once SSH is working, bootstrap the runtime repositories:

```bash
./scripts/bootstrap_repos.sh
```

The script will clone PingTing and ClownPeanuts in parallel into sibling directories alongside SquirrelOps (e.g., `/Users/matt/code/pingting` and `/Users/matt/code/clownpeanuts`). If either repository already exists at the expected path, the script will fetch and fast-forward-merge instead of cloning.

### Option B: HTTPS with a Personal Access Token

If you prefer HTTPS or cannot use SSH, you can authenticate with a GitHub personal access token. Create a token at [github.com/settings/tokens](https://github.com/settings/tokens) with read access to:

- `mattmacrocket/pingting`
- `mattmacrocket/clownpeanuts`

Then export the token and protocol before running the bootstrap:

```bash
export CLONE_PROTOCOL=https
export GH_ACCESS_TOKEN='ghp_your_token_here'
./scripts/bootstrap_repos.sh
```

The script uses an ephemeral `GIT_ASKPASS` helper to supply the token to Git's credential prompt. The token is never embedded in the clone URL itself, and the helper script is automatically deleted when the bootstrap finishes. This means the token does not persist in your Git configuration or shell history (beyond the `export` line in your current session).

You can also use the `GITHUB_TOKEN` environment variable instead of `GH_ACCESS_TOKEN` — the script checks both.

## 4. Verify the Setup

Run the smoke test to confirm that both runtime repositories were cloned correctly:

```bash
./harness/smoke.sh
```

The smoke harness performs the following checks against each managed repository defined in `config/projects.yaml`:

1. Confirms that a `.git` directory exists at the expected path (e.g., `/Users/matt/code/pingting/.git`).
2. Confirms that the verification key file exists on disk. The verification key is a file path declared in `config/projects.yaml` that serves as a lightweight indicator of a successful and complete checkout. The current verification keys are:
   - `pingting/main.py` for PingTing
   - `clownpeanuts/cli.py` for ClownPeanuts
3. Runs `git rev-parse --is-inside-work-tree` to confirm that Git considers the directory a valid repository.

Each repository is checked in parallel. If all checks pass, you will see:

```
Smoke check passed.
```

If any check fails, the output will indicate which repository and which specific check did not pass.

## 5. Day-to-Day Updates

When you want to pull the latest changes for the managed runtime repositories, use the update script:

```bash
./scripts/update_repos.sh
```

This script is similar to the bootstrap script, but with one key difference: it only operates on repositories that already exist locally. If a repository has not been cloned yet, the update script skips it with a `[skip]` message rather than cloning it. This is a safety measure — if you want to add a new repository to your workspace, use the bootstrap script instead.

The update script performs `git fetch --all --prune` followed by `git pull --ff-only` for each existing repository, running them in parallel. The `--ff-only` flag means the pull will fail if the local branch has diverged from the remote (i.e., it will not create a merge commit). If you see a fast-forward failure, you will need to resolve the local divergence manually before updating.

Before each update, the script verifies that the existing checkout's remote URL matches what `config/projects.yaml` declares. If you have a directory at the expected path but it points to a different GitHub repository, the update will be aborted for that repository with a mismatch error.

After updating, run the smoke test again to confirm everything is still in order:

```bash
./harness/smoke.sh
```

## 6. Using a Different Base Directory

By default, all scripts assume the runtime repositories live under `/Users/matt/code`. This is the sole entry in the `ALLOWED_BASE_ROOTS` list. The scripts validate the base directory against this list before performing any operations — if the directory is outside the allowed roots, the script will exit with an error.

To use a different base directory, you need to do two things:

1. Add your desired directory to the `ALLOWED_BASE_ROOTS` environment variable.
2. Pass it as the first argument to each script.

For example, to use `/Users/matt/work` instead:

```bash
export ALLOWED_BASE_ROOTS="/Users/matt/work,/Users/matt/code"
./scripts/bootstrap_repos.sh /Users/matt/work
./scripts/update_repos.sh /Users/matt/work
./harness/smoke.sh /Users/matt/work
```

The `ALLOWED_BASE_ROOTS` variable accepts a comma-separated list of directory prefixes. A base directory is considered valid if it equals or is a subdirectory of any entry in the list. You can include multiple roots if you work across several directory trees.

Note that you need to include the original default (`/Users/matt/code`) in the list if you still want it to work as well — setting `ALLOWED_BASE_ROOTS` replaces the default rather than appending to it.

## 7. Understanding the Configuration File

The repository definitions live in `config/projects.yaml`. This file is the single source of truth used by the bootstrap script, update script, and smoke harness. A typical entry looks like this:

```yaml
projects:
  - name: pingting
    repo: git@github.com:mattmacrocket/pingting.git
    role: runtime
    verification_key: pingting/main.py
```

The fields are:

- **`name`** — The directory name the repository will be cloned into under the base directory.
- **`repo`** — The Git remote URL. This is declared in SSH format but is automatically converted to HTTPS format when `CLONE_PROTOCOL=https`.
- **`role`** — Either `runtime` (a managed application repository) or `umbrella` (the orchestration repository itself). Only `runtime` entries are processed by the bootstrap, update, and smoke scripts.
- **`verification_key`** — A relative file path within the cloned repository that the smoke harness checks for existence. This is a lightweight way to confirm that the repository was cloned completely and is the expected project.

## 8. Troubleshooting

### "BASE_DIR ... is outside ALLOWED_BASE_ROOTS"

The directory you specified (or the default `/Users/matt/code`) is not in the allowed roots list. This is the directory validation guard preventing operations in unexpected locations.

**Fix:** Add your intended directory to the `ALLOWED_BASE_ROOTS` environment variable before running the script. See Section 6 above for details.

### "Repository mismatch ... expected ... found ..."

The script found a directory at the expected path, but its Git remote URL points to a different repository than what `config/projects.yaml` declares. This can happen if you previously cloned a different project into the same directory name, or if the configuration was changed.

**Fix:** Either move or remove the existing checkout at that path, or change your base directory to avoid the conflict. The script will not overwrite or modify a checkout that does not match.

### "missing pingting/main.py" or "missing clownpeanuts/cli.py" in smoke

The smoke harness found the `.git` directory but the verification key file is missing. This typically means the clone was incomplete or the repository is in an unexpected state (e.g., checked out on a branch that does not have the file).

**Fix:** Re-run the bootstrap script to re-clone or update the affected repository, then run the smoke test again:

```bash
./scripts/bootstrap_repos.sh
./harness/smoke.sh
```

### "No timeout utility found" warning

The scripts could not find the `timeout` command (Linux) or `gtimeout` command (macOS via coreutils). Without it, Git operations will not have a hard timeout, meaning a stalled network connection could cause the script to hang indefinitely.

**Fix:** Install GNU coreutils:

```bash
brew install coreutils
```

This provides `gtimeout`, which the scripts detect and use automatically.

### SSH authentication failures

If `git clone` fails with a permission denied error when using SSH, check the following:

- Run `ssh -T git@github.com` to confirm your SSH key is recognized by GitHub.
- Make sure your SSH key is loaded in the agent: `ssh-add -l` should list your key.
- If you use multiple SSH keys, confirm your `~/.ssh/config` routes `github.com` to the correct key.

### HTTPS token issues

If HTTPS cloning fails with a 401 or 403 error:

- Confirm that the `GH_ACCESS_TOKEN` (or `GITHUB_TOKEN`) environment variable is set and contains a valid, non-expired token.
- Confirm that the token has read access to the repositories listed in `config/projects.yaml`.
- Make sure `CLONE_PROTOCOL=https` is set — the token is only used with HTTPS cloning.

### Fast-forward pull failures

If the update script reports that `git pull --ff-only` failed, it means your local branch has commits that are not on the remote, so Git cannot fast-forward. This is unusual for the managed runtime repositories since they are typically not edited locally through this workspace.

**Fix:** Navigate to the affected repository and resolve the divergence manually (e.g., with `git rebase` or `git reset`), then re-run the update script.
