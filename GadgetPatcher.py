import argparse
import sys
import tempfile
import zipfile
import shutil
import subprocess
import pathlib
import plistlib
from urllib import request
import io
import lzma
import time
import os

def checkRequisites():
    if not (sys.platform.startswith("darwin") or sys.platform.startswith("linux")):
        print("OS not supported by the tool, exiting program")
        exit()
    try:
        subprocess.run(["which", "gcc"], check=True, capture_output=True)
    except subprocess.CalledProcessError as cpe:
        print("GCC compiler cannot be found in $PATH using `which`, exiting program")
        exit()

def getGadget(options):
    if options.download_gadget:
        # Download gadget to a temp dir
        versionResponse = request.urlopen("https://github.com/frida/frida/releases/latest")
        latestVersion = versionResponse.url.split("/")[-1]
        gitHubUrl = "https://github.com/frida/frida/releases/download/{%VERSION%}/frida-gadget-{%VERSION%}-ios-universal.dylib.xz"
        with request.urlopen(gitHubUrl.replace("{%VERSION%}", latestVersion)) as response:
            if response.status != 200:
                print("Response returned while downloading Gadget was not 200 OK. Exiting")
                exit()
            gadgetData = io.BytesIO(response.read())
        # Uncompress XZ file
        uncompressedGadget = lzma.open(gadgetData) 
        # Write to temp file
        gadgetTempFile = tempfile.NamedTemporaryFile("wb", suffix=".tmpdylib", delete=False)
        gadgetTempFile.write(uncompressedGadget.read())
        print(gadgetTempFile.name)
        return gadgetTempFile.name           
        
    else:
        return options.gadget

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

def getInsertDylibPath():
    binaryPath = pathlib.Path(__file__).parent.joinpath("insert_dylib")
    if not binaryPath.exists():
        compileInsertDylib()
    return binaryPath


def main(gadgetFilePath: str, ipaFilePath: str):
    insertDylibPath = getInsertDylibPath()

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
    # Delete src gadget file if is temp
    if gadgetFilePath.endswith(".tmpdylib"):
        os.remove(gadgetFilePath)

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
    os.rename("PATCHED_{}.zip".format(ipaFileName),"PATCHED_{}".format(ipaFileName))


if __name__ == "__main__":
    checkRequisites() # Checks script is running on Linux or macOS and if GCC is installed
    # Parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("ipa_file", help="Path of the IPA file to be patched")
    # Gadget Mutex
    gadgetMutex = parser.add_mutually_exclusive_group()
    gadgetMutex.add_argument("--gadget", metavar="FRIDA_GADGET_PATH", help="Path of the Frida Gadget dylib")
    gadgetMutex.add_argument("--download-gadget", action="store_true", help="Downloads latest iOS FridaGadget from GitHub")
    args = parser.parse_args()
    gadgetPath = getGadget(args)
    main(gadgetPath, args.ipa_file)