"""BioBatch Sentinel: deterministic bioprocess incident-response code-repair tasks."""
from dataclasses import dataclass
import textwrap


@dataclass
class Case:
    group: str
    code: str
    expect: object


@dataclass
class TaskInstance:
    task_id: str
    title: str
    difficulty: str
    instructions: str
    files: dict
    cases: list
    reference: dict


def _case(group, code, expect):
    return Case(group, textwrap.dedent(code).strip(), expect)


def sensor_calibration_task(seed):
    return TaskInstance(
        task_id="sensor_calibration", title="Correct the sensor calibration", difficulty="easy",
        instructions=("`sensors.calibrate_reading(raw, offset, scale)` must first subtract the sensor's "
                      "zero offset from `raw`, then multiply by `scale`. Return the calibrated reading."),
        files={"sensors.py": "def calibrate_reading(raw, offset, scale):\n    return raw * scale + offset\n"},
        cases=[
            _case("target", "from sensors import calibrate_reading\nresult = calibrate_reading(10, 2, 1.5)", 12.0),
            _case("target", "from sensors import calibrate_reading\nresult = calibrate_reading(20, 4, 0.5)", 8.0),
            _case("regression", "from sensors import calibrate_reading\nresult = calibrate_reading(0, 0, 1)", 0),
            _case("regression", "from sensors import calibrate_reading\nresult = calibrate_reading(5, 0, 2)", 10),
        ],
        reference={"sensors.py": "def calibrate_reading(raw, offset, scale):\n    return (raw - offset) * scale\n"},
    )


def ph_alarm_task(seed):
    return TaskInstance(
        task_id="ph_alarm", title="Fix the pH alarm boundaries", difficulty="easy",
        instructions=("`alarms.ph_out_of_range(ph, low, high)` returns True only when pH is strictly "
                      "below `low` or strictly above `high`. Values exactly at either limit are in range."),
        files={"alarms.py": "def ph_out_of_range(ph, low, high):\n    return ph <= low or ph >= high\n"},
        cases=[
            _case("target", "from alarms import ph_out_of_range\nresult = ph_out_of_range(6.8, 6.8, 7.2)", False),
            _case("target", "from alarms import ph_out_of_range\nresult = ph_out_of_range(7.2, 6.8, 7.2)", False),
            _case("regression", "from alarms import ph_out_of_range\nresult = ph_out_of_range(6.5, 6.8, 7.2)", True),
            _case("regression", "from alarms import ph_out_of_range\nresult = ph_out_of_range(7.0, 6.8, 7.2)", False),
        ],
        reference={"alarms.py": "def ph_out_of_range(ph, low, high):\n    return ph < low or ph > high\n"},
    )


def do_trend_task(seed):
    return TaskInstance(
        task_id="do_trend", title="Handle missing dissolved-oxygen readings", difficulty="medium",
        instructions=("`trends.average_dissolved_oxygen(readings)` averages numeric readings, ignores missing "
                      "values represented by `None`, and returns 0.0 if no numeric readings are available."),
        files={"trends.py": "def average_dissolved_oxygen(readings):\n    return sum(readings) / len(readings)\n"},
        cases=[
            _case("target", "from trends import average_dissolved_oxygen\nresult = average_dissolved_oxygen([6.2, None, 6.8])", 6.5),
            _case("target", "from trends import average_dissolved_oxygen\nresult = average_dissolved_oxygen([None, None])", 0.0),
            _case("regression", "from trends import average_dissolved_oxygen\nresult = average_dissolved_oxygen([5.0, 7.0])", 6.0),
            _case("regression", "from trends import average_dissolved_oxygen\nresult = average_dissolved_oxygen([8.0])", 8.0),
        ],
        reference={"trends.py": (
            "def average_dissolved_oxygen(readings):\n"
            "    available = [value for value in readings if value is not None]\n"
            "    if not available:\n        return 0.0\n"
            "    return sum(available) / len(available)\n"
        )},
    )


def contamination_task(seed):
    return TaskInstance(
        task_id="contamination_signal", title="Correct the contamination threshold", difficulty="medium",
        instructions=("`quality.contamination_suspected(turbidity, baseline, threshold)` returns True when "
                      "turbidity has increased by at least `threshold` above baseline. Equality counts."),
        files={"quality.py": (
            "def contamination_suspected(turbidity, baseline, threshold):\n"
            "    return (turbidity - baseline) > threshold\n"
        )},
        cases=[
            _case("target", "from quality import contamination_suspected\nresult = contamination_suspected(15, 10, 5)", True),
            _case("target", "from quality import contamination_suspected\nresult = contamination_suspected(23, 20, 3)", True),
            _case("regression", "from quality import contamination_suspected\nresult = contamination_suspected(14, 10, 5)", False),
            _case("regression", "from quality import contamination_suspected\nresult = contamination_suspected(18, 10, 5)", True),
        ],
        reference={"quality.py": (
            "def contamination_suspected(turbidity, baseline, threshold):\n"
            "    return (turbidity - baseline) >= threshold\n"
        )},
    )


def recovery_task(seed):
    return TaskInstance(
        task_id="recovery_action", title="Prioritize the batch recovery action", difficulty="medium",
        instructions=("`recovery.recommend_action(ph, do_mg_l, contamination_suspected)` must prioritize: "
                      "suspected contamination -> 'isolate_batch'; dissolved oxygen below 4.0 -> "
                      "'increase_aeration'; pH strictly outside 6.8–7.2 -> 'adjust_ph'; otherwise "
                      "'continue_monitoring'. This is a simulated exercise, not real process-control advice."),
        files={"recovery.py": (
            "def recommend_action(ph, do_mg_l, contamination_suspected):\n"
            "    if do_mg_l < 4.0:\n        return 'increase_aeration'\n"
            "    if ph < 6.8 or ph > 7.2:\n        return 'adjust_ph'\n"
            "    if contamination_suspected:\n        return 'isolate_batch'\n"
            "    return 'continue_monitoring'\n"
        )},
        cases=[
            _case("target", "from recovery import recommend_action\nresult = recommend_action(7.0, 2.5, True)", "isolate_batch"),
            _case("target", "from recovery import recommend_action\nresult = recommend_action(6.5, 6.0, True)", "isolate_batch"),
            _case("regression", "from recovery import recommend_action\nresult = recommend_action(7.0, 3.0, False)", "increase_aeration"),
            _case("regression", "from recovery import recommend_action\nresult = recommend_action(6.5, 6.0, False)", "adjust_ph"),
            _case("regression", "from recovery import recommend_action\nresult = recommend_action(7.0, 6.0, False)", "continue_monitoring"),
        ],
        reference={"recovery.py": (
            "def recommend_action(ph, do_mg_l, contamination_suspected):\n"
            "    if contamination_suspected:\n        return 'isolate_batch'\n"
            "    if do_mg_l < 4.0:\n        return 'increase_aeration'\n"
            "    if ph < 6.8 or ph > 7.2:\n        return 'adjust_ph'\n"
            "    return 'continue_monitoring'\n"
        )},
    )


TASKS = {
    "sensor_calibration": sensor_calibration_task,
    "ph_alarm": ph_alarm_task,
    "do_trend": do_trend_task,
    "contamination_signal": contamination_task,
    "recovery_action": recovery_task,
}
DEMO_TASK = "sensor_calibration"


def build_task(task_id, seed):
    if task_id not in TASKS:
        raise KeyError(f"unknown task '{task_id}'. Available: {', '.join(TASKS)}")
    return TASKS[task_id](seed)
