import subprocess
import sys
import os

def main():
    print("===========================================")
    print(" Building PLC Barcode Router for Linux (ELF)")
    print("===========================================")
    
    # 1. Install dependencies
    print("\n[1/3] Installing requirements & PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "pyinstaller"])

    # 2. Run PyInstaller with main.spec
    print("\n[2/3] Building executable with PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "PyInstaller", "main.spec", "--clean"])

    # 3. Output info
    dist_dir = os.path.join(os.getcwd(), "dist")
    print(f"\n[3/3] Build completed successfully!")
    print(f"Linux binary created in: {dist_dir}")
    print("To run on Linux:")
    print("  chmod +x dist/main_v2.05")
    print("  ./dist/main_v2.05")

if __name__ == "__main__":
    main()
