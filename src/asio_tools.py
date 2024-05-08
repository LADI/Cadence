import os
import shutil

from shared import HOME


class _MainObj:
    have_wine = bool(shutil.which('regedit'))
    wine_prefix = ''
    if have_wine:
        wine_prefix = os.getenv("WINEPREFIX")
        if not wine_prefix:
            wine_prefix = os.path.join(HOME, ".wine")
    
    
_main_obj = _MainObj

def have_wine() -> bool:
    return _main_obj.have_wine

def getWineAsioKeyValue(key: str, default: int) -> str:
    wineFile = os.path.join(_main_obj.wine_prefix, "user.reg")

    if not os.path.exists(wineFile):
        return default

    wineDumpF = open(wineFile, "r")
    wineDump = wineDumpF.read()
    wineDumpF.close()

    wineDumpSplit = wineDump.split("[Software\\\\Wine\\\\WineASIO]")

    if len(wineDumpSplit) <= 1:
        return default

    wineDumpSmall = wineDumpSplit[1].split("[")[0]
    keyDumpSplit = wineDumpSmall.split('"%s"' % key)

    if len(keyDumpSplit) <= 1:
        return default

    keyDumpSmall = keyDumpSplit[1].split(":")[1].split("\n")[0]
    return keyDumpSmall

def smartHex(value: int, length: int) -> str:
    hexStr = hex(value).replace("0x","")

    if len(hexStr) < length:
        zeroCount = length - len(hexStr)
        hexStr = "%s%s" % ("0"*zeroCount, hexStr)

    return hexStr