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
    if not (sys.platform.startswith("darwin")):
        print("OS not supported by the tool, exiting program")
        exit()

def getInsertDylibOption(args):
    if args.bundled_insert_dylib:
        return "bundled"
    elif args.system_insert_dylib:
        return "system"
    else:
        return args.external_insert_dylib

def compileInsertDylib():
    scriptPath = pathlib.Path(__file__).parent
    outputPath = scriptPath.joinpath("insert_dylib")
    insertDylibSourcePath = scriptPath.joinpath("insert_dylib_source").joinpath(sys.platform).joinpath("main.c")
    if sys.platform.startswith("darwin"):
        try:
            proc = subprocess.run(["gcc", insertDylibSourcePath,"-o", outputPath], check=True)
        except subprocess.CalledProcessError as cpe:
                print("Error while compiling insert_dylib, exiting program")
                exit()
    elif sys.platform.startswith("linux"):
        try:
            includePath = insertDylibSourcePath.parent.joinpath("include")
            proc = subprocess.run(["gcc", insertDylibSourcePath,"-I", includePath,"-o", outputPath], check=True)
        except subprocess.CalledProcessError as cpe:
                print("Error while compiling insert_dylib, exiting program")
                exit()

def getInsertDylibPath(insertDylibOption):
    if insertDylibOption == "bundled":
        binaryPath = pathlib.Path(__file__).parent.joinpath("insert_dylib")
        if not binaryPath.exists():
            compileInsertDylib()
        return binaryPath
    elif insertDylibOption == "system":
        try:
            proc = subprocess.run(["which", "insert_dylib"], check=True)
            return proc.stdout
        except subprocess.CalledProcessError as cpe:
            print("insert_dylib binary cannot be found in $PATH using `which`, exiting program")
            exit()
    else:
        if not pathlib.Path(insertDylibOption).exists():
            print("insert_dylib binary cannot be found in the specified path, exiting program")
            exit()
        else:
            return insertDylibOption


def main(gadgetFilePath: str, ipaFilePath: str, insertDylibOption: str):
    insertDylibPath = getInsertDylibPath(insertDylibOption)

    tempDir = tempfile.TemporaryDirectory().name
    ipaFileName = ipaFilePath.split("/")[-1]

    # Uncompress IPA file in tmp dir
    try:
        ipaFile = zipfile.ZipFile(ipaFilePath)
        ipaFile.extractall(tempDir)
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
    checkOS() # Checks script is running on Linux or macOS
    # Parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("frida_gadget", help="Path of the Frida Gadget dylib")
    parser.add_argument("ipa_file", help="Path of the IPA file to be patched")
    # insert_dylib options
    insert_dylib_mutex = parser.add_mutually_exclusive_group(required=True)
    insert_dylib_mutex.add_argument("-bundled-insert-dylib",
                                    action="store_true",
                                    help="Uses bundled insert_dylib (Will compile it if not compiled)")
    insert_dylib_mutex.add_argument("-system-insert-dylib", action="store_true", help="Search in PATH for insert_dylib binary and use it")
    insert_dylib_mutex.add_argument("-external-insert-dylib", metavar="INSERT_DYLIB_PATH", help="Path of the insert_dylib binary")
    args = parser.parse_args()
    insertDylibOption = getInsertDylibOption(args)
    main(args.frida_gadget, args.ipa_file, insertDylibOption)
