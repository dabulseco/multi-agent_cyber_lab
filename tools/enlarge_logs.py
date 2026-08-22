"""Grow the four log files where sample size carries the analytical lesson.

Every row that exists today is preserved verbatim — those are the narrative beats the
scenarios and the instructor notes are written around. What gets added is the ordinary
traffic surrounding them, so the deterministic analyzers have a baseline to separate
signal from, and a coefficient of variation is computed over hundreds of intervals
rather than three.

Seeded, so regenerating produces identical files.
"""
import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RNG = random.Random(20260822)


def ts(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


# This script appends generated rows to whatever it finds on disk, so running it a
# second time would stack another few hundred rows on top of the first pass. The logs
# are already enlarged and committed; the guard makes that mistake loud instead of
# silent. Delete the guard only if you are regenerating from the original small files.
ALREADY_ENLARGED = 50


def read_existing(path):
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        rows = [r for r in reader if r]
    if len(rows) > ALREADY_ENLARGED:
        raise SystemExit(
            f"{path.name} already has {len(rows)} rows — it has been enlarged already. "
            f"Re-running would append a second batch. Restore the original file first."
        )
    return header, rows


def write(path, header, rows):
    """Sort by timestamp (column 0) and write. Original rows keep their exact values."""
    rows = sorted(rows, key=lambda r: r[0])
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
    print(f"{path.name}: {len(rows)} rows")


# --------------------------------------------------------------- traffic spike

def traffic_spike():
    """Admissions-deadline surge.

    The scenario asks students to decide attack vs. legitimate rush, and its learning
    goals explicitly reward saying the evidence is inconclusive. So the added traffic
    stays deliberately ambiguous: a very high unique-IP ratio (consistent with either a
    distributed flood or a real crowd) combined with human-irregular timing and 5xx
    errors that follow load rather than causing it.
    """
    path = ROOT / "data/logs/web_log_traffic_spike.csv"
    header, existing = read_existing(path)
    rows = list(existing)

    uris = ["/admissions", "/financial-aid", "/apply", "/deadlines", "/status", "/portal/login"]
    uri_weights = [34, 20, 22, 8, 10, 6]
    agents = [
        "Mozilla/5.0", "Mozilla/5.0 (iPhone)", "Mozilla/5.0 (Android)", "Mozilla/5.0 (iPad)",
        "Mozilla/5.0 (Macintosh)", "Mozilla/5.0 (Windows NT 10.0)",
    ]
    agent_weights = [26, 24, 20, 10, 10, 10]

    def ip():
        block = RNG.choice(["198.51.100", "203.0.113", "192.0.2"])
        return f"{block}.{RNG.randint(2, 250)}"

    # A pool of returning visitors keeps the unique-to-row ratio below 1.0 — real
    # crowds contain people who reload, and a ratio of exactly 1.0 would hand students
    # the answer.
    returning = [ip() for _ in range(40)]

    # Baseline: an ordinary hour before the surge.
    t = parse("2026-05-02T12:45:00Z")
    while t < parse("2026-05-02T13:56:00Z"):
        src = RNG.choice(returning) if RNG.random() < 0.45 else ip()
        rows.append([
            ts(t), src, "www.campus.edu",
            RNG.choices(uris, uri_weights)[0], "200",
            RNG.choices(agents, agent_weights)[0],
        ])
        t += timedelta(seconds=max(4, int(RNG.expovariate(1 / 42))))

    # Surge: volume climbs, intervals stay jittery, 5xx appears as capacity gives out.
    t = parse("2026-05-02T13:59:35Z")
    end = parse("2026-05-02T14:38:00Z")
    while t < end:
        elapsed = (t - parse("2026-05-02T13:59:35Z")).total_seconds()
        load = min(1.0, elapsed / 900)
        status = "503" if RNG.random() < 0.18 + 0.22 * load else ("500" if RNG.random() < 0.04 else "200")
        src = RNG.choice(returning) if RNG.random() < 0.3 else ip()
        rows.append([
            ts(t), src, "www.campus.edu",
            RNG.choices(uris, uri_weights)[0], status,
            RNG.choices(agents, agent_weights)[0],
        ])
        t += timedelta(seconds=max(1, int(RNG.expovariate(1 / 7.5))))

    write(path, header, rows)


# ------------------------------------------------------------------- egress

def egress():
    """Routine outbound traffic, so the escalating run has something to escalate from.

    The three climbing transfers from 10.5.10.22 and the single small transfer from
    10.5.10.30 are the scenario's evidence and are left untouched.
    """
    path = ROOT / "data/logs/egress_exfiltration.csv"
    header, existing = read_existing(path)
    rows = list(existing)

    hosts = ["10.5.10.30", "10.5.10.31", "10.5.10.45", "10.5.20.14", "10.5.33.8", "10.5.10.7"]
    destinations = [
        ("52.94.236.10", "443"), ("140.82.114.4", "443"), ("13.107.42.14", "443"),
        ("151.101.1.69", "443"), ("104.18.32.115", "443"), ("199.232.36.133", "80"),
    ]

    t = parse("2026-03-17T07:02:00Z")
    while t < parse("2026-03-17T18:30:00Z"):
        host = RNG.choice(hosts)
        dst, port = RNG.choice(destinations)
        # Ordinary business egress: mostly small, occasionally a backup or sync burst.
        size = RNG.randint(180_000, 900_000) if RNG.random() > 0.12 else RNG.randint(900_000, 1_400_000)
        rows.append([ts(t), host, dst, port, str(size)])
        # Exponential spacing: bursty, like real traffic. Uniform gaps would make the
        # baseline look machine-regular and hand students a finding that isn't there.
        t += timedelta(seconds=max(20, int(RNG.expovariate(1 / 150))))

    write(path, header, rows)


# --------------------------------------------------------------- auth (shared)

def auth_ransomware():
    """Normal campus authentication around the jlee / finance.svc compromise.

    The 74-second US-HI → RO source switch is the finding; without a baseline of
    single-source accounts it is not obviously anomalous.
    """
    path = ROOT / "data/logs/auth_log_ransomware_lab.csv"
    header, existing = read_existing(path)
    rows = list(existing)

    users = ["mchen", "rgarcia", "kpatel", "swilliams", "dnguyen", "aroberts", "tkim",
             "lmartin", "bthompson", "jlee", "ehall", "cwright"]
    services = ["vpn", "sso", "fileshare", "mail", "sshd"]
    service_weights = [26, 34, 18, 16, 6]
    # Each account keeps its own habitual workstation, so a second source address for
    # one user stands out as a measurable deviation rather than as background noise.
    home_ip = {u: f"10.5.{RNG.randint(10, 40)}.{RNG.randint(2, 250)}" for u in users}

    t = parse("2026-03-04T06:30:00Z")
    while t < parse("2026-03-04T17:45:00Z"):
        user = RNG.choice(users)
        failed = RNG.random() < 0.07
        rows.append([
            ts(t), user, home_ip[user],
            "FAILED" if failed else "SUCCESS",
            RNG.choices(services, service_weights)[0], "US-HI",
        ])
        t += timedelta(seconds=max(20, int(RNG.expovariate(1 / 145))))

    write(path, header, rows)


def auth_sabotage():
    """A normal working day before the late-night sabotage window.

    This is what makes 'off-hours share' meaningful: the deleted-backup sequence runs
    at 23:41-00:05 against a baseline that sits entirely inside working hours.
    """
    path = ROOT / "data/logs/auth_log_sabotage.csv"
    header, existing = read_existing(path)
    rows = list(existing)

    users = ["t.walker", "s.okafor", "m.iverson", "p.ramirez", "j.dutta", "h.novak",
             "c.bergman", "n.oyelaran"]
    services = ["vpn", "sso", "domain_admin_console", "backup_server", "fileshare", "ad"]
    service_weights = [22, 38, 8, 8, 18, 6]
    home_ip = {u: f"10.5.{RNG.randint(10, 40)}.{RNG.randint(2, 250)}" for u in users}

    # One continuous working day before the 23:41 sabotage window. A multi-day baseline
    # would put 12-hour overnight gaps into the interval series, and every dispersion
    # statistic would then describe the calendar rather than the behaviour.
    t = parse("2026-04-19T07:12:00Z")
    while t < parse("2026-04-19T18:40:00Z"):
        user = RNG.choice(users)
        failed = RNG.random() < 0.05
        rows.append([
            ts(t), user, home_ip[user],
            "FAILED" if failed else "SUCCESS",
            RNG.choices(services, service_weights)[0], "US-HI",
        ])
        t += timedelta(seconds=max(30, int(RNG.expovariate(1 / 190))))

    write(path, header, rows)


if __name__ == "__main__":
    traffic_spike()
    egress()
    auth_ransomware()
    auth_sabotage()
