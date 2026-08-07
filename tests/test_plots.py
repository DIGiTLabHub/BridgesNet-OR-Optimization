"""Plot-level checks for duration-aware manuscript artifacts."""

from __future__ import annotations

import matplotlib.pyplot as plt

from bridgesnet.plots import plot_gantt
from bridgesnet.results import ScheduleRow


def test_gantt_uses_team_service_duration() -> None:
    schedule = [
        ScheduleRow("B1", "C1", "RRU", 1, 0, 1, 1, 0.2, 0.5, 1.0),
        ScheduleRow("B2", "C1", "ERT", 1, 1, 3, 2, 0.3, 0.8, 2.0),
    ]
    figure = plot_gantt(schedule, {"RRU": "blue", "ERT": "orange"})
    widths = [patch.get_width() for patch in figure.axes[0].patches]
    assert widths == [1, 2]
    assert figure.axes[0].get_xlabel() == "Time (days)"
    plt.close(figure)
