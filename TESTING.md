# Windows test session

Branch: `test/windows-diag`. **This branch is for testing only — it is never opened as a pull
request.** It contains the fix from `fix/rev-a-screen-off` plus a throwaway diagnostic script.

Hardware in question: Turing 3.5" (`REVISION: A`), Windows, started from Task Scheduler.

---

## 1. Get the code onto the Windows PC

Needs [Python 3.9+](https://www.python.org/downloads/windows/) (tick *"Add python.exe to PATH"*)
and [Git for Windows](https://git-scm.com/download/win).

Open **PowerShell** and run:

```powershell
git clone https://github.com/boscocp/turing-smart-screen-python.git
cd turing-smart-screen-python
git checkout test/windows-diag
python -m pip install -r requirements.txt
```

If `pip` fails with a `401` error, it is picking up a private registry. Force public PyPI:

```powershell
python -m pip install --index-url https://pypi.org/simple -r requirements.txt
```

---

## 2. Experiment B — which command actually blanks the panel

This is the one that decides what goes into the fix for
[issue #907](https://github.com/mathoudebine/turing-smart-screen-python/issues/907).

**Stop the system monitor first** (tray icon → Exit, or `taskkill /im main.exe`, and disable the
Task Scheduler task for now). While it runs it holds the COM port and the script cannot open it.

```powershell
python diag-screenoff.py
```

What it does: shows a readable test pattern, sends **one** command, waits for you to look at the
panel, then restores it. Five candidates, in this order:

| # | what is sent | why |
|---|---|---|
| 1 | `SCREEN_OFF` (108) | exactly what `ScreenOff()` does today (`lcd_comm_rev_a.py:141`) |
| 2 | `SetBrightness(0)` | byte-identical to the first command in #907; needs no undocumented byte |
| 3 | `SetBrightness(0)` + `SCREEN_OFF` | the minimal candidate fix |
| 4 | `TO_BLACK` (103) | marked `# NOT TESTED` in the enum, used nowhere else in the project |
| 5 | command `212` | **undocumented, opt-in.** You must type `YES`. Skip it on the first run. |

After each one, answer:

- `1` = fully dark, backlight off (no glow at all)
- `2` = content gone, but backlight still on ← **this is your current symptom**
- `3` = nothing changed
- `4` = something else

Results are printed and saved to `diag-results.txt`. **Send me that file.**

If the panel stops responding at any point, unplug it and plug it back in, then re-run.

> Command `212` is skipped unless you type `YES`. It appears nowhere in this project and is not
> documented anywhere; #907 sends it but its author wrote *"I don't know why my screen behaves like
> this"*. Only worth trying if tests 1–4 all fail to blank the panel.

---

## 3. Experiment A — is LibreHardwareMonitor involved in the PC freeze?

Separate question, runs over days rather than minutes.

Edit `config.yaml` and change:

```yaml
  HW_SENSORS: AUTO
```

to:

```yaml
  HW_SENSORS: PYTHON
```

That bypasses LibreHardwareMonitor and its ring-0 driver completely. You lose CPU temperature and
fan speed; everything else keeps working, and it no longer needs administrator rights.

Then use the PC normally for a few days.

- **Freeze stops** → LibreHardwareMonitor is implicated, and the thread-safety PR is worth writing.
- **Freeze continues** → LHM is not the cause and we look somewhere else. Do not open that PR.

Note whether the boot freeze also changes, but treat that as an observation only — it is
intermittent, so a few clean boots prove nothing either way.

---

## 4. Testing the exit fix (already on this branch)

Commit `fix(scheduler): aguarda o envio ao display concluir antes de encerrar` makes the app wait
for the display write to actually complete before exiting, and closes the serial port.

With the system monitor running normally (`python main.py`):

1. Exit from the tray icon → note whether the panel behaves any differently than before.
2. `taskkill /im python.exe` (or `main.exe`) → same check.
3. Look at `log.log` for the line `(Waited N.Ns)` after *"Waiting for all pending request"*.
   Before this fix it was always `0.0s`. A non-zero value means the flush is now real.

This fix on its own is **not** expected to blank your panel — that needs the `ScreenOff` change,
which is what Experiment B decides. It makes sure the command is not cut off mid-send.

---

## 5. Building the .exe (later, once the fix is settled)

```powershell
pyinstaller --noconfirm turing-system-monitor.spec
.\dist\turing-system-monitor\main.exe
```

Windows Defender / SmartScreen may flag the result. That is inherent to this project — the bundle
carries the LibreHardwareMonitor DLLs and the spec sets `upx=True`. The upstream maintainer has
fought the same false positives publicly. Set `upx=False` in the spec if it gets in the way.

Keep `WEATHER_API_KEY` empty when building: the spec bakes `config.yaml` into the bundle.
