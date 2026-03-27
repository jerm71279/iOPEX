# Claude Code — WSL Setup Guide

Complete setup guide for installing Claude Code on Windows Subsystem for Linux (WSL).

---

## Prerequisites

- Windows 10 (version 2004+) or Windows 11
- Administrator access on the Windows machine

---

## Step 1 — Install WSL

Open **PowerShell as Administrator** and run:

```powershell
wsl --install
```

This installs WSL 2 with Ubuntu as the default distribution. **Restart your PC** when prompted.

After restart, Ubuntu will launch automatically and ask you to create a Linux username and password. These are your WSL credentials — they don't need to match your Windows login.

> If WSL was already installed, verify you have WSL 2:
> ```powershell
> wsl --set-default-version 2
> wsl --list --verbose
> ```

---

## Step 2 — Update Ubuntu

Open WSL (type `wsl` in Windows search or launch Ubuntu from the Start menu):

```bash
sudo apt update && sudo apt upgrade -y
```

---

## Step 3 — Install Node.js

Claude Code requires Node.js 18+. Install via NodeSource:

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs -y
```

Verify:

```bash
node --version   # should show v20.x.x
npm --version    # should show 10.x.x
```

---

## Step 4 — Install Claude Code

```bash
npm install -g @anthropic-ai/claude-code
```

Verify:

```bash
claude --version
```

---

## Step 5 — Authenticate

Launch Claude Code from any directory:

```bash
claude
```

On first launch it will open a browser window to sign in with your Anthropic account. Complete the login, return to the terminal, and you're ready.

---

## Step 6 — Start Working

Navigate to your project folder and launch:

```bash
cd ~/projects/my-project
claude
```

To resume a previous session:

```bash
claude -r
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Open WSL | Type `wsl` in Windows search |
| Update packages | `sudo apt update && sudo apt upgrade -y` |
| Install Claude Code | `npm install -g @anthropic-ai/claude-code` |
| Launch Claude Code | `claude` |
| Resume last session | `claude -r` |
| Check version | `claude --version` |
| Check Node version | `node --version` |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `wsl --install` fails | Ensure Hyper-V and Virtual Machine Platform are enabled in Windows Features |
| `npm: command not found` | Re-run the Node.js install steps in Step 3 |
| `claude: command not found` | Run `npm install -g @anthropic-ai/claude-code` again; check `npm prefix -g` is on your PATH |
| Browser doesn't open for auth | Run `claude` with `--no-browser` and follow the manual token flow |
| Permission denied on `npm install -g` | Use `sudo npm install -g @anthropic-ai/claude-code` |
| WSL clock drift (affects auth) | Run `sudo hwclock -s` or `sudo ntpdate pool.ntp.org` |

---

## Optional — Configure Git (recommended)

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

---

*iOPEX Technologies — Internal Setup Documentation*
