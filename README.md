# Neon Drop

A modern falling-block puzzler with synthwave visuals. Built with Python and pygame-ce, compiled to WebAssembly for browser play.

![status](https://img.shields.io/badge/status-in%20development-yellow)

## Features

- Guideline-accurate SRS rotation with full wall-kick tables
- 7-bag randomizer for fair piece distribution
- T-spin, back-to-back, and combo scoring
- DAS/ARR input handling for responsive play
- Procedurally-synthesized sound effects
- Playable in the browser (coming soon)

## Controls

| Key | Action |
| --- | --- |
| ← / → | Move |
| ↓ | Soft drop |
| Space | Hard drop |
| ↑ / X | Rotate CW |
| Z / Ctrl | Rotate CCW |
| C / Shift | Hold |
| Esc | Pause |

## Development

Requires Python 3.11+.

```bash
git clone https://github.com/YOUR-USERNAME/neon-drop.git
cd neon-drop
python -m venv .venv
source .venv/Scripts/activate    # Git Bash on Windows
pip install -e ".[dev]"
neon-drop