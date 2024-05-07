
import os
from subprocess import getoutput
from PyQt5.QtWidgets import QApplication


class CalesonSystemCheck(object):
    ICON_ERROR = 0
    ICON_WARN = 1
    ICON_OK = 2

    def __init__(self):
        object.__init__(self)

        self.name = self.tr("check")
        self.icon = self.ICON_OK
        self.result = self.tr("yes")

        self.moreInfo = self.tr("nothing to report")

    def tr(self, text: str):
        return QApplication.translate("CalesonSystemCheck", text)
    
    def get_id(self)->str:
        return ''


class CalesonSystemCheck_audioGroup(CalesonSystemCheck):
    def __init__(self):
        CalesonSystemCheck.__init__(self)

        self.name = self.tr("User in audio group")

        user = getoutput("whoami").strip()
        groups = getoutput("groups").strip().split(" ")

        if "audio" in groups:
            self.icon = self.ICON_OK
            self.result = self.tr("Yes")
            self.moreInfo = None

        else:
            fd = open("/etc/group", "r")
            groupRead = fd.read().strip().split("\n")
            fd.close()

            onAudioGroup = False
            for lineRead in groupRead:
                if lineRead.startswith("audio:"):
                    groups = lineRead.split(":")[-1].split(",")
                    if user in groups:
                        onAudioGroup = True
                    break

            if onAudioGroup:
                self.icon = self.ICON_WARN
                self.result = self.tr("Yes, but needs relogin")
                self.moreInfo = None
            else:
                self.icon = self.ICON_ERROR
                self.result = self.tr("No")
                self.moreInfo = None

    def get_id(self)->str:
        return 'audio_group'

    def tr(self, text):
        return QApplication.translate("CalesonSystemCheck_audioGroup", text)


class CalesonSystemCheck_kernel(CalesonSystemCheck):
    def __init__(self):
        CalesonSystemCheck.__init__(self)

        self.name = self.tr("Current kernel")

        uname3 = os.uname()[2]
        uname4 = getoutput("uname -a").strip().split()

        versionInt = []
        versionStr = uname3.split("-",1)[0]
        versionSplit = versionStr.split(".")

        for split in versionSplit:
            if split.isdigit():
                versionInt.append(int(split))
            else:
                versionInt = [0, 0, 0]
                break

        self.result = versionStr + " "

        if "PREEMPT" in uname4 or "PREEMPT_RT" in uname4:
            self.icon = self.ICON_OK
            if "PREEMPT" in uname4:
                self.moreInfo = self.tr("Be sure to properly configure your kernel.")
                self.result  += self.tr("PREEMPT")
            else:
                self.moreInfo = None
            #elif versionInt >= [2, 6, 39]:
                self.result  += self.tr("PREEMPT_RT")

        else:
            if versionInt >= [2, 6, 11]:
                #Linux kernel versions 2.6.11 and up can be patched for PREEMPT_RT and
                #versions 2.6.13 and up can be configured for CONFIG_PREEMPT
                # sources
                # https://wiki.linuxfoundation.org/realtime/preempt_rt_versions
                # https://cateee.net/lkddb/web-lkddb/PREEMPT.html
                self.icon = self.ICON_WARN
                self.moreInfo = self.tr(
                    "RT may be available if compiling this version w/CONFIG_PREEMPT or patching this kernel w/CONFIG_PREEMPT_RT.")

                if "-" not in uname3:
                    if uname3.endswith("-pae"):
                        kernelType = uname3.split("-")[-2].lower()
                        self.result += kernelType.title() + self.tr(" Vanilla (PAE)")
                    else:
                        kernelType = uname3.split("-")[-1].lower()
                        self.result += kernelType.title() + self.tr(" Vanilla")
            else:
                self.icon = self.ICON_ERROR
                self.moreInfo = self.tr("No realtime options for this version of kernel.")

    def get_id(self)->str:
        return 'kernel'

    def tr(self, text):
        return QApplication.translate("CalesonSystemCheck_kernel", text)

calesonSystemChecks = list[CalesonSystemCheck]()

def initSystemChecks(linux=True):
    if linux:
        calesonSystemChecks.append(CalesonSystemCheck_kernel())
        calesonSystemChecks.append(CalesonSystemCheck_audioGroup())