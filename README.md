# FridaGadgetPatcher
Tool to patch an IPA file with FridaGadget.dylib

## Usage
```
$ python3 GadgetPatcher.py --help
usage: GadgetPatcher.py [-h]
                        (-bundled-insert-dylib | -system-insert-dylib | -external-insert-dylib INSERT_DYLIB_PATH)
                        frida_gadget ipa_file

positional arguments:
  frida_gadget          Path of the Frida Gadget dylib
  ipa_file              Path of the IPA file to be patched

optional arguments:
  -h, --help            show this help message and exit
  -bundled-insert-dylib
                        Uses bundled insert_dylib (Will compile it if not compiled)
  -system-insert-dylib  Search in PATH for insert_dylib binary and use it
  -external-insert-dylib INSERT_DYLIB_PATH
                        Path of the insert_dylib binary
```
