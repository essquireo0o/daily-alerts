# Daily Alerts — the Windows appointment reminder you actually can't miss

**Free full-screen alarm reminder for Windows. Never miss a dentist appointment, meeting, medication, or deadline again.** Daily Alerts puts a whole month on screen, lets you set a custom alert time and your own message for every appointment, and then — at that time — takes over your entire screen with a loud, flashing, impossible-to-ignore alarm that does not go away until you click it.

Most reminder apps show a tiny notification in the corner that you swipe away without reading. This one is built for people who keep missing things anyway. It runs quietly in the **system tray** and stays out of the way until it needs to scream at you.

## Why people use it

- You keep **missing appointments** even though you "set a reminder."
- A small toast notification isn't enough — you need something you **physically cannot ignore**.
- You want the reminder to say **your** words ("Go to the dentist", "Leave NOW for the airport"), in giant letters.
- You want it running in the background **all the time**, without a browser tab or a subscription.

## Features

- **Full-month calendar view** — see every appointment for the whole month at a glance, with today highlighted. Flip between months, jump back to today.
- **Alarms you can't miss** — at your chosen alert time the screen goes full-screen red, flashes, beeps loudly, and shows your custom message in huge text. The only way out is to click **OK — I'm going** (or **Snooze 5 min**).
- **Your own alert time** — dentist at 1:00 pm? Set the alarm for 12:15 pm so you actually leave on time.
- **Your own message** — type exactly what you want it to shout at you.
- **Weekly repeat** — for standing appointments, medication, and recurring meetings.
- **System tray** — closing or minimizing the window sends it to the tray; it keeps running so alarms always fire.
- **Start with Windows** — one click adds it to startup so it's always watching.
- **No account, no cloud, no subscription** — your appointments are saved locally in a plain JSON file. Nothing leaves your PC.
- **No dependencies to fuss with** — pure Python plus a small tray library.

## Install & run

1. Install [Python 3.10+](https://www.python.org/downloads/) for Windows.
2. Install the system-tray dependency:
   ```
   pip install pystray pillow
   ```
3. Run it (no console window):
   ```
   pythonw daily_alerts.py
   ```
4. In the app, click **Start with Windows** so it launches automatically and lives in your system tray.

Your appointments are stored at `%APPDATA%\DailyAlerts\appointments.json`.

## How an alarm works

Add an appointment → give it a day, an appointment time, an **alert time**, and the message you want. Daily Alerts checks every few seconds. When the alert time arrives it fires the full-screen alarm and keeps it on top of everything until you dismiss it. Snooze re-fires it in five minutes. Miss the window entirely and it still alerts you up to fifteen minutes past the appointment, so a late start doesn't cost you the reminder.

## Keywords

Windows appointment reminder, full screen alarm, desktop reminder app, never miss an appointment, loud alarm reminder, medication reminder Windows, meeting reminder app, calendar alarm, ADHD reminder app, system tray reminder, free reminder software.

## License

MIT — do whatever you want with it.


---

## Copyright

Copyright © 2026 ING Mining LLC. Released under the MIT License (see LICENSE).

Contact: ns@ingmining.com
