#!/usr/bin/env python3
import glob
import os
import shutil

def main():
    os.makedirs("delivery/USA", exist_ok=True)
    os.makedirs("delivery/UK", exist_ok=True)
    
    # 1. Copy clean deduplicated US files into delivery/USA/
    if os.path.exists("delivery_clean"):
        for f in glob.glob("delivery_clean/*.csv"):
            dst = os.path.join("delivery/USA", os.path.basename(f))
            shutil.copy(f, dst)
            print(f"-> delivery/USA/{os.path.basename(f)}")
            
    # 2. Clean up top-level files in delivery/ if they exist
    for f in glob.glob("delivery/*.csv"):
        try:
            os.remove(f)
        except Exception:
            pass

    print("Folder structure organized: delivery/USA/ and delivery/UK/ ready!")

if __name__ == "__main__":
    main()
