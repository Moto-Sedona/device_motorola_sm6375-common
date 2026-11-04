#! /vendor/bin/sh
#=============================================================================
# Copyright (c) 2019-2022 Qualcomm Technologies, Inc.
# All Rights Reserved.
# Confidential and Proprietary - Qualcomm Technologies, Inc.
#=============================================================================

VENDOR_DIR="/vendor/lib/modules"
VENDOR_DLKM_DIR="/vendor_dlkm/lib/modules"
THREADS=8

MODPROBE="/vendor/bin/modprobe"

# vendor modules partition could be /vendor/lib/modules or /vendor_dlkm/lib/modules
POSSIBLE_DIRS="${VENDOR_DLKM_DIR} ${VENDOR_DIR}"
audio_arch=`getprop ro.boot.audio`
boot_device=`getprop ro.boot.device`

for dir in ${POSSIBLE_DIRS} ;
do
	if [ ! -e ${dir}/modules.load ]; then
		continue
	fi

	if [ "$audio_arch" == "audioreach" ]; then
		if [ -e ${dir}/modules.audio.ar.blocklist ]; then
			audio_blocklist_expr="$(sed -n -e 's/blocklist \(.*\)/\1/p' ${dir}/modules.audio.ar.blocklist | sed -e 's/^/-e /')"
		else
			audio_blocklist_expr="-e %"
		fi
	else
		if [ -e ${dir}/modules.audio.legacy.blocklist ]; then
			audio_blocklist_expr="$(sed -n -e 's/blocklist \(.*\)/\1/p' ${dir}/modules.audio.legacy.blocklist | sed -e 's/^/-e /')"
		else
			audio_blocklist_expr="-e %"
		fi
	fi

	if [ -e ${dir}/modules.blocklist ]; then
		blocklist_expr="$(sed -n -e 's/blocklist \(.*\)/\1/p' ${dir}/modules.blocklist | sed -e 's/^/-e /')"
	else
		# Use pattern that won't be found in modules list so that all modules pass through grep below
		blocklist_expr="-e %"
	fi

	if [ -e ${dir}/modules.blocklist.${boot_device} ]; then
		device_blocklist_expr="$(sed -n -e 's/blocklist \(.*\)/\1/p' ${dir}/modules.blocklist.${boot_device} | sed -e 's/^/-e /')"
	else
		# Use pattern that won't be found in modules list so that all modules pass through grep below
		device_blocklist_expr="-e %"
	fi
	# Filter out modules in blocklist - we would see unnecessary errors otherwise
	load_modules=$(sed = ${dir}/modules.load | sed 'N;s/\n/\t/' | sort -uk2 | sort -nk1 | cut -f2- | grep -w -v ${blocklist_expr} | grep -w -v ${audio_blocklist_expr} | grep -w -v ${device_blocklist_expr})
	first_module=$(echo ${load_modules} | cut -d " " -f1)
	other_modules=$(echo ${load_modules} | cut -d " " -f2-)
	if ! ${MODPROBE} -b -s -d ${dir} -a ${first_module} > /dev/null ; then
		continue
	fi

	module_count=$(echo ${other_modules} | wc -w)
	module_avg=$((${module_count}/${THREADS}))
	module_rem=$((${module_count}%${THREADS}))

	# less modules , just start modprobe
	if [ ${module_count} -le $((${THREADS}*2)) ]; then
		for module in ${other_modules}; do
			( ${MODPROBE} -b -d ${dir} -a ${module} > /dev/null ) &
		done

		wait

		setprop vendor.all.modules.ready 1
		echo "Total ${module_count} modules Loaded"
		exit 0
	fi
	# more modules and load by groups
	load_task=0
	load_start=1
	while [[ ${load_task} -lt ${THREADS} ]];
	do
		load_len=$((${module_avg}-1))
		if [ ${module_rem} -gt 0 ];
		then
			module_rem=$((${module_rem}-1))
			load_len=$((${load_len}+1))
		fi
		if [ ${load_task} ==  $((${THREADS}-1)) ];
		then
			slice_modules=$(echo ${other_modules} | cut -d " " -f${load_start}-)
		else
			slice_modules=$(echo ${other_modules} | cut -d " " -f${load_start}-$((${load_start}+${load_len})))
		fi
		# TODO: fixup args list too long
		( ${MODPROBE} -b -d ${dir} -a ${slice_modules} > /dev/null ) &
		load_start=$((${load_start}+${load_len}+1))
		load_task=$((${load_task}+1))
	done

	wait

	setprop vendor.all.modules.ready 1
	echo "Total ${module_count} modules Loaded"
	exit 0
done

exit 1
