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
