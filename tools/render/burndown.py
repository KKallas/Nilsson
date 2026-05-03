#!/usr/bin/env python3
"""Render an issue burndown bar chart and push it to the dashboard.

Inputs:
  --start: str — start date (YYYY-MM-DD). Default: 7 days ago.
  --end: str — end date (YYYY-MM-DD). Default: today.
  --exclude: str — comma-separated issue numbers to exclude (e.g. "48,49,111").
  --port: int — server port (default: 8421).

Process:
  1. Fetches all issues (open + closed) from GitHub via `gh`.
  2. Computes daily open-issue count, new issues, and closed issues.
  3. Renders a Frappe line chart with actual remaining, opened, closed, and ideal lines.

Output: Prints dashboard link."""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


def fetch_issues() -> list[dict]:
    """Fetch all issues (open + closed, up to 200) with timestamps."""
    cmd = [
        "gh", "issue", "list", "--state", "all", "--limit", "200",
        "--json", "number,title,state,createdAt,closedAt",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"gh error: {result.stderr}", file=sys.stderr)
        return []
    return json.loads(result.stdout)


def compute_daily_stats(
    issues: list[dict], start: date, end: date, exclude: set[int],
) -> dict:
    """Return daily open/new/closed counts for the date range."""
    filtered = [i for i in issues if i.get("number") not in exclude]

    days = (end - start).days + 1
    labels: list[str] = []
    open_eod: list[int] = []
    new_day: list[int] = []
    closed_day: list[int] = []

    for offset in range(days):
        d = start + timedelta(days=offset)
        sod = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
        eod = sod + timedelta(days=1)

        open_count = 0
        new_count = 0
        closed_count = 0

        for iss in filtered:
            created = datetime.fromisoformat(
                iss["createdAt"].replace("+00:00", "+00:00"),
            ).replace(tzinfo=timezone.utc) if iss.get("createdAt") else None
            closed_at = datetime.fromisoformat(
                iss["closedAt"].replace("+00:00", "+00:00"),
            ).replace(tzinfo=timezone.utc) if iss.get("closedAt") else None

            if created is None:
                continue

            # Was this issue open at end of day?
            if created < eod and (closed_at is None or closed_at >= eod):
                open_count += 1

            # Was this issue created today?
            if sod <= created < eod:
                new_count += 1

            # Was this issue closed today?
            if closed_at and sod <= closed_at < eod:
                closed_count += 1

        labels.append(d.strftime("%b %d"))
        open_eod.append(open_count)
        new_day.append(new_count)
        closed_day.append(closed_count)

    return {
        "labels": labels,
        "open_issues": open_eod,
        "new_issues": new_day,
        "closed_issues": closed_day,
    }


# Frappe Charts v1.6.1 UMD — confirmed working CDN URL.
# v2 IIFE does NOT expose the global; v1.6.1 UMD exposes `frappe.Chart`.
TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ margin:0; padding:16px; background:#0d1117; color:#c9d1d9;
         font-family:-apple-system,BlinkMacSystemFont,sans-serif; }}
  .wrap {{ background:#161b22; border:1px solid #30363d; border-radius:8px;
           padding:20px; max-width:820px; margin:0 auto; }}
  h2 {{ margin:0 0 4px; color:#fff; font-size:20px; }}
  .sub {{ margin:0 0 16px; color:#888; font-size:13px; }}
  #chart {{ margin-bottom:16px; }}
  .stats {{ display:flex; gap:16px; justify-content:center; flex-wrap:wrap; }}
  .stat {{ background:#16213e; padding:12px 20px; border-radius:8px; text-align:center; }}
  .stat .n {{ font-size:24px; font-weight:bold; }}
  .stat .l {{ font-size:11px; color:#888; margin-top:2px; }}
  .c-new {{ color:#4fc3f7; }}
  .c-closed {{ color:#81c784; }}
  .c-open {{ color:#ff8a65; }}
</style>
</head>
<body>
<div class="wrap">
  <h2>{title}</h2>
  <p class="sub">{subtitle}</p>
  <div id="chart"></div>
  <div class="stats">
    <div class="stat"><div class="n c-new">{total_new}</div><div class="l">New Issues</div></div>
    <div class="stat"><div class="n c-closed">{total_closed}</div><div class="l">Closed Issues</div></div>
    <div class="stat"><div class="n c-open">{end_open}</div><div class="l">Still Open</div></div>
  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/frappe-charts@1.6.1/dist/frappe-charts.min.umd.js"></script>
<script>
var labels = {labels_json};
var openIssues = {open_json};
var newIssues = {new_json};
var closedIssues = {closed_json};

// Ideal line: only 2 or 3 real points, nulls everywhere else
var startVal = openIssues[0] || 0;
var endVal = openIssues[openIssues.length - 1] || 0;
var n = labels.length;
var slope = (endVal - startVal) / Math.max(n - 1, 1);
var ideal = new Array(n).fill(null);
ideal[0] = startVal;
ideal[n - 1] = endVal;

if (slope < 0 && endVal > 0) {{
  // Trending down: add one projected zero point
  var extraDays = Math.ceil(endVal / Math.abs(slope));
  for (var j = 0; j < extraDays; j++) {{
    var last = new Date(labels[labels.length - 1] + " 2026");
    last.setDate(last.getDate() + j + 1);
    var months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    labels.push(months[last.getMonth()] + " " + String(last.getDate()).padStart(2, "0"));
    openIssues.push(null);
    newIssues.push(null);
    closedIssues.push(null);
    ideal.push(null);
  }}
  ideal[ideal.length - 1] = 0;
}}

new frappe.Chart("#chart", {{
  data: {{
    labels: labels,
    datasets: [
      {{ name: "Open Issues", type: "line", values: openIssues }},
      {{ name: "New",         type: "line", values: newIssues }},
      {{ name: "Closed",      type: "line", values: closedIssues }},
      {{ name: "Ideal",       type: "line", values: ideal }}
    ]
  }},
  type: "axis-mixed",
  height: 300,
  colors: ["#58a6ff", "#4fc3f7", "#81c784", "#6b7280"],
  lineOptions: {{ regionFill: 0, dotSize: 3, hideLine: 0, hideDots: 0, spline: 1 }},
  axisOptions: {{ xAxisMode: "tick", xIsSeries: 1 }},
  tooltipOptions: {{
    formatTooltipY: function(d) {{ return d !== null ? d + " issues" : "—"; }}
  }}
}});
</script>
</body>
</html>"""


def build_html(stats: dict, exclude: set[int]) -> str:
    """Generate the full HTML string from daily stats."""
    title = "Issue Burndown \u2014 " + stats["labels"][0] + " to " + stats["labels"][-1]
    nums = sorted(exclude)
    subtitle = ("Excluding issues: " + ", ".join(f"#{n}" for n in nums)) if nums else "All issues included"

    total_new = sum(stats["new_issues"])
    total_closed = sum(stats["closed_issues"])
    end_open = stats["open_issues"][-1] if stats["open_issues"] else 0

    return TEMPLATE.format(
        title=title,
        subtitle=subtitle,
        labels_json=json.dumps(stats["labels"]),
        open_json=json.dumps(stats["open_issues"]),
        new_json=json.dumps(stats["new_issues"]),
        closed_json=json.dumps(stats["closed_issues"]),
        total_new=total_new,
        total_closed=total_closed,
        end_open=end_open,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Render an issue burndown bar chart to the dashboard")
    parser.add_argument("--start", help="Start date YYYY-MM-DD (default: 7 days ago)")
    parser.add_argument("--end", help="End date YYYY-MM-DD (default: today)")
    parser.add_argument("--exclude", default="", help='Comma-separated issue numbers to exclude (e.g. "48,49,111")')
    parser.add_argument("--port", type=int, default=8421)
    args = parser.parse_args()

    today = date.today()
    end_date = datetime.strptime(args.end, "%Y-%m-%d").date() if args.end else today
    start_date = datetime.strptime(args.start, "%Y-%m-%d").date() if args.start else end_date - timedelta(days=7)

    exclude: set[int] = set()
    if args.exclude:
        for part in args.exclude.split(","):
            part = part.strip()
            if part.isdigit():
                exclude.add(int(part))

    issues = fetch_issues()
    stats = compute_daily_stats(issues, start_date, end_date, exclude)

    total_new = sum(stats["new_issues"])
    total_closed = sum(stats["closed_issues"])
    end_open = stats["open_issues"][-1] if stats["open_issues"] else 0

    html = build_html(stats, exclude)

    print("=== BURNDOWN BAR ===")
    print(f"Range: {start_date} to {end_date}  |  Excluded: {len(exclude)}")
    print(f"  |  Closed: {total_closed}  |  Still Open: {end_open}")

    artifact_id = hashlib.md5(f"burndown_bar{time.time()}".encode()).hexdigest()[:12]
    artifact_dir = Path("public/charts")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    html_path = artifact_dir / f"{artifact_id}.html"
    html_path.write_text(html)

    base = f"http://127.0.0.1:{args.port}"
    chart_url = f"{base}/public/charts/{artifact_id}.html"
    png_url = f"{base}/renderpng?src=/public/charts/{artifact_id}.html"
    print(f"[Open in dashboard]({chart_url})")
    print(f"[Download PNG]({png_url})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
