#!/usr/bin/env python3

import argparse
from datetime import datetime
import os
import sys
from sys import stderr
import toml
from xfinity_usage.xfinity_usage import XfinityUsage


DATE_FMT = "%m/%d/%Y"


def get_usage_data(username, password):
    """
    Attempt to fetch usage data from Xfinity.

    Arguments:
        username (str): Xfinity username.
        password (str): Xfinity password.

    Raises:
        RuntimeError: If the request fails.
    """
    usage_req = XfinityUsage(username, password, browser_name="firefox-headless")
    return usage_req.run()


def parse_usage_data(usage_data):
    """
    Parses usage data from `get_usage_data` into a simplified dictionary.

    Returns:
        dict: Parsed usage data.

    Raises:
        RuntimeError: If parsing of any fields fails.
    """
    try:
        used = float(usage_data["used"])
        total = float(usage_data["total"])
        units = usage_data["units"]
    except KeyError:
        raise RuntimeError("Missing usage field")
    except ValueError:
        raise RuntimeError("Invalid float for usage")

    try:
        last_month = usage_data["raw"]["usageMonths"][-1]
    except KeyError:
        raise RuntimeError('Missing "usageMonths" field')
    except IndexError:
        raise RuntimeError("No month data found")

    try:
        start_date = datetime.strptime(last_month["startDate"], DATE_FMT)
        end_date = datetime.strptime(last_month["endDate"], DATE_FMT)
    except KeyError:
        raise RuntimeError("Missing start and end date")
    except ValueError:
        raise RuntimeError("Failed to decode date range")

    try:
        cur_date = datetime.fromtimestamp(usage_data["data_timestamp"])
    except KeyError:
        raise RuntimeError("Missing start and end date")
    except ValueError:
        raise RuntimeError("Failed to decode current date")

    return {
        "used": used,
        "total": total,
        "units": units,
        "start_date": start_date,
        "end_date": end_date,
        "cur_date": cur_date,
    }


def main(config_file):
    try:
        with open(config_file) as f:
            cfg = toml.load(f)
        username = cfg["username"]
        password = cfg["password"]
    except (OSError, IOError) as e:
        print("Failed to read config file: {}".format(e), file=stderr)
        sys.exit(0)
    except KeyError:
        print("Missing username or password in config file", file=stderr)
        sys.exit(0)

    print("Requesting usage data...")
    try:
        raw_usage_data = get_usage_data(username, password)
    except RuntimeError as e:
        print("Failed to fetch usage data: {}".format(e))
        sys.exit(0)

    print("Parsing usage data...")
    try:
        data = parse_usage_data(raw_usage_data)
    except RuntimeError as e:
        print("Failed to parse usage data: {}".format(e))

    used = data["used"]
    total = data["total"]
    units = data["units"]
    start_date = data["start_date"]
    end_date = data["end_date"]
    cur_date = data["cur_date"]

    month_hours = (end_date - start_date).total_seconds() / 3600 + 24
    cur_hours = (cur_date - start_date).total_seconds() / 3600

    percent_elapsed = cur_hours / month_hours * 100
    percent_bw = used / total * 100

    print("\nSummary:")
    print("  Policy elapsed:     {elapse:.2f}%".format(elapse=percent_elapsed))
    print(
        "  Bandwidth consumed: {per_bw:.2f}% ({used}{units}/{total}{units})".format(
            per_bw=percent_bw, used=int(used), total=int(total), units=units
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Checks this month's bandwidth usage for an Xfinity Internet plan"
    )
    parser.add_argument(
        "config",
        nargs="?",
        default="config.toml",
        type=str,
        help="Configuration file containing username and password",
    )
    args = parser.parse_args()
    main(args.config)
