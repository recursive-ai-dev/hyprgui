"""Talks to the running Hyprland compositor via hyprctl.

Reading always goes through `hyprctl getoption`, which reflects Hyprland's
actual live config state regardless of whether it was loaded from a Lua or
.conf file — so displayed values are correct even for options this app has
never touched. Writing applies instantly via `hyprctl keyword` and is
separately persisted by config_store so it survives a restart.
"""
import json
import subprocess


class HyprctlError(RuntimeError):
    pass


def _run(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["hyprctl", *args], capture_output=True, text=True, timeout=5
        )
    except FileNotFoundError as e:
        raise HyprctlError("hyprctl not found - is Hyprland running?") from e
    except subprocess.TimeoutExpired as e:
        raise HyprctlError("hyprctl timed out") from e
    if result.returncode != 0:
        raise HyprctlError(result.stderr.strip() or "hyprctl failed")
    return result.stdout


def get_option(dotted_key: str):
    """Returns the current live value of a config option, or None if it
    can't be read (unset, or an option hyprctl can't introspect standalone).
    """
    colon_key = dotted_key.replace(".", ":")
    try:
        out = _run(["-j", "getoption", colon_key])
        data = json.loads(out)
    except (HyprctlError, json.JSONDecodeError):
        return None
    for field in ("bool", "int", "float", "str", "css", "gradient", "vec2"):
        if field in data:
            return data[field]
    return None


def set_option(dotted_key: str, value_str: str) -> bool:
    colon_key = dotted_key.replace(".", ":")
    try:
        _run(["keyword", colon_key, value_str])
        return True
    except HyprctlError:
        return False


def reload() -> bool:
    try:
        _run(["reload"])
        return True
    except HyprctlError:
        return False


def dispatch(dispatcher_args: str) -> bool:
    try:
        _run(["dispatch", *dispatcher_args.split(" ", 1)])
        return True
    except HyprctlError:
        return False


def list_monitors() -> list[dict]:
    try:
        return json.loads(_run(["-j", "monitors"]))
    except (HyprctlError, json.JSONDecodeError):
        return []


def list_binds() -> list[dict]:
    try:
        return json.loads(_run(["-j", "binds"]))
    except (HyprctlError, json.JSONDecodeError):
        return []
