"""Einheitlicher Diagrammstil für Notebooks und README-Grafiken."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

from .config import FIGURES_DIR

COLORS = {
    "blue": "#2a78d6",
    "orange": "#eb6834",
    "aqua": "#1baf7a",
    "yellow": "#eda100",
    "magenta": "#e87ba4",
    "violet": "#6250d6",
    "red": "#e34948",
    "grey": "#8c8b86",
}
SERIES = [COLORS[c] for c in ("blue", "orange", "aqua", "yellow", "magenta", "violet")]
TEXT = "#0b0b0b"
TEXT_MUTED = "#52514e"
GRID = "#e4e3df"


def set_style() -> None:
    plt.rcParams.update(
        {
            "figure.figsize": (11, 4.5),
            "figure.dpi": 110,
            "savefig.dpi": 150,
            "savefig.bbox": "tight",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": GRID,
            "axes.labelcolor": TEXT_MUTED,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "axes.titlecolor": TEXT,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.grid.axis": "y",
            "axes.prop_cycle": plt.cycler(color=SERIES),
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "lines.linewidth": 2,
            "xtick.color": TEXT_MUTED,
            "ytick.color": TEXT_MUTED,
            "legend.frameon": False,
            "font.size": 10,
        }
    )


def save(fig, name: str, directory: Path = FIGURES_DIR) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.png"
    fig.savefig(path)
    return path
