# RunWatch Prerequisites

Use this guide before running `install.sh`, especially on a fresh Linux VM or
on a machine that has not used `tmux` before.

This guide assumes you may not have `sudo`. A conda-compatible manager is used
only to provide command-line tools such as `tmux`, `lsof`, `fish`, and `uv`.
RunWatch itself is still managed by `uv` in this repository.

## 1. Choose an Environment Manager

If you already have `micromamba`, `mamba`, or `conda`, use it directly:

```bash
export MAMBA_CMD=micromamba
```

Replace `micromamba` with `mamba` or `conda` if that is what your machine has:

```bash
export MAMBA_CMD=conda
```

For a persistent bash setup:

```bash
echo 'export MAMBA_CMD=micromamba' >> ~/.bashrc
source ~/.bashrc
```

For a persistent fish setup:

```fish
set -Ux MAMBA_CMD micromamba
```

Only install micromamba if no conda-compatible tool is available:

```bash
curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba
mkdir -p ~/.local/bin
mv bin/micromamba ~/.local/bin/
```

Add it to your shell path:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

For a persistent bash setup:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
echo 'export MAMBA_CMD=micromamba' >> ~/.bashrc
source ~/.bashrc
```

For fish:

```fish
fish_add_path ~/.local/bin
set -Ux MAMBA_CMD micromamba
```

Verify:

```bash
$MAMBA_CMD --version
```

## 2. Install Base Tools

Install shared command-line tools in `base`. This does not create a RunWatch
project environment; the repository still uses `uv` for that.

```bash
$MAMBA_CMD install -y -n base -c conda-forge python=3.10 uv tmux lsof curl ca-certificates fish
$MAMBA_CMD activate base
```

Verify:

```bash
python --version
uv --version
tmux -V
lsof -v
fish --version
```

### 2.1 Optional: Beautify fish With fisher

This step only improves the interactive shell experience. RunWatch does not
need fisher.

Install `git` first because many fish plugins are fetched from GitHub:

```bash
$MAMBA_CMD install -y -n base -c conda-forge curl git fish ca-certificates
```

Start fish:

```bash
$MAMBA_CMD activate base
fish
```

Check that fish can see `git` and uses the conda-compatible `curl`, not Snap
curl:

```fish
command -v git
command -v curl
type -a curl
```

Install fisher inside fish:

```fish
curl -sL https://raw.githubusercontent.com/jorgebucaran/fisher/main/functions/fisher.fish | source
fisher install jorgebucaran/fisher
fisher --version
```

The `fisher install jorgebucaran/fisher` step persists fisher into
`~/.config/fish/functions`, so it is available in future fish sessions.

Optional prompt theme:

```fish
fisher install ilancosman/tide@v6
functions -q tide; and tide configure
```

If the prompt symbols look broken after tide installs successfully, keep the
default fish prompt or install a Nerd Font in your terminal.

## 3. Initialize Shell Support

If your shell has not been initialized for micromamba yet:

```bash
micromamba shell init -s bash -r ~/.local/share/mamba
source ~/.bashrc
```

For `conda`, use:

```bash
conda init bash
source ~/.bashrc
```

If you plan to run commands inside fish, initialize your environment manager for
fish too.

For micromamba:

```fish
micromamba shell init -s fish -r ~/.local/share/mamba
source ~/.config/fish/config.fish
```

For conda:

```fish
conda init fish
source ~/.config/fish/config.fish
```

## 4. Use fish Without Making It Default

This guide does not make fish your default login shell. Do not run `chsh`.
Start fish manually only when you want it:

```bash
fish
```

Inside fish, activate `base` before working on RunWatch:

```fish
$MAMBA_CMD activate base
```

If fish does not know `$MAMBA_CMD activate`, initialize it once:

```fish
micromamba shell init -s fish -r ~/.local/share/mamba
source ~/.config/fish/config.fish
$MAMBA_CMD activate base
```

For conda, use `conda init fish` instead of `micromamba shell init`.

## 5. Verify tmux

Create a test session:

```bash
tmux new -s runwatch-test
```

Detach from tmux with:

```text
Ctrl+b, then d
```

List sessions:

```bash
tmux ls
```

If `tmux ls` shows `runwatch-test`, RunWatch can discover tmux panes.

### 5.1 Optional: Catppuccin tmux Theme Experiment

This step only changes tmux appearance. RunWatch does not need it. It requires
GitHub access.

Catppuccin's tmux README recommends manual installation. Clone the theme:

```bash
mkdir -p ~/.config/tmux/plugins/catppuccin
git clone -b v2.3.0 https://github.com/catppuccin/tmux.git ~/.config/tmux/plugins/catppuccin/tmux
```

Add this experimental block to `~/.tmux.conf`. Do not paste this block into
fish or bash directly; `run` and `set -g` are tmux configuration commands.

One direct way to append it is:

```bash
printf '%s\n' \
  '# RunWatch optional tmux appearance experiment.' \
  'set -g mouse on' \
  'set -g default-terminal "tmux-256color"' \
  '' \
  'set -g @catppuccin_flavor "mocha"' \
  'set -g @catppuccin_window_status_style "rounded"' \
  'run ~/.config/tmux/plugins/catppuccin/tmux/catppuccin.tmux' \
  '' \
  'set -g status-position bottom' \
  'set -g status-interval 2' \
  'set -g status-left-length 40' \
  'set -g status-right-length 80' \
  'set -g status-left "#[bold] #S "' \
  'set -g status-right "%Y-%m-%d %H:%M "' \
  '' \
  'bind-key -n MouseDown3Pane display-menu -T "#[align=centre]Pane" \' \
  '  "Split horizontal" h "split-window -h" \' \
  '  "Split vertical" v "split-window -v" \' \
  '  "" \' \
  '  "Kill pane" x "confirm-before -p '\''Kill this pane? (y/n)'\'' kill-pane" \' \
  '  "Kill window" X "confirm-before -p '\''Kill this window? (y/n)'\'' kill-window" \' \
  '  "" \' \
  '  "New window" n "new-window" \' \
  '  "Rename window" r "command-prompt -I '\''#W'\'' '\''rename-window %%'\''" \' \
  '  "" \' \
  '  "Reload config" R "source-file ~/.tmux.conf; display-message '\''tmux config reloaded'\''"' \
  >> ~/.tmux.conf
```

The right-click pane menu needs tmux 3.x. Check your version with:

```bash
tmux -V
```

Reload tmux:

```bash
tmux source-file ~/.tmux.conf
```

Right-click menu troubleshooting:

- Use right-click inside a tmux pane, not in a normal fish or bash terminal.
- If right-click pastes text such as `tmux source-file ~/.tmux.conf` into the
  prompt, your terminal is handling right-click as paste before tmux receives
  the mouse event. Enable tmux mouse support first with the reload command above,
  then try again inside tmux.
- In VS Code's integrated terminal, change the terminal right-click behavior if
  it is set to paste. Search settings for `terminal.integrated.rightClickBehavior`.

Verify tmux received the options:

```bash
tmux show -g mouse
tmux list-keys -n MouseDown3Pane
```

If the status bar symbols look broken, install a Nerd Font in your terminal or
remove icon-heavy Catppuccin options later.

To remove the experiment, delete the Catppuccin block from `~/.tmux.conf` and
reload tmux again.

## 6. Optional GPU Check

GPU metrics need NVIDIA tools from the host machine. If this command fails,
RunWatch still works, but the GPU card will show `unknown`.

```bash
nvidia-smi
```

## 7. Continue With README

Prerequisite setup ends here. From this point on, follow the existing
[README.md](README.md), starting at **Install**.

Before running the README commands, make sure `base` is active:

```bash
$MAMBA_CMD activate base
```

Then use the README sections:

- **Install**
- **.env Example**
- **Start**
- **Stop**
- **Change Host Or Port**

## If You Do Have sudo

On Ubuntu or Debian, you can install system tools directly instead of using a
conda-compatible manager for `tmux` and `lsof`:

```bash
sudo apt update
sudo apt install -y curl ca-certificates tmux lsof python3 python3-venv
```

You can still use `uv` for the Python project environment.

## Quick Checks

```bash
$MAMBA_CMD activate base
command -v python
command -v uv
command -v tmux
command -v lsof
fish --version
tmux ls
```

If any command is missing, activate `base` or install the matching prerequisite
above before starting RunWatch.
