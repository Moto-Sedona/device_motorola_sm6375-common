#!/usr/bin/env -S PYTHONPATH=../../../tools/extract-utils python3
#
# SPDX-FileCopyrightText: The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#

import os

from extract_utils.fixups_blob import (
    blob_fixup,
    blob_fixups_user_type,
)
from extract_utils.fixups_lib import (
    lib_fixups,
    lib_fixups_user_type,
)
from extract_utils.main import (
    ExtractUtils,
    ExtractUtilsModule,
)

namespace_imports = [
    'hardware/qcom-caf/sm6375-6.1',
    'device/motorola/sm6375-common',
    'hardware/qcom-caf/wlan',
    'hardware/motorola',
    'vendor/qcom/opensource/commonsys/display',
    'vendor/qcom/opensource/commonsys-intf/display',
    'vendor/qcom/opensource/dataservices',
]


def lib_fixup_vendor_suffix(lib: str, partition: str, *args, **kwargs):
    return f'{lib}_{partition}' if partition == 'vendor' else None


lib_fixups: lib_fixups_user_type = {
    **lib_fixups,
    (
        'com.qualcomm.qti.dpm.api@1.0',
        'vendor.qti.diaghal@1.0',
        'vendor.qti.hardware.wifidisplaysession@1.0',
        'vendor.qti.ImsRtpService-V1-ndk',
        'vendor.qti.imsrtpservice@3.0',
        'vendor.qti.imsrtpservice@3.1',
    ): lib_fixup_vendor_suffix,
}


blob_fixups: blob_fixups_user_type = {
    # Keep the generated vendor incremental version instead of rewriting it.
    'vendor/bin/init.oem.hw.sh': blob_fixup()
        .regex_replace(r'(?ms)^set_ro_vendor_incremental\(\)\n\{\n.*?^\}\n\n', '')
        .regex_replace(r'(?m)^set_ro_vendor_incremental &\n\n', ''),
    # The stock sensor HAL keeps the stock transport and protobuf libraries;
    # the malmo sensor services use their own libssc and libsnsapi.
    'vendor/lib64/sensors.ssc.so': blob_fixup()
        .replace_needed('libsnsapi.so', 'libsnsapi-stock.so')
        .replace_needed('libssc.so', 'libssc-stock.so')
        .add_needed('libcompiler_rt.so'),
    'vendor/lib64/libssc-stock.so': blob_fixup()
        .fix_soname()
        .replace_needed('libsnsapi.so', 'libsnsapi-stock.so'),
    'vendor/lib64/libsnsapi-stock.so': blob_fixup()
        .fix_soname(),
    # SoftDev's unused installd cpuset scan requires forbidden cross-process access.
    'vendor/bin/thermal-engine-v2': blob_fixup()
        .sig_replace(
            '00 ff ff b0 00 d8 09 91 b3 39 00 94 88 2e 00 d0 00 61 05 b9 20 02 f8 37 a0 18 00 d0 00 20 29 91 a4 f4 ff 97 a0 03 00 34',
            '00 ff ff b0 00 d8 09 91 00 00 80 12 88 2e 00 d0 00 61 05 b9 20 02 f8 37 a0 18 00 d0 00 20 29 91 a4 f4 ff 97 a0 03 00 34'),
    'vendor/etc/media_profiles_blair.xml': blob_fixup()
        .regex_replace(r'\s+maxHFR(?:FrameWidth|FrameHeight|Mode)="[^"]*"', '')
        .regex_replace(r'\s*<(?:VideoEditorCap|ExportVideoProfile)\b[^>]*/>', ''),
    'system_ext/lib64/libwfdmmsrc_system.so': blob_fixup()
        .add_needed('libaudiobase.so')
        .add_needed('libgui_shim.so'),
    'system_ext/lib64/libwfdservice.so': blob_fixup()
        .replace_needed('android.media.audio.common.types-V4-cpp.so', 'android.media.audio.common.types-V5-cpp.so')
        .add_needed('libaudiobase.so'),
    'system_ext/lib64/libwfdnative.so': blob_fixup()
        .add_needed('libinput_shim.so'),
    ('vendor/lib64/libdpps.so', 'vendor/lib64/libsnapdragoncolor-manager.so'): blob_fixup()
        .replace_needed('libtinyxml2.so', 'libtinyxml2-v34.so'),
    ('vendor/bin/qcc-vendor', 'vendor/bin/xtra-daemon', 'vendor/lib64/libqcc_sdk.so'): blob_fixup()
        .add_needed('libbinder_shim.so'),
    'vendor/lib64/libqcodec2_core.so': blob_fixup()
        .add_needed('libcodec2_shim.so'),
    'vendor/etc/seccomp_policy/qcrilnr@2.0.policy': blob_fixup()
        .add_line_if_missing('getppid: 1')
        .add_line_if_missing('uname: 1'),
    'vendor/lib64/libsensorndkbridge.so': blob_fixup()
        .replace_needed('android.hardware.sensors-V2-ndk.so', 'android.hardware.sensors-V3-ndk.so'),
    'system_ext/etc/permissions/moto-telephony.xml': blob_fixup()
        .regex_replace('/system/', '/system_ext/'),
}  # fmt: skip


module = ExtractUtilsModule(
    'sm6375-common',
    'motorola',
    blob_fixups=blob_fixups,
    lib_fixups=lib_fixups,
    namespace_imports=namespace_imports,
    add_generated_carriersettings=False,
    skip_main_proprietary_file=True,
)

source = os.environ.get('SM6375_BLOB_SOURCE', 'all')
if source not in ('all', 'stock', 'malmo'):
    raise ValueError('SM6375_BLOB_SOURCE must be all, stock, or malmo')
if source in ('all', 'stock'):
    module.add_proprietary_file('proprietary-files.txt')
if source in ('all', 'malmo'):
    module.add_proprietary_file('proprietary-files-malmo.txt')

if __name__ == '__main__':
    ExtractUtils.device(module).run()
