# ☁️ Cloudflare IP Scanner

A fast, cross-platform Python tool that scans Cloudflare IP addresses and measures:

- **Ping / Latency** (ms) — via system `ping` with TCP fallback
- **Jitter** (ms) — standard deviation across ping samples
- **Packet Loss** (%) — from ping statistics
- **Download Speed** (Mbps) — direct measurement to each IP

Supports **Quick Scan** (auto-fetches Cloudflare's published IP ranges) and **Custom Scan** (your own list of IPs from a text file). All tests run in parallel for speed.

---

## 📸 Output Preview

```
╔══════════════════════════════════════╗
║    Cloudflare IP Scanner  v1.0       ║
╚══════════════════════════════════════╝

Mode: Quick Scan
  Found 15 CIDR blocks.
  Sampled 75 IPs (up to 5 per CIDR).

╭──────┬──────────────────┬────────────┬─────────────┬────────┬─────────────┬────────╮
│ Rank │ IP Address       │ Ping (ms)  │ Jitter (ms) │ Loss % │ Speed Mbps  │ Method │
├──────┼──────────────────┼────────────┼─────────────┼────────┼─────────────┼────────┤
│    1 │ 104.16.0.5       │ 11.4       │ 0.8         │ 0%     │ 312.5       │ icmp   │
│    2 │ 103.21.244.12    │ 14.2       │ 1.1         │ 0%     │ 289.0       │ icmp   │
│    3 │ 141.101.64.3     │ 18.7       │ 2.3         │ 0%     │ 201.3       │ icmp   │
│  ... │ ...              │ ...        │ ...         │ ...    │ ...         │ ...    │
╰──────┴──────────────────┴────────────┴─────────────┴────────┴─────────────┴────────╯

Scan complete.  Reachable: 68 / 75 IPs
```

Colour coding: 🟢 ≤ 50 ms · 🟡 ≤ 150 ms · 🔴 > 150 ms

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/cloudflare-ip-scanner.git
cd cloudflare-ip-scanner
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> Python 3.10 or later is required.

### 3. Run a quick scan

```bash
python cf_scanner.py quick
```

---

## 📖 Usage

### Quick Scan

Automatically fetches Cloudflare's published IP ranges and randomly samples IPs from each CIDR block.

```bash
python cf_scanner.py quick [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--sample N` | 5 | IPs to sample per CIDR block |
| `--ipv6` | off | Include IPv6 ranges |
| `--workers N` | 50 | Parallel threads |
| `--no-speed` | off | Skip the download speed test |
| `--csv FILE` | — | Save results to a CSV file |
| `--top N` | — | Show only the top N results |

**Examples:**

```bash
# Default quick scan
python cf_scanner.py quick

# 10 IPs per block, IPv6 included, 100 threads, save to CSV, show top 20
python cf_scanner.py quick --sample 10 --ipv6 --workers 100 --csv results.csv --top 20

# Fast scan without speed test
python cf_scanner.py quick --no-speed --top 10
```

---

### Custom Scan

Reads a plain-text file where each line is an IP address and tests exactly those IPs.

```bash
python cf_scanner.py custom --file <FILE> [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--file FILE` | required | Path to IP list file |
| `--workers N` | 50 | Parallel threads |
| `--no-speed` | off | Skip the download speed test |
| `--csv FILE` | — | Save results to a CSV file |
| `--top N` | — | Show only the top N results |

**Examples:**

```bash
# Test IPs from a file
python cf_scanner.py custom --file my_ips.txt

# Save results, skip speed test
python cf_scanner.py custom --file my_ips.txt --no-speed --csv output.csv
```

**IP list file format** (`my_ips.txt`):

```
# Lines starting with # are comments and are ignored
# Blank lines are also ignored

104.16.0.1
104.17.0.1
103.21.244.0
2606:4700::1
```

---

## ⚙️ How It Works

```
┌────────────────────────────────────────────────────────────────┐
│                        cf_scanner.py                           │
│                                                                │
│  Quick Scan                    Custom Scan                     │
│  ──────────                    ───────────                     │
│  Fetch CF IP ranges  ────┐     Read IPs from file  ────┐      │
│  (cloudflare.com/ips-v4) │                              │      │
│  Sample N IPs per CIDR ──┘                              │      │
│                          │                              │      │
│                    ┌─────▼──────────────────────────────▼───┐  │
│                    │       Thread Pool (parallel scan)       │  │
│                    │                                        │  │
│                    │  For each IP:                          │  │
│                    │   1. system ping × 5 → RTTs            │  │
│                    │      → avg latency, jitter, loss%      │  │
│                    │   2. TCP fallback if ICMP blocked       │  │
│                    │   3. HTTP download → Mbps               │  │
│                    └────────────────┬───────────────────────┘  │
│                                     │                          │
│                    ┌────────────────▼───────────────────────┐  │
│                    │  Sort by latency · Display table        │  │
│                    │  Optional: save to CSV                  │  │
│                    └────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

### Metrics explained

| Metric | What it means | Good value |
|---|---|---|
| **Ping / Latency** | Round-trip time for a packet to reach the IP and return | < 50 ms |
| **Jitter** | Variation between ping samples (consistency measure) | < 5 ms |
| **Packet Loss** | % of ping packets that never received a reply | 0% |
| **Download Speed** | Throughput measured by downloading 5 MB from that specific IP | As high as possible |

### TCP Fallback

On systems where ICMP (ping) is blocked — common on cloud VMs, containers, and some corporate networks — the scanner automatically falls back to a TCP connect test on port 443. This provides a single latency reading but cannot measure jitter or packet loss.

---

## 🖥️ Platform Support

| Platform | ICMP Ping | TCP Fallback | Speed Test |
|---|---|---|---|
| Linux | ✅ | ✅ | ✅ |
| macOS | ✅ | ✅ | ✅ |
| Windows | ✅ | ✅ | ✅ |

> **Note:** On Linux, running without `sudo` may restrict ICMP. If ping results seem wrong, try `sudo python cf_scanner.py quick`.

---

## 📦 Output: CSV Format

When `--csv results.csv` is used, the file contains:

```
rank,ip,reachable,avg_ms,jitter,loss_pct,speed_mbps,method
1,104.16.0.5,True,11.4,0.8,0.0,312.5,icmp
2,103.21.244.12,True,14.2,1.1,0.0,289.0,icmp
...
```

---

## 🤝 Contributing

Contributions are welcome! Please open an issue or pull request for:
- Bug fixes
- New output formats (JSON, HTML report)
- Additional metrics (TTL, geo-location lookup)
- GUI wrapper

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## ⚠️ Disclaimer

This tool is intended for personal network diagnostics and research. Use responsibly and in accordance with Cloudflare's Terms of Service. Do not use for automated large-scale abuse or DDoS testing.
