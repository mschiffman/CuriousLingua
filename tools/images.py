"""Lists the lessons that are missing pictures, and the folder each one expects.

    python tools/images.py

New pictures are processed by 1_images.bat (Downloads -> G:\\My Drive\\_YOUTUBE -> img\\ytstory,
80% size, Squoosh/MozJPEG quality 75, via tools/convert.py).
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

sys.stdout.reconfigure(encoding="utf-8")
n = 0
for L in lib.lessons():
    miss = [x for x in lib.images(L) if not lib.find(x)]
    if miss:
        n += 1
        print(f"  {L['id']:<44} {len(miss)} missing in {L['img_dir'].replace('/', chr(92))}")
print(f"{n} lesson(s) with missing pictures" if n else "No lesson is missing pictures.")
