"""OS-level task scheduling for automations (Windows schtasks / Unix crontab)."""

import logging
import os
import platform
import subprocess


def get_platform() -> str:
    """Returns 'windows', 'darwin', or 'linux'."""
    p = platform.system().lower()
    if p == "windows":
        return "windows"
    if p == "darwin":
        return "darwin"
    return "linux"


def _freq_to_schtasks(frequency: str) -> str:
    mapping = {"daily": "DAILY", "weekly": "WEEKLY", "hourly": "HOURLY"}
    return mapping.get(frequency, "DAILY")


def _day_to_schtasks(day_of_week: int | None) -> str | None:
    """Convert 0-6 (Mon-Sun) to schtasks day abbreviation."""
    days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    if day_of_week is None or not (0 <= day_of_week <= 6):
        return None
    return days[day_of_week]


def _freq_to_cron(frequency: str, time: str, day_of_week: int | None) -> str:
    """Build cron expression for given frequency."""
    parts = time.split(":") if time else ["09", "00"]
    minute = parts[1] if len(parts) > 1 else "00"
    hour = parts[0]
    if frequency == "hourly":
        return f"0 * * * *"
    if frequency == "weekly":
        dow = day_of_week if day_of_week is not None else 1
        return f"{minute} {hour} * * {dow}"
    # daily
    return f"{minute} {hour} * * *"


def schedule_automation(
    automation_id: int, name: str, script_path: str, schedule: dict
) -> dict:
    """Schedule an automation. Returns {"ok": True, "platform": str, "schedule_id": str} or {"ok": False, "error": str}."""
    pf = get_platform()
    frequency = schedule.get("frequency", "daily")
    time_str = schedule.get("time", "09:00")
    day_of_week = schedule.get("day_of_week")
    task_name = f"PPM_{name}"
    schedule_id = f"PPM_{name}"

    try:
        if pf == "windows":
            cmd = [
                "schtasks", "/create",
                "/tn", task_name,
                "/tr", f"py {script_path}",
                "/sc", _freq_to_schtasks(frequency),
                "/st", time_str,
                "/f",
            ]
            if frequency == "weekly":
                day = _day_to_schtasks(day_of_week)
                if day:
                    cmd += ["/d", day]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return {"ok": False, "error": result.stderr.strip() or result.stdout.strip()}
            return {"ok": True, "platform": pf, "schedule_id": schedule_id}

        else:
            # macOS / Linux — crontab approach
            cron_expr = _freq_to_cron(frequency, time_str, day_of_week)
            cron_line = f"{cron_expr} py {script_path} # {schedule_id}\n"

            # Read existing crontab
            existing = ""
            read_result = subprocess.run(
                ["crontab", "-l"], capture_output=True, text=True, timeout=10
            )
            if read_result.returncode == 0:
                existing = read_result.stdout

            # Remove any existing PPM entry for this task, then append
            lines = [l for l in existing.splitlines(keepends=True) if schedule_id not in l]
            lines.append(cron_line)
            new_crontab = "".join(lines)

            write_result = subprocess.run(
                ["crontab", "-"],
                input=new_crontab,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if write_result.returncode != 0:
                return {"ok": False, "error": write_result.stderr.strip()}
            return {"ok": True, "platform": pf, "schedule_id": schedule_id}

    except Exception as exc:
        logging.exception("schedule_automation failed")
        return {"ok": False, "error": str(exc)}


def unschedule_automation(name: str) -> dict:
    """Remove a scheduled automation. Returns {"ok": True} or {"ok": False, "error": str}."""
    pf = get_platform()
    task_name = f"PPM_{name}"

    try:
        if pf == "windows":
            result = subprocess.run(
                ["schtasks", "/delete", "/tn", task_name, "/f"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return {"ok": False, "error": result.stderr.strip() or result.stdout.strip()}
            return {"ok": True}

        else:
            read_result = subprocess.run(
                ["crontab", "-l"], capture_output=True, text=True, timeout=10
            )
            existing = read_result.stdout if read_result.returncode == 0 else ""
            lines = [l for l in existing.splitlines(keepends=True) if task_name not in l]
            new_crontab = "".join(lines)
            write_result = subprocess.run(
                ["crontab", "-"],
                input=new_crontab,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if write_result.returncode != 0:
                return {"ok": False, "error": write_result.stderr.strip()}
            return {"ok": True}

    except Exception as exc:
        logging.exception("unschedule_automation failed")
        return {"ok": False, "error": str(exc)}


def list_scheduled() -> list[dict]:
    """List all PPM-managed scheduled tasks. Returns list of {"name": str, "schedule_id": str, "next_run": str | None}."""
    pf = get_platform()
    results: list[dict] = []

    try:
        if pf == "windows":
            result = subprocess.run(
                ["schtasks", "/query", "/fo", "LIST", "/v"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return results

            # Parse block-style output for PPM_ tasks
            current: dict = {}
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith("TaskName:"):
                    task_name = line.split(":", 1)[1].strip().lstrip("\\")
                    if task_name.startswith("PPM_"):
                        current = {"name": task_name[4:], "schedule_id": task_name, "next_run": None}
                    else:
                        current = {}
                elif current and line.startswith("Next Run Time:"):
                    next_run = line.split(":", 1)[1].strip()
                    current["next_run"] = next_run if next_run != "N/A" else None
                    results.append(current)
                    current = {}

        else:
            read_result = subprocess.run(
                ["crontab", "-l"], capture_output=True, text=True, timeout=10
            )
            if read_result.returncode != 0:
                return results
            for line in read_result.stdout.splitlines():
                if "# PPM_" in line:
                    parts = line.rsplit("# PPM_", 1)
                    schedule_id = "PPM_" + parts[1].strip()
                    results.append({
                        "name": parts[1].strip(),
                        "schedule_id": schedule_id,
                        "next_run": None,
                    })

    except Exception:
        logging.exception("list_scheduled failed")

    return results
