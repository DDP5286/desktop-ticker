# Desktop Ticker

A tiny always-on-top Windows widget that shows the live **Bitcoin** price and the **S&P 500**:
**SPY** during regular market hours, **ES futures** after hours, overnight and on weekends.

![Desktop Ticker screenshot](docs/screenshot.png)

- BTC updates every 2 seconds (shows 24h change)
- SPY / ES update every 5 seconds (shows change from previous close)
- Switches between SPY and ES automatically using the exchange's own session times, so holidays and early closes are handled
- Drag it anywhere on your desktop; it remembers where you left it
- No API keys, no extra packages, one file

## Requirements

- Windows 10 or 11
- [Python 3](https://www.python.org/downloads/) (3.9 or newer). The default installer includes everything needed (tkinter).

## Run it

1. Download this repo (green **Code** button → **Download ZIP**, then unzip), or clone it:
   ```
   git clone https://github.com/DDP5286/desktop-ticker.git
   ```
2. Double-click `ticker.pyw`, or run:
   ```
   pythonw ticker.pyw
   ```

The widget appears in the bottom-right corner, just above the taskbar.

## Using it

- **Move:** drag with the left mouse button
- **Options:** right-click for *Always on top*, *Reset position* and *Exit*

Your position and settings are saved in `%APPDATA%\desktop-ticker.json`.

## Start it with Windows

Run this in PowerShell from the folder that contains `ticker.pyw`:

```powershell
$lnk = Join-Path ([Environment]::GetFolderPath('Startup')) 'Desktop Ticker.lnk'
$s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
$s.TargetPath = (Get-Command pythonw).Source
$s.Arguments = '"' + (Resolve-Path .\ticker.pyw) + '"'
$s.WorkingDirectory = (Get-Location).Path
$s.Save()
```

Keep the folder where it is afterwards, because the shortcut points to it.
To stop it starting with Windows, turn off **Desktop Ticker** in Task Manager → *Startup apps*, or delete the shortcut
(press `Win + R`, type `shell:startup`, and delete `Desktop Ticker.lnk`).

## Data sources

- **BTC:** [Coinbase Exchange public API](https://docs.cdp.coinbase.com/exchange/)
- **SPY and ES futures:** Yahoo Finance's public chart endpoint. It's unofficial and undocumented, so it may change or stop working without notice.

Prices are for personal, informational use only. They may be delayed or wrong, so don't trade on them.

## License

[MIT](LICENSE)
