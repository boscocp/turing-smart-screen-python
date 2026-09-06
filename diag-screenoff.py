# SPDX-License-Identifier: GPL-3.0-or-later
#
# DIAGNOSTIC SCRIPT - not part of any pull request, do not merge.
#
# Issue #907: on some Turing/TURZX 3.5" (rev A) panels, exiting the app leaves the
# backlight on. ScreenOff() at library/lcd/lcd_comm_rev_a.py:141 only sends the
# SCREEN_OFF command and never touches brightness.
#
# This sends each candidate command ONE AT A TIME so we can see which one actually
# blanks the panel, instead of guessing. Results are written to diag-results.txt.
#
# Usage, from the repository root, with the system monitor STOPPED:
#     python diag-screenoff.py

from library.pythoncheck import check_python_version

check_python_version()

import time
import traceback

from library.lcd.lcd_comm_rev_a import LcdCommRevA, Command, Orientation

# "AUTO" detects the port. Replace with e.g. "COM3" if detection fails.
COM_PORT = "AUTO"
WIDTH, HEIGHT = 320, 480

# Brightness the panel is restored to between tests (config.yaml ships 20)
RESTORE_BRIGHTNESS = 20

RESULTS_FILE = "diag-results.txt"
RESULTS = []


def show_pattern(lcd):
    """Put readable content on the panel, so 'content cleared' is distinguishable
    from 'backlight actually off'."""
    lcd.Clear()
    lcd.DisplayText("SCREEN OFF TEST", 8, 100,
                    font="res/fonts/roboto/Roboto-Bold.ttf", font_size=26,
                    font_color=(255, 255, 255), background_color=(0, 0, 160))
    lcd.DisplayText("if you can read this\nthe backlight is ON", 8, 145,
                    font="res/fonts/roboto/Roboto-Regular.ttf", font_size=18,
                    font_color=(255, 255, 0), background_color=(0, 0, 160))


def restore(lcd):
    lcd.ScreenOn()
    lcd.SetBrightness(level=RESTORE_BRIGHTNESS)


def run_test(lcd, name, description, action):
    print("\n" + "-" * 68)
    print("TEST: %s" % name)
    print("      %s" % description)
    choice = input("      [Enter] to run, or 's' to skip: ").strip().lower()
    if choice == "s":
        RESULTS.append((name, "skipped", "-"))
        return

    try:
        show_pattern(lcd)
        time.sleep(1.5)
        print("      pattern shown. sending the command now...")
        action()
        time.sleep(1.5)
    except Exception:
        print("      !! the command raised an exception:")
        traceback.print_exc()
        RESULTS.append((name, "exception", "-"))
        return

    print("\n      LOOK AT THE PANEL. Which one is it?")
    print("        1 = fully dark, backlight OFF (no glow at all)")
    print("        2 = content gone, but backlight still ON (glow / background visible)")
    print("        3 = nothing changed, text still readable")
    print("        4 = something else (describe it to me afterwards)")
    observation = input("      your answer (1-4): ").strip() or "?"

    print("      restoring the panel...")
    try:
        restore(lcd)
        show_pattern(lcd)
        time.sleep(1.5)
        responsive = input("      did the pattern come back? (y/n): ").strip().lower() or "?"
    except Exception:
        print("      !! restore failed:")
        traceback.print_exc()
        responsive = "restore-failed"

    RESULTS.append((name, observation, responsive))
    print("      recorded: observation=%s, responsive=%s" % (observation, responsive))


if __name__ == "__main__":
    print("=" * 68)
    print("rev A screen-off diagnostic - issue #907")
    print("=" * 68)
    print("\nMake sure the system monitor (main.py / main.exe) is STOPPED, otherwise")
    print("it holds the COM port and this script cannot open it.\n")
    input("[Enter] to start: ")

    lcd = LcdCommRevA(com_port=COM_PORT, display_width=WIDTH, display_height=HEIGHT)

    # Same order as Display.initialize_display() in library/display.py
    print("\nresetting the display (takes ~5 seconds)...")
    lcd.Reset()
    lcd.InitializeComm()
    lcd.SetOrientation(orientation=Orientation.PORTRAIT)
    restore(lcd)

    sub_revision = str(lcd.sub_revision)
    print("detected sub-revision: %s" % sub_revision)
    print("detected size: %dx%d" % (lcd.display_width, lcd.display_height))

    # 1. Exactly what the app does today.
    run_test(lcd, "SCREEN_OFF (108) alone",
             "what ScreenOff() does today, at lcd_comm_rev_a.py:141",
             lambda: lcd.SendCommand(Command.SCREEN_OFF, 0, 0, 0, 0))

    # 2. The candidate that needs no undocumented command.
    run_test(lcd, "SetBrightness(0) alone",
             "byte-identical to the first command in issue #907. is the backlight controllable?",
             lambda: lcd.SetBrightness(level=0))

    # 3. Both together, in #907's order.
    run_test(lcd, "SetBrightness(0) + SCREEN_OFF (108)",
             "the two documented commands together - the minimal fix if this works",
             lambda: (lcd.SetBrightness(level=0), time.sleep(0.1),
                      lcd.SendCommand(Command.SCREEN_OFF, 0, 0, 0, 0)))

    # 4. The command the enum itself marks NOT TESTED.
    run_test(lcd, "TO_BLACK (103) alone",
             "marked '# NOT TESTED' at lcd_comm_rev_a.py:35, used nowhere else in the project",
             lambda: lcd.SendCommand(Command.TO_BLACK, 0, 0, 0, 0))

    # 5. Undocumented. Opt-in, and last.
    print("\n" + "=" * 68)
    print("The last test sends command 212. It appears NOWHERE in this project and")
    print("is not documented anywhere. Issue #907 sends it, but its author wrote")
    print("\"I don't know why my screen behaves like this\".")
    print("If it wedges the panel you may have to unplug it.")
    print("=" * 68)
    if input("\nrun the command-212 test? type YES to run, anything else skips: ").strip() == "YES":
        run_test(lcd, "command 212 (UNDOCUMENTED)",
                 "unknown command byte, sent last on purpose",
                 lambda: lcd.SendCommand(212, 0, 0, 0, 0))
    else:
        RESULTS.append(("command 212 (UNDOCUMENTED)", "skipped", "-"))

    header = [
        "rev A screen-off diagnostic - issue #907",
        "sub-revision: %s   size: %dx%d" % (sub_revision, lcd.display_width, lcd.display_height),
        "",
        "observation key: 1=fully dark  2=backlight still on  3=no change  4=other",
        "",
        "%-40s %-12s %s" % ("command", "observation", "came back"),
    ]
    lines = header + ["%-40s %-12s %s" % r for r in RESULTS]
    report = "\n".join(lines)

    print("\n" + "=" * 68)
    print(report)
    print("=" * 68)

    with open(RESULTS_FILE, "w") as f:
        f.write(report + "\n")
    print("\nsaved to %s - send me that file (or the table above)." % RESULTS_FILE)

    restore(lcd)
    lcd.closeSerial()
    print("serial port closed. done.")
