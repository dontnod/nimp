# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
import socket
import random
import string
import time
import contextlib
import shutil

from utilities.build        import *
from utilities.deployment   import *

def write_gp4_patch(volume_id, content_id, passcode, storage_type):
    <?xml version="1.0" encoding="utf-8"?>
<psproject fmt="gp4" version="1000">
  <volume>
    <volume_type>pkg_ps4_patch</volume_type>
    <volume_id>LifeIsStrange</volume_id>
    <volume_ts>2015-02-04 15:48:00</volume_ts>
    <package content_id="UP0082-CUSA01442_00-LIFEISSTRANGE001" passcode="LOLOLOLOLOLOLOLOLOLOLOLOLOL" storage_type="digital25" app_type="upgradable" app_path="" patch_type="ref_a"/>
    <chunk_info chunk_count="2" scenario_count="1">
      <chunks supported_languages="">
        <chunk id="0" layer_no="0" label="" />
        <chunk id="1" layer_no="0" label="" />
      </chunks>
      <scenarios default_id="0">
        <scenario id="0" type="sp" initial_chunk_count="1" label="Scenario #0">0-1</scenario>
      </scenarios>
    </chunk_info>
  </volume>
  <files img_no="0">
    <file targ_path="sce_sys/param.sfo" orig_path="Other\param_SCEA.sfo" />
	<file targ_path="sce_sys/shareparam.json" orig_path="Other\shareparam.json" />
    <file targ_path="sce_sys/changeinfo/changeinfo.xml" orig_path="Other\changeinfo.xml" />
	<file targ_path="sce_sys/changeinfo/changeinfo_02.xml" orig_path="Other\changeinfo_02.xml" />
    <file targ_path="eboot.bin" orig_path="Binaries\ExampleGame-ORBIS-Test.elf" pfs_compression="enable" />
	<file targ_path="/EXAMPLEGAME/PS4FINALTOC.TXT" orig_path="Other\PS4FINALTOC.txt" />
	<file targ_path="/EXAMPLEGAME/PS4FINALTOC_FRA.TXT" orig_path="Other\PS4FINALTOC_FRA.txt" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/EXAMPLEGAME_LOC_INT.XXX" orig_path="CookedOrbisFinal\EXAMPLEGAME_LOC_INT.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/GFXUI.XXX" orig_path="CookedOrbisFinal\GFXUI.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/GP_JOURNAL_E1_SF.XXX" orig_path="CookedOrbisFinal\GP_JOURNAL_E1_SF.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/ONLINESUBSYSTEMNP.XXX" orig_path="CookedOrbisFinal\ONLINESUBSYSTEMNP.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/SN_FONT_EN_SF.XXX" orig_path="CookedOrbisFinal\SN_FONT_EN_SF.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/SN_OUTGAMESENSENMENU_SF.XXX" orig_path="CookedOrbisFinal\SN_OUTGAMESENSENMENU_SF.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/SN_SENSENMENU_SF.XXX" orig_path="CookedOrbisFinal\SN_SENSENMENU_SF.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/STARTUP.XXX" orig_path="CookedOrbisFinal\STARTUP.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/STARTUP_LOC_INT.XXX" orig_path="CookedOrbisFinal\STARTUP_LOC_INT.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/TX_E1_2A_SF.XXX" orig_path="CookedOrbisFinal\TX_E1_2A_SF.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/TX_E1_6A_SF.XXX" orig_path="CookedOrbisFinal\TX_E1_6A_SF.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/WHATIF_MENU_E1_GRCC.XXX" orig_path="CookedOrbisFinal\WHATIF_MENU_E1_GRCC.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/WHATIF_MENU_E2_GRCC.XXX" orig_path="CookedOrbisFinal\WHATIF_MENU_E2_GRCC.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/WHATIF_MENU_E3_GRCC.XXX" orig_path="CookedOrbisFinal\WHATIF_MENU_E3_GRCC.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/WHATIF_MENU_E4_GRCC.XXX" orig_path="CookedOrbisFinal\WHATIF_MENU_E4_GRCC.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/WHATIF_MENU_E5_GRCC.XXX" orig_path="CookedOrbisFinal\WHATIF_MENU_E5_GRCC.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/COALESCED_FRA.BIN" orig_path="CookedOrbisFinal\COALESCED_FRA.BIN" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/COALESCED_INT.BIN" orig_path="CookedOrbisFinal\COALESCED_INT.BIN" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/CORE.XXX" orig_path="CookedOrbisFinal\CORE.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_1A.XXX" orig_path="CookedOrbisFinal\E1_1A.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_1A_CLIFFFUTURE_LD.XXX" orig_path="CookedOrbisFinal\E1_1A_CLIFFFUTURE_LD.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_2A.XXX" orig_path="CookedOrbisFinal\E1_2A.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_2A_ARTCLASS_LD.XXX" orig_path="CookedOrbisFinal\E1_2A_ARTCLASS_LD.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_2A_CORRIDOR_LD.XXX" orig_path="CookedOrbisFinal\E1_2A_CORRIDOR_LD.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_2A_TOILETS_LD.XXX" orig_path="CookedOrbisFinal\E1_2A_TOILETS_LD.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_3A.XXX" orig_path="CookedOrbisFinal\E1_3A.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_3A_CAMPUSA_LD.XXX" orig_path="CookedOrbisFinal\E1_3A_CAMPUSA_LD.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_3A_CAMPUSA_LD2.XXX" orig_path="CookedOrbisFinal\E1_3A_CAMPUSA_LD2.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_3B.XXX" orig_path="CookedOrbisFinal\E1_3B.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_3B_CAMPUSB_LD.XXX" orig_path="CookedOrbisFinal\E1_3B_CAMPUSB_LD.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_3C.XXX" orig_path="CookedOrbisFinal\E1_3C.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_3C_BATHROOM_LD.XXX" orig_path="CookedOrbisFinal\E1_3C_BATHROOM_LD.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_3C_CORRIDOR_LD.XXX" orig_path="CookedOrbisFinal\E1_3C_CORRIDOR_LD.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_3C_DANAROOM_LD.XXX" orig_path="CookedOrbisFinal\E1_3C_DANAROOM_LD.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_3C_MAXROOM_LD.XXX" orig_path="CookedOrbisFinal\E1_3C_MAXROOM_LD.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_3C_VICROOM_LD.XXX" orig_path="CookedOrbisFinal\E1_3C_VICROOM_LD.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_3D.XXX" orig_path="CookedOrbisFinal\E1_3D.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_3D_CAMPUSPARK_LD.XXX" orig_path="CookedOrbisFinal\E1_3D_CAMPUSPARK_LD.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_4A.XXX" orig_path="CookedOrbisFinal\E1_4A.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_4A_CHLOECAR_LD.XXX" orig_path="CookedOrbisFinal\E1_4A_CHLOECAR_LD.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_4A_CHOUSEFRONT_LD.XXX" orig_path="CookedOrbisFinal\E1_4A_CHOUSEFRONT_LD.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_5A.XXX" orig_path="CookedOrbisFinal\E1_5A.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_5A_BATHROOM_LD.XXX" orig_path="CookedOrbisFinal\E1_5A_BATHROOM_LD.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_5A_CHLOEROOM_LD.XXX" orig_path="CookedOrbisFinal\E1_5A_CHLOEROOM_LD.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_5A_CORRIDOR_LD.XXX" orig_path="CookedOrbisFinal\E1_5A_CORRIDOR_LD.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_5A_PARENTSROOM_LD.XXX" orig_path="CookedOrbisFinal\E1_5A_PARENTSROOM_LD.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_5B.XXX" orig_path="CookedOrbisFinal\E1_5B.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_5B_GARAGE_LD.XXX" orig_path="CookedOrbisFinal\E1_5B_GARAGE_LD.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_5B_GARDEN_LD.XXX" orig_path="CookedOrbisFinal\E1_5B_GARDEN_LD.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_5B_LIVINGROOM_LD.XXX" orig_path="CookedOrbisFinal\E1_5B_LIVINGROOM_LD.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_6A.XXX" orig_path="CookedOrbisFinal\E1_6A.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_6A_CLIFFNOW_LD.XXX" orig_path="CookedOrbisFinal\E1_6A_CLIFFNOW_LD.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_6B.XXX" orig_path="CookedOrbisFinal\E1_6B.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/E1_6B_CLIFFFUTURE_LD.XXX" orig_path="CookedOrbisFinal\E1_6B_CLIFFFUTURE_LD.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/ENGINE.XXX" orig_path="CookedOrbisFinal\ENGINE.XXX" pfs_compression="enable" />
    <file targ_path="EXAMPLEGAME/COOKEDORBISFINAL/EXAMPLEGAME.XXX" orig_path="CookedOrbisFinal\EXAMPLEGAME.XXX" pfs_compression="enable" />
	<file targ_path="EXAMPLEGAME/WWISEAUDIO/PS4/Init.bnk" orig_path="WwiseAudio\PS4\Init.bnk" pfs_compression="enable" />
  </files>
  <rootdir>
    <dir targ_name="sce_sys">
      <dir targ_name="changeinfo" />
    </dir>
  </rootdir>
</psproject>