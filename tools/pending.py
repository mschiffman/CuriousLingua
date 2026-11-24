"""Record, check and upload every lesson whose audio is still pending. This is what record_pending.bat runs.

    python -E tools/pending.py            list, ask, record the missing clips, wait, upload
    python -E tools/pending.py --list     only list what is pending

Card pages and dialogues only. Word lists, reading texts and picture stories have their own commands: use 2_audio.bat.
A lesson counts as soon as its file says "aud_ext": "mp3?v=pending", whether or not you have read it yet."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio

HANDLED = ("cards", "dialogue")


def main():
    rows = audio.status(show=False)
    todo = [r for r in rows if r[0].get("type") in HANDLED and not r[0].get("audio_file")]
    other = [r[0]["id"] for r in rows if r not in todo]
    if not todo:
        print("No card page or dialogue is waiting for audio.")
    for L, total, miss, chars in todo:
        state = "ready to upload" if not miss else f"{len(miss)} of {total} clips to record"
        print(f"  {L['id']:<44} {state:<28} {chars:>6,} characters")
    if other:
        print("\nNot handled here (use 2_audio.bat): " + ", ".join(other))
    if not todo or "--list" in sys.argv:
        return
    chars = sum(r[3] for r in todo)
    try:
        left, limit = audio.balance()
        print(f"\nElevenLabs: {left:,} characters left of {limit:,}")
    except BaseException as err:
        print(f"\nElevenLabs balance: could not read it ({err})")
    if chars and input(f"Record about {chars:,} characters for {sum(1 for r in todo if r[2])} lesson(s)? (y/n) ").strip().lower() != "y":
        return

    failed = []
    for L, total, miss, _ in todo:
        if not miss:
            continue
        print(f"\n=== {L['id']} ===")
        try:
            audio.make(L, [], [])
        except SystemExit as err:   # one lesson failing does not stop the others
            print(f"  stopped: {err}")
            failed.append(L["id"])
    ready = [L for L, *_ in todo if L["id"] not in failed and not audio.missing(L)]
    if failed:
        print("\nNot recorded: " + ", ".join(failed))
    if not ready:
        return
    print(f'\nListen to any clip marked "<<< check" above (Japanese and Korean: read the "heard" column).')
    input(f"Press Enter to upload {len(ready)} lesson(s), or close this window to stop here. ")
    for L in ready:
        print(f"\n=== upload {L['id']} ===")
        try:
            audio.upload(L)
        except SystemExit as err:
            print(f"  stopped: {err}")
    print("\nDone. Run 5_publish.bat to put the pages online.")


if __name__ == "__main__":
    main()
