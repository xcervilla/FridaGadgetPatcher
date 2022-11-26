import argparse
import sys
import tempfile
import zipfile
import shutil
import subprocess
import time
import pathlib
import plistlib

def checkOS():
    # TODO check architecture of CPU (ARM 32/64 bit , Intel 64 bit , etc...)
    if sys.platform.startswith("linux"):
        print("Tool not implemented yet for Linux")
        exit()
    elif not sys.platform.startswith("darwin"):
        print("OS not supported by the tool, exiting program")
        exit()

def main(gadgetFilePath: str, ipaFilePath: str, insertDylibPath: str):
    tempDir = tempfile.TemporaryDirectory().name
    ipaFileName = ipaFilePath.split("/")[-1]

    # Uncompress IPA file in tmp dir
    try:
        ipaFile = zipfile.ZipFile(ipaFilePath)
        ipaFile.extractall(tempDir)
        #time.sleep(60)
    except zipfile.BadZipFile as bzf:
        print("IPA cannot be uncompressed, exiting program")
        exit()
    except FileNotFoundError as e:
        print("Provided IPA file cannot be found, exiting program")
        exit()
    
    # Get .app dir inside the Payload dir so we can get the binary
    payloadDir = pathlib.Path(tempDir).joinpath("Payload")
    appDir = None
    for elem in payloadDir.iterdir():
        if elem.is_dir() and str(elem).endswith(".app"):
            appDir = elem

    # Create Frameworks folder if it doesn't exits
    frameworksDir = appDir.joinpath("Frameworks")
    frameworksDir.mkdir(exist_ok=True)

    # Move FridaGadget.dylib into Frameworks dir
    shutil.copyfile(gadgetFilePath, frameworksDir.joinpath("FridaGadget.dylib"))

    # Parse Info.plist to get binary name
    with open(str(appDir.joinpath("Info.plist")), "rb") as f:
        infoPlist = plistlib.load(f)
        binaryName = infoPlist["CFBundleExecutable"]
    binaryPath = appDir.joinpath(binaryName)
    # Execute insert_dylib
    try:
        proc = subprocess.run([insertDylibPath, "--inplace",
                                                "--strip-codesig",
                                                "@executable_path/Frameworks/FridaGadget.dylib",
                                                str(binaryPath)],
                                                check=True,
        # Send 'y' input as it will state that the path doesn't exist, but it exists
                                                input=bytes("y", "ascii"),
                                                capture_output=True)
        proc.check_returncode() # Double check that retcode is 0
        print("FridaGadget.dylib successfully inserted into binary")

    except subprocess.CalledProcessError as cpe:
        print("Error while using insert_dylib tool")
        exit()
    
    # Re-Compress again the IPA
    shutil.make_archive("PATCHED_{}".format(ipaFileName), "zip", tempDir)


if __name__ == "__main__":
    # Parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("frida_gadget", help="Path of the Frida Gadget dylib")
    parser.add_argument("ipa_file", help="Path of the IPA file to be patched")
    parser.add_argument("insert_dylib_bin", help="Path of the insert_dylib binary")
    args = parser.parse_args()
    checkOS()
    main(args.frida_gadget, args.ipa_file, args.insert_dylib_bin)
