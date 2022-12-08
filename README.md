# FridaGadgetPatcher
Tool to patch an IPA file with FridaGadget.dylib

## Usage
```
$ python3 GadgetPatcher.py --help
usage: GadgetPatcher.py [-h] [--gadget FRIDA_GADGET_PATH | --download-gadget] ipa_file

positional arguments:
  ipa_file              Path of the IPA file to be patched

optional arguments:
  -h, --help            show this help message and exit
  --gadget FRIDA_GADGET_PATH
                        Path of the Frida Gadget dylib
  --download-gadget     Downloads latest iOS FridaGadget from GitHub
```
