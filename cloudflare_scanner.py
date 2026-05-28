import argparse
import csv
import ipaddress
import platform
import random
import socket
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from rich import box
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.table import Table

CF_IPV4_URL = "https://www.cloudflare.com/ips-v4"
CF_IPV6_URL = "https://www.cloudflare.com/ips-v6"
CF_SPEED_TEST_URL = "https://speed.cloudflare.com/__down?bytes=10485760"
PING_COUNT = 5
FALLBACK_PORT = 443
PING_TIMEOUT  = 2
SPEED_TIMEOUT = 10
DEFAULT_WORKERS = 50
DEFAULT_SAMPLE = 5

def fetch_cloudflare_ranges(include_ipv6: bool = False) -> list[str]:
    urls = [CF_IPV4_URL]
    if include_ipv6:
        urls.append(CF_IPV6_URL)

    ranges = []
    for url in urls:
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            for line in resp.text.splitlines():
                cidr = line.strip()
                if cidr:
                    ranges.append(cidr)
        except requests.RequestException as exc:
            print(f"[WARNING] Could not fetch {url}: {exc}", file=sys.stderr)

    return ranges


def sample_ips_from_cidr(cidr: str, count: int) -> list[str]:
    try:
        network = ipaddress.ip_network(cidr, strict=False)
        hosts = list(network.hosts())
        if len(hosts) <= count:
            return [str(h) for h in hosts]
        return [str(h) for h in random.sample(hosts, count)]
    except ValueError:
        return []


def _ping_command(ip: str, count: int, timeout: int) -> list[str]:
    system = platform.system().lower()
    if system == "windows":
        return ["ping", "-n", str(count), "-w", str(timeout * 1000), ip]
    else:
        return ["ping", "-c", str(count), "-W", str(timeout), ip]


def parse_ping_output(output: str) -> dict:
    import re

    result = {"rtts": [], "avg_ms": None, "jitter": None, "loss_pct": None}

    loss_match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*(?:packet\s*)?loss", output, re.I)
    if loss_match:
        result["loss_pct"] = float(loss_match.group(1))

    rtts = []

    for m in re.finditer(r"time[=<](\d+(?:\.\d+)?)\s*ms", output, re.I):
        rtts.append(float(m.group(1)))

    if rtts:
        result["rtts"] = rtts
        result["avg_ms"] = round(statistics.mean(rtts), 2)
        result["jitter"] = round(statistics.stdev(rtts), 2) if len(rtts) > 1 else 0.0

    return result


def ping_ip(ip: str, count: int = PING_COUNT, timeout: int = PING_TIMEOUT) -> dict:
    base = {
        "ip": ip,
        "reachable": False,
        "avg_ms": None,
        "jitter": None,
        "loss_pct": 100.0,
        "method": "icmp",
    }

    cmd = _ping_command(ip, count, timeout)

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout * count + 5,
        )
        output = proc.stdout.decode(errors="replace") + proc.stderr.decode(errors="replace")
        metrics = parse_ping_output(output)

        if metrics["avg_ms"] is not None:
            base.update(metrics)
            base["reachable"] = True
        else:
            base["loss_pct"] = metrics.get("loss_pct", 100.0)

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    if not base["reachable"]:
        base["method"] = "tcp"
        t_start = time.monotonic()
        try:
            with socket.create_connection((ip, FALLBACK_PORT), timeout=timeout):
                elapsed = (time.monotonic() - t_start) * 1000
            base["reachable"] = True
            base["avg_ms"]    = round(elapsed, 2)
            base["jitter"]    = None
            base["loss_pct"]  = 0.0
        except OSError:
            pass

    return base


def measure_download_speed(target_ip: str, timeout: int = SPEED_TIMEOUT) -> float | None:
    import ssl
    from urllib3.connection import HTTPSConnection
    from urllib3.connectionpool import HTTPSConnectionPool
    from requests.adapters import HTTPAdapter
 
    HOST     = "speed.cloudflare.com"
    PATH     = "/__down?bytes=5242880"
    PORT     = 443
 
    class DirectIPConnection(HTTPSConnection):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
 
        def connect(self):
            context = ssl.create_default_context()
            raw_sock = socket.create_connection((target_ip, PORT), timeout=timeout)
            self.sock = context.wrap_socket(raw_sock, server_hostname=HOST)
 
    class DirectIPConnectionPool(HTTPSConnectionPool):
        ConnectionCls = DirectIPConnection
 
    class DirectIPAdapter(HTTPAdapter):
        def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
            return DirectIPConnectionPool(HOST, port=PORT)
 
        def get_connection(self, url, proxies=None):
            return DirectIPConnectionPool(HOST, port=PORT)
 
    session = requests.Session()
    session.mount("https://", DirectIPAdapter())
 
    try:
        t_start = time.monotonic()
        resp = session.get(
            f"https://{HOST}{PATH}",
            timeout=timeout,
            stream=True,
        )
        resp.raise_for_status()
 
        bytes_received = 0
        for chunk in resp.iter_content(chunk_size=65536):
            bytes_received += len(chunk)
 
        elapsed = time.monotonic() - t_start
 
        if elapsed == 0 or bytes_received == 0:
            return None
 
        mbps = (bytes_received * 8) / (elapsed * 1_000_000)
        return round(mbps, 2)
 
    except Exception:
        return None
    finally:
        session.close()


def scan_ip(ip: str, test_speed: bool = True) -> dict:
    result = ping_ip(ip)

    if test_speed and result["reachable"]:
        result["speed_mbps"] = measure_download_speed(ip)
    else:
        result["speed_mbps"] = None

    return result


def scan_all(
    ip_list: list[str],
    workers: int = DEFAULT_WORKERS,
    test_speed: bool = True,
    console: Console = None,
) -> list[dict]:
    if console is None:
        console = Console()

    results = []
    total = len(ip_list)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[cyan]{task.completed}/{task.total}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Scanning IPs…", total=total)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_ip = {
                executor.submit(scan_ip, ip, test_speed): ip
                for ip in ip_list
            }

            for future in as_completed(future_to_ip):
                try:
                    results.append(future.result())
                except Exception as exc:
                    ip = future_to_ip[future]
                    results.append({
                        "ip": ip, "reachable": False,
                        "avg_ms": None, "jitter": None,
                        "loss_pct": 100.0, "speed_mbps": None,
                        "method": "error", "error": str(exc),
                    })
                finally:
                    progress.advance(task)

    results.sort(key=lambda r: (not r["reachable"], r["avg_ms"] or float("inf")))
    return results


def display_results(results: list[dict], console: Console, top_n: int = None):
    show = results[:top_n] if top_n else results

    table = Table(
        title="Cloudflare IP Scan Results",
        box=box.ROUNDED,
        show_lines=True,
        header_style="bold cyan",
    )

    table.add_column("Rank",       justify="right",  style="dim",    width=5)
    table.add_column("IP Address", justify="left",   style="white",  width=20)
    table.add_column("Ping (ms)",  justify="right",  width=10)
    table.add_column("Jitter (ms)",justify="right",  width=11)
    table.add_column("Loss %",     justify="right",  width=8)
    table.add_column("Speed Mbps", justify="right",  width=11)
    table.add_column("Method",     justify="center", style="dim",    width=7)

    for rank, r in enumerate(show, start=1):
        if not r["reachable"]:
            ping_str  = "[red]unreachable[/red]"
            jitter_str= "[dim]—[/dim]"
            loss_str  = "[red]100%[/red]"
            speed_str = "[dim]—[/dim]"
        else:
            ms = r["avg_ms"]
            color = "green" if ms <= 50 else ("yellow" if ms <= 150 else "red")
            ping_str   = f"[{color}]{ms}[/{color}]"

            j = r.get("jitter")
            jitter_str = f"{j}" if j is not None else "[dim]—[/dim]"

            loss = r.get("loss_pct", 0)
            loss_color = "green" if loss == 0 else ("yellow" if loss < 20 else "red")
            loss_str = f"[{loss_color}]{loss}%[/{loss_color}]"

            sp = r.get("speed_mbps")
            speed_str = f"{sp}" if sp is not None else "[dim]—[/dim]"

        table.add_row(
            str(rank),
            r["ip"],
            ping_str,
            jitter_str,
            loss_str,
            speed_str,
            r.get("method", "—"),
        )

    console.print(table)


def save_csv(results: list[dict], path: str):
    fieldnames = ["rank", "ip", "reachable", "avg_ms", "jitter",
                  "loss_pct", "speed_mbps", "method"]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for rank, r in enumerate(results, start=1):
            writer.writerow({"rank": rank, **r})

    print(f"[INFO] Results saved to: {path}")


def quick_scan(args, console: Console) -> list[dict]:
    console.print("\n[bold cyan]Mode:[/bold cyan] Quick Scan")
    console.print(f"  Fetching Cloudflare IP ranges (IPv6: {args.ipv6})…")

    ranges = fetch_cloudflare_ranges(include_ipv6=args.ipv6)
    if not ranges:
        console.print("[red]ERROR: Could not fetch any IP ranges. Check your internet connection.[/red]")
        sys.exit(1)

    console.print(f"  Found [bold]{len(ranges)}[/bold] CIDR blocks.")

    # Build the IP sample pool.
    ip_pool = []
    for cidr in ranges:
        ip_pool.extend(sample_ips_from_cidr(cidr, args.sample))

    console.print(f"  Sampled [bold]{len(ip_pool)}[/bold] IPs (up to {args.sample} per CIDR).\n")

    return scan_all(ip_pool, workers=args.workers, test_speed=not args.no_speed, console=console)


def custom_scan(args, console: Console) -> list[dict]:
    path = Path(args.file)
    if not path.exists():
        console.print(f"[red]ERROR: File not found: {path}[/red]")
        sys.exit(1)

    console.print(f"\n[bold cyan]Mode:[/bold cyan] Custom Scan  ({path})")

    ip_list = []
    with open(path, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                ipaddress.ip_address(line)
                ip_list.append(line)
            except ValueError:
                console.print(f"  [yellow]Skipping invalid entry:[/yellow] {line!r}")

    if not ip_list:
        console.print("[red]ERROR: No valid IP addresses found in the file.[/red]")
        sys.exit(1)

    console.print(f"  Loaded [bold]{len(ip_list)}[/bold] IPs from file.\n")

    return scan_all(ip_list, workers=args.workers, test_speed=not args.no_speed, console=console)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cf_scanner",
        description="Scan Cloudflare IPs for latency, jitter, packet loss, and speed.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest="mode", required=True)

    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument(
        "--workers", type=int, default=DEFAULT_WORKERS, metavar="N",
        help=f"Number of parallel threads (default: {DEFAULT_WORKERS}).",
    )
    shared.add_argument(
        "--no-speed", action="store_true",
        help="Skip the download speed test (faster scan).",
    )
    shared.add_argument(
        "--csv", metavar="FILE",
        help="Save results to a CSV file.",
    )
    shared.add_argument(
        "--top", type=int, metavar="N",
        help="Display only the top N results in the table.",
    )

    quick_p = subparsers.add_parser(
        "quick",
        parents=[shared],
        help="Auto-fetch Cloudflare IP ranges and scan a random sample.",
    )
    quick_p.add_argument(
        "--sample", type=int, default=DEFAULT_SAMPLE, metavar="N",
        help=f"IPs to sample per CIDR block (default: {DEFAULT_SAMPLE}).",
    )
    quick_p.add_argument(
        "--ipv6", action="store_true",
        help="Include IPv6 ranges (requires IPv6 connectivity).",
    )

    custom_p = subparsers.add_parser(
        "custom",
        parents=[shared],
        help="Test a specific list of IPs from a text file.",
    )
    custom_p.add_argument(
        "--file", required=True, metavar="FILE",
        help="Path to a text file with one IP address per line.",
    )

    return parser


def main():
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    parser  = build_parser()
    args    = parser.parse_args()
    console = Console()

    console.print("\n[bold white]╔══════════════════════════════════════╗[/bold white]")
    console.print("[bold white]║    Cloudflare IP Scanner  v1.0       ║[/bold white]")
    console.print("[bold white]╚══════════════════════════════════════╝[/bold white]\n")

    if args.mode == "quick":
        results = quick_scan(args, console)
    elif args.mode == "custom":
        results = custom_scan(args, console)
    else:
        parser.print_help()
        sys.exit(1)

    reachable = [r for r in results if r["reachable"]]
    console.print(f"\n[bold]Scan complete.[/bold]  "
                  f"Reachable: [green]{len(reachable)}[/green] / "
                  f"[white]{len(results)}[/white] IPs\n")

    display_results(results, console, top_n=args.top)

    if args.csv:
        save_csv(results, args.csv)


if __name__ == "__main__":
    main()
