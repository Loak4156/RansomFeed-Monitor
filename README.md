
# RansomFeed Monitor

A lightweight Python script that monitors the [ransomfeed.it](https://ransomfeed.it/rss-complete.php) RSS feed for new ransomware incidents matching a specific keyword (e.g., a country or company name). When a match is found, it sends a detailed email alert using a customizable HTML template.

---

## ✨ Features

- Monitors [ransomfeed.it](https://ransomfeed.it) for new ransomware events.
- Filters events by configurable keyword.
- Sends alert emails using your system's Postfix (via `sendmail`).
- Smart email rate limiting:
  - ✅ Max 3 emails per minute.
  - ✅ Max 13 emails per day.
- Keeps track of already processed entries to avoid duplicates.
- Configuration moved to `config.ini`.
- Automatic log rotation (up to 10 MB, 2 backups).
- Clean and responsive HTML email template (with dark mode support).

---

## 🚀 Getting Started

### 1. Clone the repo
```bash
git clone https://github.com/Loak4156/ransomfeed-monitor.git
cd ransomfeed-monitor
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure settings
Edit the `config.ini` file:

```ini
[main]
rss_url = https://ransomfeed.it/rss-complete.php
keyword = USA
state_file = state.json
log_file = /var/log/ransomfeed_monitor.log
poll_interval = 300
record_retention_days = 12

[email]
from = YOUR_EMAIL
to = YOUR_RECIPIENT_EMAIL
emails_per_minute = 3
emails_per_day = 13
```

Make sure your system has `sendmail` configured and working (e.g. via Postfix).

---

## 🌐 File Structure

```
ransomfeed-monitor/
├── ransomfeed_monitor.py                # Main monitoring script
├── email_template_with_placeholders.html  # Responsive email template
├── config.ini                           # Configuration file
├── state.json                           # Auto-generated: stores processed IDs and email timestamps
├── requirements.txt                     # Python dependencies
├── README.md                            # Project documentation
```

---

## ⏱ Usage

```bash
python3 ransomfeed_monitor.py
```


## 📊 Sample Email Output

- Subject: `New event with keyword 'USA': XYZ Corp hit by BlackCat`
- Includes:
  - Victim name
  - Ransomware group
  - Date and time
  - Source link
  - Cleaned description from RSS

---

## 📝 License
MIT License

---

## 🤔 Why?
This tool helps CTI analysts and threat researchers stay alert to new ransomware attacks relevant to specific targets of interest.

---

## 😎 Author
**Vasily Kononov**  
Threat Intelligence Lead  

