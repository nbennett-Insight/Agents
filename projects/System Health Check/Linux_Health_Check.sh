#!/bin/bash
#
# Veritas - Linux Health Check - Version 2.0
#
# Start: Initialization
# Initialization: Environment: pwd
presentDir=$(pwd)
if [ ${?} -ne 0 ]; then
    echo -e "Error: Failed to get present working directory ('pwd'). Exiting."
    exit 9
fi
presentDirCheck=$(echo -e "${presentDir}" | grep -c " ")
if [ ${presentDirCheck} -ne 0 ]; then
    echo -e "Error: Present working directory contains 'space' in path. Please retry from another directory. Exiting."
    exit 9
fi
# Initialization: Environment: Check 'timeout'
timeout 1 echo
if [ ${?} -eq 0 ]; then
    tmt=1
else
    timeoutPath=$(ls -1 /bin/timeout 2>/dev/null)
    if [ ${?} -eq 0 ]; then
        alias timeout=${timeoutPath}
        tmt=1
    else
        timeoutPath=$(ls -1 /usr/bin/timeout 2>/dev/null)
        if [ ${?} -eq 0 ]; then
            alias timeout=${timeoutPath}
            tmt=1
        fi
    fi
fi
if [ -z ${tmt} ]; then echo -e "\nError: Cannot find 'timeout' binary in '\$PATH', '/bin/timeout' or '/usr/bin/timeout'. Exiting.\n"; exit 9; fi
# Initialization: Environment: Variables
initVariables() {
    bin=${0}
    lhcVersion=2.0
    p0=$(printf '=%.0s' {0..130}); p1=$(printf '=%.0s' {0..100}); p2=$(printf '=%.0s' {0..76}); p3=$(printf '=%.0s' {0..46}); p4=$(printf '=%.0s' {0..28}); p5=$(printf '=%.0s' {0..22});
    sourceDir=$(dirname "${0}")
    sourceDate=$(date +%F)
    sourceTime=$(date +%s)
    sourceTimeLong=$(date +%Hh_%Mm_%Ss)
    hostnameIP=$(timeout -s 9 5 /bin/hostname -i 2>/dev/null)
    hostnameFull=$(timeout -s 9 5 /bin/hostname -f 2>/dev/null)
    hostnameShort=$(timeout -s 9 5 /bin/hostname -s 2>/dev/null)
    hostnameShortForce=$(echo ${hostnameShort} | awk -F. '{print $1}')
    if [ -z ${hostnameShortForce} ]; then
        echo -e "Error: Exiting. Unable to determine local hostname: /bin/hostname -s"
        exit 9
    fi
    filePrefix=${sourceDate}
    fileSuffix=${hostnameShortForce}-${sourceTime}-${sourceTimeLong}
}
initVariables
# Initialization: Environment: Process Log
runLog() {
    export psLog=${presentDir}/${filePrefix}-Vx-LHC-Process_Log-${fileSuffix}.log
    . ${0} log 2>&1 | tee ${psLog}; exit
}
runVerbose() {
    export psLog=${presentDir}/${filePrefix}-Vx-LHC-Process_Log-${fileSuffix}.log
    set -x; . ${0} 2>&1 | tee ${psLog}; exit
}
# Initialization: Environment: Execution
if [[ -z ${1} ]]; then runLog; elif [[ -n ${1} && ${1} == verbose ]]; then runVerbose; fi
if [[ -n ${1} && ${1} == @(log|verbose) ]]; then menuPersist=1;
elif [[ -n ${1} && ${1} != @(log|verbose) ]]; then menuPersist=0; mainOpt=${1}; fi
# Initialization: Environment: Platform
initPlatform() {
    optsMain="performance"
    # NetBackup
    if [ -f /usr/openv/netbackup/version ]; then nbuHost=1; optsMain+=" netbackup"; else nbuHost=0; fi
    # MSDP
    if [ -f /etc/pdregistry.cfg ]; then msdpHost=1; optsMain+=" msdp"; else msdpHost=0; fi
    # Linux
    if [ -d /proc ]; then genericHost=1; optsMain+=" os memory storage network"; else genericHost=0; fi
    # Container
    cgroupCount=$(timeout -s 9 10 grep -c "docker\|libpod" /proc/1/cgroup)
    if [[ -f /.dockerenv || ${cgroupCount} -ne 0 ]]; then appInst=1; else appInst=0; fi
    # NB App
    if [[ -f /etc/nbapp-release && ${appInst} -eq 0 ]]; then nbApp=1; else nbApp=0; fi
    # Flex App
    if [[ -f /etc/flex-release && ${appInst} -eq 0 ]]; then flexApp=1; else flexApp=0; fi
    # NBFS App
    if [[ -f /etc/nbfs-app-release && ${appInst} -eq 0 ]]; then nbfsApp=1; else nbfsApp=0; fi
    # Access App
    if [[ -f /etc/ltr-app-release && ${appInst} -eq 0 ]]; then accessApp=1; else accessApp=0; fi
    # Generic App
    if [[ ${flexApp} -eq 1 || ${nbApp} -eq 1 || ${nbfsApp} -eq 1 || ${accessApp} -eq 1 ]]; then genericApp=1; optsMain+=" appliance"; else genericApp=0; fi
    optsMain+=" logs trace compress quit"
}
initPlatform
# Initialization: Function: Runtime Log
epochTimeInt=${sourceTime}
logTime() {
    epochTimeDelta=$(echo -e "$(($(date +%s) - epochTimeInt))")
    epochTimeInt=$(date +%s)
    epochTimeStr=$(date -d @${epochTimeInt} +"%Y-%m-%d, %H:%M:%S")
    epochTimeTotal=$(echo -e "$((epochTimeInt - sourceTime))")
    echo -e "${epochTimeInt}, ${epochTimeStr}, ${epochTimeTotal}, ${epochTimeDelta}, ${FUNCNAME[1]}" 1>>${outputDir}/LHC-Log.csv
}
# End: Initialization
# Start: Operations
# Operation: Settings - Output Directory
setOutput() {
    echo -e "${p3}\nOutput Directory\n${p3}"
    pwdSpace=$(timeout -s 9 10 df $(pwd) 2>/dev/null | tail -n1 | awk '{print $(NF-2)}')
    if [[ -n ${pwdSpace} && ${pwdSpace} -gt 10000000 ]]; then
        echo -e "\nCreate output folder in the present working directory? (y/n)\n\n\t Current Directory: $(pwd)\n\nEnter 'y' or 'n'...\n"
        read pathCheck
        if [ -z ${pathCheck} ]; then
            echo -e "Please enter 'y' or 'n'...\n"
            read pathCheck
            if [ -z ${pathCheck} ]; then
                echo -e "Error: Invalid response. Exiting.\n"
                exit 9
            fi
        fi
        if [ ${pathCheck} = 'y' ]; then
            outputPath=$(pwd)
            echo -e "\nOutput directory confirmed.\n"
        fi
    fi
    if [ -z ${outputPath} ]; then
        echo -e "${p5}\nStorage Volumes\n${p5}"
        outSize=$(timeout -s 9 10 df -hl 2>/dev/null)
        exitStatus=${?}
        outSizeCount=$(echo -e "${outSize}" | wc -l)
        if [ ${outSizeCount} -gt 1 ]; then
            outSizeSort=$(echo -e "${outSize}" | awk '{print $4, $6}' | sort -h | grep -v "docker\|vpfs\|msdp\|vx\|baseboard\|cgroup\|run\|dev" | tail -n7)
            echo -e "\tSize Path\n${outSizeSort}\n" | column -t | sed 's/^/\t/g'
        fi
        if [ ${exitStatus} -ne 0 ]; then
            echo -e "Error: The 'df -h' command returned a non-zero exit status."
        fi
        echo -e "\n${p5}\nSelect Path\n${p5}"
        echo -e "\nEnter the path for the output directory...\n"
        read outputPath
        if [ -z ${outputPath} ]; then
            echo -e "Error: Invalid response.\n"
            echo -e "\nEnter the path for the output directory...\n"
            read outputPath
            if [ -z ${outputPath} ]; then
                echo -e "Error: Invalid response. Exiting.\n"
                exit 9
            fi
        fi
        pathSpace=$(timeout -s 9 10 df ${outputPath} 2>/dev/null | tail -n1 | awk '{print $(NF-2)}')
        if [[ -n ${pathSpace} && ${pathSpace} -lt 10000000 ]]; then
            echo -e "\n\nError: The path specified has less than 10 GB of free space. Exiting.\n"
            exit 9
        else
            echo -e "\n\nOutput directory confirmed.\n\n"
        fi
    fi
    # Initialization - Output - Path - Validation
    outputPathCheck1=$(echo ${outputPath} | grep "[[:space:]]" | wc -l)
    outputPathCheck2=$(echo ${outputPath} | grep -v "^/" | wc -l)
    if [ ${outputPathCheck1} -gt 0 ]; then
        echo -e "\033[0;31m${p2}\nError - Invalid Option\n${p2}"
        echo -e "Error: Invalid output path: The path specifiedhas a 'space' in the name.\033[0m\n"
        unset outputPath
        mainMenu
    fi
    if [[ ${outputPathCheck2} -gt 0 ]]; then
        echo -e "\033[0;31m${p2}\nError - Invalid Option\n${p2}"
        echo -e "Error: Invalid output path: The path specified does not begin with a '/' forward slash.\033[0m\n"
        unset outputPath
        mainMenu
    fi
    if [[ ! -d ${outputPath} ]]; then
        echo -e "\033[0;31m${p2}\nError - Invalid Option\n${p2}"
        echo -e "\n\n\e[1mError: Invalid output path: The path specified does not exist.\033[0m\n"
        unset outputPath
        mainMenu
    else
        export outputDir=${outputPath}/${filePrefix}-LHC-Linux_Health_Check-${fileSuffix}
        export reportDir=${outputDir}/Reports
        mkdir -p ${outputDir} ${reportDir}
        if [[ ${?} -eq 0 && -d ${outputDir} ]]; then
            echo -e "Output directory created.\n\n"
        else
            echo -e "\033[0;31m${p2}\nError - Invalid Option\n${p2}"
            echo -e "\n\n\e[1mError: Failed to create output directory, please retry using a different output path.\033[0m\n"
            unset outputPath
            mainMenu
        fi
        outputFile=${outputDir}/
        reportFile=${reportDir}/
        lhcChecksum=$(echo ${lhcVersion} | sha256sum | awk '{print $1}')
        echo -e "LHC_Version=${lhcVersion}\nLHC_Checksum=${lhcChecksum}" 1>${outputDir}/LHC-Version.cfg
        echo -e "NBU_Host: ${nbuHost}\nMSDP_Host: ${msdpHost}\nAccess_Host: ${accessApp}\nFlex_Host: ${flexApp}\nNBA_Host: ${nbApp}\nNBFS_Host: ${nbfsApp}\nGeneric_App: ${genericApp}\nGeneric_Host: ${genericHost}\nApp_Instance: ${appInst}" | column -t 1>${outputDir}/LHC-Platform.txt
        echo -e "NBU_Host=${nbuHost}\nMSDP_Host=${msdpHost}\nAccess_Host=${accessApp}\nFlex_Host=${flexApp}\nNBA_Host=${nbApp}\nNBFS_Host=${nbfsApp}\nGeneric_App=${genericApp}\nGeneric_Host=${genericHost}\nApp_Instance=${appInst}" 1>${outputDir}/LHC-Platform.cfg
    fi
	logTime
}
# Operation: Settings - Run Complete
runComplete() {
    if [ ${genericHost} -eq 1 ]; then
        osOverviewReport
        osConfigurationReport
        osMessagesReport
        memory
        network
        storage
        performanceSnapshotReport
    fi
    if [ ${appInst} -eq 0 ]; then
        performanceHistoricalReport
    fi
    if [ ${nbuHost} -eq 1 ]; then
        nbuEnvironmentReport
        nbuConfigurationReport
        nbuSLPReport
    fi
    if [ ${msdpHost} -eq 1 ]; then
        msdpOverviewReport
        msdpSessionReport
        msdpDedupeReport
        msdpCloudReport
    fi
    if [ ${genericApp} -eq 1 ]; then
        appliance
    fi
    compress
    quit
}
# Operation: Settings - Report Options
setOptions() {
    echo -e "${p2}\nReport Options\n${p2}"
    # Setting - Logs - MSDP - Overview
    msdpReport=n
    if [ ${msdpHost} -eq 1 ]; then
        echo -e "${p3}\nMSDP - Report\n${p3}"
        echo -e "\nDo you want to execute the MSDP reports? (y/n)\n"; read msdpReport; echo -e "\n"
        if [ ${msdpReport} == y ]; then
            # Setting - Logs - MSDP - Client Session Logs
            if [ ${msdpHost} -eq 1 ]; then
                echo -e "${p3}\nMSDP - Client Session Logs\n${p3}"
                echo -e "\nDo you want to execute the MSDP Client Session Log Report? (y/n)\n"; read sessionLogs; echo -e "\n"
            fi
            # Setting - Logs - MSDP - Historical Dedupe Report
            if [ ${msdpHost} -eq 1 ]; then
                echo -e "${p3}\nMSDP - Historical Dedupe Report\n${p3}"
                echo -e "\nDo you want to execute the MSDP Historical Dedupe Report? (y/n)\n"; read dedupeRates; echo -e "\n"
            fi
            # Setting - Logs - MSDP - Cloud - OCSD Report 
            if [ ${msdpHost} -eq 1 ]; then
                echo -e "${p3}\nMSDP - Cloud Storage - OCSD Report\n${p3}"
                echo -e "\nDo you want to execute the MSDP Cloud Storage Report (OCSD)? (y/n)\n"; read ocsdReport; echo -e "\n"
            fi
        else
            dedupeRates=n
            sessionLogs=n
            ocsdReport=n
        fi
    fi
    # Settings - Software - NetBackup
    nbuReport=n
    if [[ ${nbuHost} -eq 1 ]]; then
        echo -e "${p3}\nNetBackup - System State\n${p3}"
        echo -e "\nDo you want to execute the NetBackup Reports? (y/n)\n"; read nbuReport; echo -e "\n"
    fi
    # Settings - Appliance - NetBackup
    appReport=n
    if [[ ${appInst} -eq 0 ]]; then
        echo -e "${p3}\nAppliance - System State\n${p3}"
        echo -e "\nDo you want to execute the Appliance Report? (y/n)\n"; read appReport; echo -e "\n"
    fi
    # Setting - LHC - OS
    osReport=n
    if [ ${genericHost} -eq 1 ]; then
        echo -e "${p3}\nLHC - Report - OS\n${p3}"
        echo -e "\nDo you want to execute the OS/Operating System Report? (y/n)\n"; read osReport; echo -e "\n"
    fi
    # Setting - LHC - Memory
    memoryReport=n
    if [ ${genericHost} -eq 1 ]; then
        echo -e "${p3}\nLHC - Report - Memory\n${p3}"
        echo -e "\nDo you want to execute the Memory Report? (y/n)\n"; read memoryReport; echo -e "\n"
    fi
    # Setting - LHC - Network
    networkReport=n
    if [ ${genericHost} -eq 1 ]; then
        echo -e "${p3}\nLHC - Report - Network\n${p3}"
        echo -e "\nDo you want to execute the Network Report? (y/n)\n"; read networkReport; echo -e "\n"
    fi
    # Setting - LHC - Storage
    storageReport=n
    if [ ${genericHost} -eq 1 ]; then
        echo -e "${p3}\nLHC - Report - Storage\n${p3}"
        echo -e "\nDo you want to execute the Storage Report? (y/n)\n"; read storageReport; echo -e "\n"
    fi
    # Setting - LHC - Performance - Historical
    histPerformance=n
    if [ ${genericHost} -eq 1 ]; then
        echo -e "${p3}\nLHC - Performance - Historical\n${p3}"
        echo -e "\nDo you want to execute the Historical Performance Report (SA Report)? (y/n)\n"; read histPerformance; echo -e "\n"
    fi
    # Setting - LHC - Performance - Snapshot
    snapPerformance=n
    if [ ${genericHost} -eq 1 ]; then
        echo -e "${p3}\nLHC - Performance - Snapshot\n${p3}"
        echo -e "\nDo you want to execute the Snapshot Performance Report? (y/n)\n"; read snapPerformance; echo -e "\n"
    fi
	logTime
}
# Operation: Settings - Report Options - Execution
runOptions() {
    if [[ -n ${osReport} && ${osReport} == y ]]; then
        osOverviewReport
        osConfigurationReport
        osMessagesReport
    fi
    if [[ -n ${msdpReport} && ${msdpReport} == y ]]; then
        msdpOverviewReport
    fi
    if [[ -n ${sessionLogs} && ${sessionLogs} == y ]]; then
        msdpSessionReport
    fi
    if [[ -n ${dedupeRates} && ${dedupeRates} == y ]]; then
        msdpDedupeReport
    fi
    if [[ -n ${ocsdReport} && ${ocsdReport} == y ]]; then
        msdpCloudReport
    fi
    if [[ -n ${nbuReport} && ${nbuReport} == y ]]; then
        nbuEnvironmentReport
        nbuConfigurationReport
    fi
    if [[ -n ${appReport} && ${appReport} == y ]]; then
        appliance
    fi
    if [[ -n ${memoryReport} && ${memoryReport} == y ]]; then
        memory
    fi
    if [[ -n ${networkReport} && ${networkReport} == y ]]; then
        network
    fi
    if [[ -n ${storageReport} && ${storageReport} == y ]]; then
        storage
    fi
    if [[ -n ${histPerformance} && ${histPerformance} == y ]]; then
        performanceHistoricalReport
    fi
    if [[ -n ${snapPerformance} && ${snapPerformance} == y ]]; then
        performanceSnapshotReport
    fi
    compress
    quit
}
# Operation: Report - OS - Initialization
osInit() {
    if [ -z ${osInitComplete} ]; then
        # Output
        osDir=${outputDir}/OS
        osEtc=${osDir}/etc
        osProc=${osDir}/proc
        osSys=${osDir}/sys
        osDirs="${osDir} ${osEtc} ${osProc} ${osSys}"
        mkdir -p ${osDirs}
        if [ ${?} -ne 0 ]; then echo -e "Error: Exiting. Failed to create folder(s): ${osDirs}."; escape; fi
        osFile=${osDir}
        osReport=${osDir}/OS
        osInitComplete=1
    fi
	logTime
}
# Operation: Report - OS - Overview
osOverviewReport() {
    if [ -z ${osInitComplete} ]; then osInit; fi
    if [[ -n ${osOverviewReportComplete} || ${osOverviewReportComplete} -eq 1 ]]; then
        echo -e "\033[0;31m\n${p2}\nError - Duplicate Report\n${p2}\n"
        echo -e "Error: OS Overview Report has already been executed.\033[0m\n";
    elif [[ -z ${osOverviewReportComplete} || ${osOverviewReportComplete} -eq 0 ]]; then
        echo -e "${p1}\nLHC - Processing - Report: OS\n${p1}"
        echo -e "${p2}\nPlatform\n${p2}"
        grep "1" ${outputDir}/LHC-Platform.txt 
        echo -e ""
        # Release
        echo -e "\n${p2}\nRelease Files\n${p2}"
        releaseFiles="/etc/nbfs-app-release /etc/flex-release /etc/ltr-app-release /etc/nbapp-release /etc/msdp-release /etc/pdos-release /etc/vxos-release /etc/os-release /etc/redhat-release"
        ls -l ${releaseFiles} 1>${osEtc}/release.txt 2>&1
        for releaseFile in ${releaseFiles}; do
            timeout -s 9 10 cp ${releaseFile} ${osEtc} 2>/dev/null
            if [ ${?} -eq 0 ]; then
                fileName=$(echo ${releaseFile} | awk -F'/' '{print $NF}')
                echo -e "${p3}\nRelease: ${releaseFile}\n${p3}"
                cat ${osEtc}/${fileName}
                echo -e ""
            fi
        done
        echo -e "\n${p2}\nSystem Information\n${p2}";
        # Hostname
        echo -e "${p3}\nHostname\n${p3}"
        echo -e "Local IP Address: ${hostnameIP}\nLocal Short Hostname: ${hostnameShort}\nLocal Full Hostname: ${hostnameFull}" | tee ${osFile}/hostname.txt
        echo -e "Local IP Address: ${hostnameIP}" 1>${osFile}/hostname-ip
        echo -e "Local Short Hostname: ${hostnameShort}" 1>${osFile}/hostname-short
        echo -e "Local Full Hostname: ${hostnameFull}" 1>${osFile}/hostname-full
        # NBU Version
        if [ ${nbuHost} -eq 1 ]; then
            echo -e "\n${p3}\nNetBackup\n${p3}"
            timeout -s 9 10 cp /usr/openv/netbackup/version ${osFile}/nbu-version
            if [ ${?} -eq 0 ]; then
                nbuVersion=$(timeout -s 9 5 awk '/VERSION/{gsub("VERSION ",""); print $0}' ${osFile}/nbu-version)
                echo ${nbuVersion}
            else
                echo "Error: Failed to get NetBackup version."
            fi 1>${osFile}/nbu-version-release.txt
            nbuVersionTimestamp=$(timeout -s 9 5 stat -c "%y" /usr/openv/netbackup/version)
            if [ ${?} -eq 0 ]; then
                echo ${nbuVersionTimestamp} 
            else
                echo "Error: Failed to get NetBackup version timestamp."
            fi 1>${osFile}/nbu-version-release-timestamp.txt
            echo -e "NetBackup Version: ${nbuVersion}\nUpgrade Timestamp: ${nbuVersionTimestamp}" | tee ${osFile}/nbu_version.txt
        fi
        # BIOS
        if [[ -f /sbin/dmidecode && ${appInst} -eq 0 ]]; then
            echo -e "\n\n${p2}\nBIOS Information\n${p2}"
            serialNumber=$(timeout -s 9 5 /sbin/dmidecode -s system-serial-number)
            echo -e "Serial Number: ${serialNumber}"
            timeout -s 9 5 /sbin/dmidecode -t bios 1>${osFile}/bios 2>&1
            if [ ${?} -eq 0 ]; then
                timeout -s 9 5 grep ":" ${osFile}/bios | sed -e 's/\t//g' | tee ${osFile}/bios.txt
            fi
        fi
        # Kernel - /proc
        echo -e "\n\n${p2}\nKernel - Proc - Summary\n${p2}"
        # Hostname
        echo -e "${p3}\nKernel - Hostname\n${p3}"
        timeout -s 9 5 cp /proc/sys/kernel/hostname ${osProc}/hostname-kernel
        hostnameKernel=$(cat ${osProc}/hostname-kernel)
        echo -e "Local IP Address: ${hostnameIP}\nLocal Short Hostname: ${hostnameShort}\nLocal Full Hostname: ${hostnameFull}\nLocal Kernel Hostname: ${hostnameKernel}" | tee ${osFile}/hostname.txt
        echo -e "Local IP Address: ${hostnameIP}" 1>${osFile}/hostname-ip
        echo -e "Local Short Hostname: ${hostnameShort}" 1>${osFile}/hostname-short
        echo -e "Local Full Hostname: ${hostnameFull}" 1>${osFile}/hostname-full
        # System
        echo -e "\n${p3}\nKernel - CPU\n${p3}"
        timeout -s 9 5 cp /proc/cmdline ${osProc}/cmdline
        timeout -s 9 5 cp /proc/loadavg ${osProc}/loadavg
        timeout -s 9 5 cp /proc/uptime ${osProc}/uptime
        timeout -s 9 5 cp /proc/cpuinfo ${osProc}/cpuinfo
        if [ ${?} -ne 0 ]; then
            echo -e "Error: Failed reeading '/proc/cpuinfo'"
        else
            timeout -s 9 5 awk -F': ' '/model name/{print $2}' ${osProc}/cpuinfo 1>${osProc}/cpuinfo-cores
            timeout -s 9 5 uniq ${osProc}/cpuinfo-cores 1>${osProc}/cpuinfo-model-name
            timeout -s 9 5 uniq -c ${osProc}/cpuinfo-cores 1>${osProc}/cpuinfo-cores-count
            timeout -s 9 5 grep "cpu MHz" ${osProc}/cpuinfo 1>${osProc}/cpuinfo-MHz
            cpuModel=$(cat ${osProc}/cpuinfo-model-name)
            cpuCount=$(awk 'END{print NR}' ${osProc}/cpuinfo-cores | awk '{print $1}')
            echo -e "CPU_Model: ${cpuModel}\nCPU_Cores: ${cpuCount}" 1>${osProc}/cpuinfo-summary
            cat ${osProc}/cpuinfo-summary
        fi
        # Memory
        echo -e "\n${p3}\nKernel - Memory\n${p3}"
        timeout -s 9 5 cp /proc/meminfo ${osProc}/meminfo
        if [ ${?} -eq 0 ]; then
            timeout -s 9 9 grep "kB" ${osProc}/meminfo 1>${osProc}/meminfo-kb
            while read key value label; do
                calc=$(echo "scale=2; ${value} / 1024000" | bc -l 2>/dev/null);
                echo -e "${key} ${calc} gB" 1>>${osProc}/meminfo-gb
            done <${osProc}/meminfo-kb
            timeout -s 9 5 grep "Mem\|Committed_AS\|CommitLimit\|Swap\|Slab\|Huge\|Mapped\|Hardware" ${osProc}/meminfo-gb > ${osProc}/meminfo-gb-overview
            cat ${osProc}/meminfo-gb-overview
            timeout -s 9 5 grep "Mem\|Committed_AS" ${osProc}/meminfo-gb 1>${osProc}/meminfo-mem-used-gb
            timeout -s 9 5 grep "Mem\|Committed_AS" ${osProc}/meminfo-kb 1>${osProc}/meminfo-mem-used-kb
            timeout -s 9 5 grep "Committed_AS" ${osProc}/meminfo-gb 1>${osProc}/meminfo-mem-committed_as-gb
            timeout -s 9 5 grep "Committed_AS" ${osProc}/meminfo-kb 1>${osProc}/meminfo-mem-committed_as-kb
            timeout -s 9 5 grep "CommitLimit" ${osProc}/meminfo-gb 1>${osProc}/meminfo-mem-commitlimit-gb
            timeout -s 9 5 grep "CommitLimit" ${osProc}/meminfo-kb 1>${osProc}/meminfo-mem-commitlimit-kb
            timeout -s 9 5 grep "Swap" ${osProc}/meminfo-gb 1>${osProc}/meminfo-mem-swap-gb
            timeout -s 9 5 grep "Swap" ${osProc}/meminfo-kb 1>${osProc}/meminfo-mem-swap-kb
            timeout -s 9 5 grep "SwapCached" ${osProc}/meminfo-gb 1>${osProc}/meminfo-mem-swap-cached-gb
            timeout -s 9 5 grep "SwapCached" ${osProc}/meminfo-kb 1>${osProc}/meminfo-mem-swap-cached-kb
            timeout -s 9 5 grep "SwapTotal" ${osProc}/meminfo-gb 1>${osProc}/meminfo-mem-swap-total-gb
            timeout -s 9 5 grep "SwapTotal" ${osProc}/meminfo-kb 1>${osProc}/meminfo-mem-swap-total-kb
            timeout -s 9 5 grep "SwapFree" ${osProc}/meminfo 1>${osProc}/meminfo-mem-swap-free
            timeout -s 9 5 grep "SwapFree" ${osProc}/meminfo 1>${osProc}/meminfo-mem-swap-free
        fi
        # Kernel Settings
        echo -e "\n${p2}\nKernel - Memory - Settings\n${p2}"
        timeout -s 9 30 sysctl -a 1>${osFile}/Kernel-Settings.txt 2>&1
        if [ ${?} -eq 0 ]; then
            timeout -s 9 10 grep "vm.vfs_cache_pressure\|vm.extfrag_threshold\|kernel.numa_balancing\|fs.nr_open\|vm.max_map_count\|vm.swappiness\|vm.overcommit_memory\|vm.overcommit_ratio\|vm.nr_hugepages\|vm.zone_reclaim_mode\|vm.min_free_kbytes\|fs.inotify.max_user_watches" ${osFile}/Kernel-Settings.txt 1>${osFile}/Kernel-Settings-Memory.txt
            cat ${osFile}/Kernel-Settings-Memory.txt
        fi
        echo -e "\n\n${p2}\nKernel - Memory - THP: Transparent HugePage\n${p2}";
        thpFiles=$(timeout -s 9 10 find /sys/kernel/mm/transparent_hugepage/ -type f)
        if [ ${?} -eq 0 ]; then
            thpDir=${osSys}/kernel/mm/transparent_hugepage
            mkdir -p ${thpDir}
            for file in ${thpFiles}; do 
                echo -e "${p3}\n${file}\n${p3}"
                timeout -s 9 5 cp ${file} ${thpDir}
                timeout -s 9 5 cat ${file}
                echo -e ""
            done
            thpFilesDisplay="/sys/kernel/mm/transparent_hugepage/enabled /sys/kernel/mm/transparent_hugepage/defrag"
            for file in ${thpFilesDisplay}; do
                echo -e "${p3}\n${file}\n${p3}"
                cat ${file}
                echo -e ""
            done | tee -a ${osFile}/Kernel-THP.txt
        fi
        # Kernel Modules
        echo -e "\n${p2}\nKernel - Modules - Common\n${p2}"
        echo -e "${p3}\nModules\n${p3}"
        echo -e "Processing: Host - /proc/modules"
        timeout -s 9 10 cp /proc/modules ${osProc} 2>/dev/null
        echo -e "Processing: Host - /proc/version"
        timeout -s 9 10 cp /proc/version ${osProc} 2>/dev/null
        # lsmod
        echo -e "Processing: Host - /sbin/lsmod"
        timeout -s 9 5 /sbin/lsmod 1>${osFile}/lsmod 2>&1
        if [ ${?} -eq 0 ]; then
            echo -e "\n${p3}\nEDAC: Active\n${p3}"
            edacList=EDAC-lsmod.txt
            timeout -s 9 5 grep edac ${osFile}/lsmod 1>${osFile}/${edacList} 2>&1
            edacCount=$(awk '/./{c++} END {print c+0}' ${osFile}/${edacList})
            echo -e "File: ${edacList}\nCount: ${edacCount}"
            if [ ${edacCount} -eq 0 ]; then
                echo -e "List: None"
            else
                echo -e "List:"
                cat ${osFile}/${edacList} | column -t
            fi
        else
            echo -e "Error: Failed running '/sbin/lsmod'."
        fi
        # modprobe
        if [ -d /etc/modprobe.d/ ]; then
            osModprobe=${osEtc}/modprobe.d
            mkdir ${osModprobe}
            if [ ${?} -ne 0 ]; then escape; fi
            if [ -d ${osModprobe} ]; then
                osModprobeFiles=$(timeout -s 9 5 find /etc/modprobe.d/ -type f)
                ls -l ${osModprobeFiles} 1>${osFile}/modprobe-list 2>&1
                for fileName in ${osModprobeFiles}; do
                    timeout -s 9 5 cp ${fileName} ${osModprobe} 2>/dev/null
                done
                echo -e "\n${p3}\nEDAC: Blocked\n${p3}"
                edacBlockList=EDAC-modprobe-blocked.txt
                grep -Hi "blacklist.*edac" ${osModprobeFiles} 1>${osFile}/${edacBlockList}
                edacBlockCount=$(awk '/./{c++} END {print c+0}' ${osFile}/${edacBlockList})
                echo -e "File: ${edacBlockList}\nCount: ${edacBlockCount}"
                if [ ${edacBlockCount} -eq 0 ]; then
                    echo -e "List: None"
                else
                    echo -e "List:"
                    cat ${osFile}/${edacBlockList} | column -t
                fi
            fi
        fi
        # /proc/sys/fs
        echo -e "\n\n${p2}\nKernel - File Descriptor Limits\n${p2}"
        mkdir -p ${osProc}/sys/fs
        if [ ${?} -ne 0 ]; then escape; fi
        sysDirs=$(timeout -s 9 10 find /proc/sys/fs -mindepth 1 -type d | sed "s|/proc/sys|${osProc}/sys|g")
        mkdir -p ${sysDirs}
        if [ ${?} -ne 0 ]; then escape; fi
        sysFiles=$(timeout -s 9 10 find /proc/sys/fs -type f -not -name 'register')
        for file in ${sysFiles}; do
            fileDir=$(echo ${file} | sed "s|/proc/sys|${osProc}/sys|g")
            timeout -s 9 10 cp ${file} ${fileDir}
        done
        fsFiles="file-max file-nr inode-nr inode-state nr_open"
        for file in ${fsFiles}; do
            echo -e "${p3}\n${file}\n${p3}"
            timeout -s 9 10 cat ${osProc}/sys/fs/${file}
            echo -e ""
        done
        # Uptime / Reboot History
        echo -e "\n${p2}\nOS Report - Reboot History\n${p2}"
        timeout -s 9 10 last reboot -F 1>${osFile}/last-reboot 2>&1
        if [ -f ${osFile}/last-reboot ]; then
            cat ${osFile}/last-reboot
            echo ""
        fi
        echo -e "\n${p2}\nOS Report - Uptime\n${p2}\n"
        timeout -s 9 10 uptime 1>${osFile}/uptime 2>/dev/null
        if [ -f ${osFile}/uptime ]; then
            cat ${osFile}/uptime
            echo ""
        fi
        timeout -s 9 10 uptime -p 1>${osFile}/uptime-p 2>/dev/null
        if [ -f ${osFile}/uptime-p ]; then
            uptimeString=$(cat ${osFile}/uptime-p)
            echo -e "System has been ${uptimeString}" | tee ${osFile}/uptime-p.txt
        fi
    fi | tee ${osFile}/OS-Overview.txt
    cp ${osFile}/OS-Overview.txt ${reportDir}
    osOverviewReportComplete=1
	logTime
}
# Operation: Report - OS - Configuration
osConfigurationReport() {
    if [[ -n ${osConfigurationReportComplete} || ${osConfigurationReportComplete} -eq 1 ]]; then
        echo -e "\033[0;31m${p2}\nError - Duplicate Report\n${p2}\n"
        echo -e "Error: OS Configuration Report has already been executed.\033[0m\n"
    elif [[ -z ${osConfigurationReportComplete} || ${osConfigurationReportComplete} -eq 0 ]]; then
        if [ -z ${osInitComplete} ]; then osInit; fi
        echo -e "\n\n\n${p1}\nLHC - Processing - Report: OS - Configuration\n${p1}"
        echo -e "${p2}\nOS Report - System State\n${p2}"
        # ulimit
        echo -e "Processing: Host - ulimit -a"
        ulimit -a 1>${osFile}/ulimit_-a
        for cmdOpt in S H; do
            echo -e "Processing: Host - ulimit -a -${cmdOpt}"
            ulimit -a -${cmdOpt} 1>${osFile}/ulimit_-a-${cmdOpt}
        done 
        # uname
        for cmdOpt in a n r v; do
            echo -e "Processing: Host - uname -${cmdOpt}"
            timeout -s 9 10 uname -${cmdOpt} 1>${osFile}/uname_-${cmdOpt}
        done
        # ipcs
        echo -e "Processing: Host - ipcs -a"
        timeout -s 9 10 ipcs -a 1>${osFile}/ipcs_-a
        echo -e "Processing: Host - ipcs -a --human"
        timeout -s 9 10 ipcs -a --human 1>${osFile}/ipcs_-a_--human
        for cmdOpt in m q s; do
            for cmdOpt2 in c t l p u; do
                echo -e "Processing: Host - ipcs -${cmdOpt} -${cmdOpt2}"
                timeout -s 9 10 ipcs -${cmdOpt} -${cmdOpt2} 1>${osFile}/ipcs_-${cmdOpt}_-${cmdOpt2}
            done
        done
        # /etc/security
        mkdir ${osEtc}/security
        echo -e "Processing: Host - /etc/security/limits.conf"
        timeout -s 9 10 cp /etc/security/limits.conf ${osEtc}/security
        echo -e "Processing: Host - /etc/security/limits.d"
        timeout -s 9 10 cp -RL /etc/security/limits.d ${osEtc}/security
        # /etc/sysctl.d/
        echo -e "Processing: Host - /etc/sysctl.d/"
        timeout -s 9 10 cp -RL /etc/sysctl.d/ ${osEtc}
        # lsof
        echo -e "Processing: Host - lsof - Timeout: 3 minutes"
        startCmdTime=$(date +%s.%N)
        timeout -s 9 180 lsof 1>${osFile}/lsof 2>&1
        exitStatus=${?}
        endCmdTime=$(date +%s.%N)
        totalCmdTime=$(echo -e "${endCmdTime} - ${startCmdTime}" | bc -l)
        echo -e "${totalCmdTime}" 1>${osFile}/lsof-runtime
        if [ ${exitStatus} -ne 0 ]; then
            echo -e "Error: Failed to execute command: lsof" 1>${osFile}/lsof.err
        fi
        # hardware
        echo -e "Processing: Host - lshw"
        timeout -s 9 30 lshw 1>${osFile}/lshw 2>/dev/null
        if [ ${?} -eq 0 ]; then
            for cmdOpt in html json short businfo; do
                echo -e "Processing: Host - lshw -${cmdOpt}"
                timeout -s 9 30 lshw -${cmdOpt} 1>${osFile}/lshw-${cmdOpt} 2>/dev/null
            done
            for cmdOpt in communication cpu disk generic memory network power volume; do
                timeout -s 9 30 lshw -class ${cmdOpt} 1>${osFile}/lshw-class-${cmdOpt} 2>/dev/null
            done
        fi
        echo -e "Processing: Host - lsmem"
        timeout -s 9 10 lsmem 1>${osFile}/lsmem 2>/dev/null
        echo -e "Processing: Host - lsns"
        timeout -s 9 10 lsns 1>${osFile}/lsns 2>/dev/null
        echo -e "Processing: Host - lsipc"
        timeout -s 9 10 lsipc 1>${osFile}/lsipc 2>/dev/null
        echo -e "Processing: Host - lslocks"
        timeout -s 9 10 lslocks 1>${osFile}/lslocks 2>/dev/null
        # hostname 
        for cmdOpt in a A d f i I s; do
            echo -e "Processing: Host - hostname -${cmdOpt}"
            timeout -s 9 10 hostname -${cmdOpt} 1>${osFile}/hostname_-${cmdOpt} 2>/dev/null
        done
        # dmidecode
        if [[ -f /sbin/dmidecode && ${appInst} -eq 0 ]]; then
            cmdOpts="processor-version system-serial-number system-product-name bios-release-date bios-version baseboard-product-name baseboard-version chassis-serial-number"
            for cmdOpt in ${cmdOpts}; do
                echo -e "Processing: Host - dmidecode -s ${cmdOpt}"
                timeout -s 9 10 dmidecode -s ${cmdOpt} 1>${osFile}/dmidecode_-s_${cmdOpt}
            done
            cmdOpts="0 1 2 3 4 7 8 9 10 16 17 19 20 39 41 bios system baseboard chassis processor memory cache connector slot"
            for cmdOpt in ${cmdOpts}; do
                echo -e "Processing: Host - dmidecode -t ${cmdOpt}"
                timeout -s 9 10 dmidecode -t ${cmdOpt} 1>${osFile}/dmidecode_-t_${cmdOpt}
            done
        fi
        # services
        echo -e "Processing: Host - systemctl list-units"
        timeout -s 9 15 /bin/systemctl list-units 1>${osFile}/systemctl_list-units
        echo -e "Processing: Host - systemctl list-files"
        timeout -s 9 15 /bin/systemctl list-unit-files 1>${osFile}/systemctl_list-unit-files
        echo -e "Processing: Host - systemctl list-units --state=failed"
        timeout -s 9 15 /bin/systemctl list-units --state=failed 1>${osFile}/systemctl_list-units_--state_failed
        if [ ${?} -eq 0 ]; then
            failedServices=$(awk '$4=="failed"{print $2}' ${osFile}/systemctl_list-units_--state_failed)
        fi
        if [ -n "${failedServices}" ]; then
            for serviceName in ${failedServices}; do
                echo -e "Processing: Host - systemctl status ${serviceName}"
                timeout -s 9 10 /bin/systemctl status ${serviceName} 1>${osFile}/systemctl_status_${serviceName}
            done
        fi
        # journal
        echo -e "Processing: Host - journalctl --list-boots"
        timeout -s 9 30 /bin/journalctl --list-boots 1>${osFile}/journalctl_--list-boots 2>&1
        if [ ${?} -eq 0 ]; then
            bootIDs=$(timeout -s 9 10 awk '!/No journal/{print $1}' ${osFile}/journalctl_--list-boots | tail -n 10)
            for bootID in ${bootIDs}; do
                echo -e "Processing: Host - journalctl --no-pager -b ${bootID}"
                timeout -s 9 60 /bin/journalctl --no-pager -b ${bootID} 1>${osFile}/journalctl_-b_${bootID}
            done
        fi
        # software
        echo -e "Processing: Host - RPM - Package List"
        timeout -s 9 30 /bin/rpm -qa 1>${osFile}/Software-Package_List 2>&1
        if [ -f /usr/openv/pack/pack.summary ]; then
            echo -e "Processing: Host - RPM - EEB List"
            timeout -s 9 5 cp /usr/openv/pack/pack.summary ${osFile}/Software-Package_List-NBU_EEBs
        fi
        osConfigurationReportComplete=1
    fi
	logTime
}
osMessagesReport() {
    if [[ -n ${osMessagesReportComplete} || ${osMessagesReportComplete} -eq 1 ]]; then
        echo -e "\033[0;31m${p2}\nError - Duplicate Report\n${p2}\n"
        echo -e "Error: OS Messages Report has already been executed.\033[0m\n"
    elif [[ -z ${osMessagesReportComplete} || ${osMessagesReportComplete} -eq 0 ]]; then
        if [ ! -f /var/log/messages ]; then
            echo -e "Info: The '/var/log/messages' file does not exist. Skipping."
        elif [ -f /var/log/messages ]; then
            if [ -z ${osInitComplete} ]; then osInit; fi
            msgDir=${outputDir}/OS-Messages
            msgFile=${msgDir}/messages
            mkdir ${msgDir}
            echo -e "\n\n${p2}\nOS Report - Messages Log\n${p2}"
            echo -e "${p3}\nProcess Logs\n${p3}"
            msgCombined=${msgFile}-combined
            timeout -s 9 10 ls -ltrh /var/log/messages* 1>${msgFile}-file_list.txt
            msgCompressed=$(ls -1 /var/log/messages-*\.*gz 2>/dev/null)
            if [ -n "${msgCompressed}" ]; then
                for fileName in ${msgCompressed}; do
                    fileSize=$(stat -c "%s" ${fileName} 2>/dev/null)
                    if [ "${fileSize}" -lt 5000000000 ]; then
                        echo -e "Processing: Messages - Log File: ${fileName}"
                        echo -e "\tExtracting..."
                        timeout -s 9 90 gzip -d ${fileName} 1>/dev/null
                        if [ ${?} -eq 0 ]; then
                            fileExtracted=$(echo -e ${fileName} | awk -F'.' '{print $1}')
                            fileName=$(ls -1 ${fileExtracted}*)
                            if [ ${?} -eq 0 ]; then
                                echo -e "\tCopying..."
                                cat ${fileName} 1>>${msgCombined}
                                echo -e "\tCompressing..."
                                timeout -s 9 90 gzip ${fileName} 1>/dev/null
                            else
                                echo -e "\tExtracting... Error"
                                echo -e "Error: Failed processing file: ${fileName}" 1>> ${msgFile}-file_list-extract.txt
                            fi
                        else
                            echo -e "\tExtracting... Error" | tee -a ${msgFile}-file_list-extract.txt
                            echo -e "Error: Failed extracting file: ${fileName}" 1>> ${msgFile}-file_list-extract.txt
                        fi
                    else
                        echo -e "WARNING: Messages log greater than 5 GB in size. Review file manually and check '/etc/audit/auditd.conf' settings." | tee -a ${msgFile}-file_list-size.txt
                        echo -e "Processing: Messages - Log File: ${fileName}: SKIPPED" | tee -a ${msgFile}-file_list-size.txt
                        messagesAlert="${messagesAlert} ${fileName}"
                    fi
                done
            fi
            msgLogs=$(ls -1tr /var/log/messages* | grep -v "\.*gz")
            for fileName in ${msgLogs}; do
                fileSize=$(stat -c "%s" ${fileName} 2>/dev/null)
                if [ "${fileSize}" -lt 5000000000 ]; then
                    echo -e "Processing: Messages - Log File: ${fileName}"
                    cat ${fileName} 1>>${msgCombined}
                else
                    echo -e "WARNING: Messages log greater than 5 GB in size. Review file manually and check '/etc/audit/auditd.conf' settings." | tee -a ${msgFile}-file_list-size.txt
                    echo -e "Processing: Messages - Log File: ${fileName}: SKIPPED" | tee -a ${msgFile}-file_list-size.txt
                    messagesAlert="${messagesAlert} ${fileName}"
                fi
                touch ${fileName}
            done
            echo -e "${messagesAlert}" 1>${msgFile}-file_list-size
            echo -e "\n${p3}\nProcess Reports\n${p3}"
            echo -e "Processing: Messages - Errors"
            grep -ai 'error\|\serr\s\|fail\|fault\|fatal\|warn\|invalid\|conflict\|crit\|exception\|cannot\|unable' ${msgCombined} 1>${msgFile}-errors
            # Kernel
            echo -e "Processing: Messages - Kernel"
            grep -ai "kernel" ${msgCombined} 1>${msgFile}-kernel
            echo -e "Processing: Messages - Kernel - Call Trace"
            grep -a -B30 -A70 "Call Trace" ${msgCombined} 1>${msgFile}-Call_Trace
            grep -a "Call Trace" ${msgFile}-Call_Trace 1>${msgFile}-Call_Trace-List
            # Memory
            echo -e "Processing: Messages - Memory - EDAC Messages"
            grep -a "\sEDAC\s" ${msgCombined} 1>${msgFile}-EDAC-Memory_Errors
            echo -e "Processing: Messages - Memory - vmalloc"
            grep -ai "vmalloc" ${msgCombined} 1>${msgFile}-errors-vmalloc
            echo -e "Processing: Messages - Memory - Out-of-Memory ('oom')"
            grep -ai "invoked oom-killer" ${msgCombined} 1>${msgFile}-errors-oom-out_of_memory
            # Hardware
            echo -e "Processing: Messages - Hardware - Machine Check Exceptions"
            grep -ai "\sMCE\|Hardware Error\|rank" ${msgCombined} 1>${msgFile}-MCE-Machine_Check_Exceptions
            # Storage
            echo -e "Processing: Messages - Storage - File System - Events"
            grep -ai "File System Check\|fsck\|mount\|unmount\|umount\|reboot\|cgroup\|replay\|corrupt\|corrupted\|data loss" ${msgCombined} 1>${msgFile}-File_System-Events
            echo -e "Processing: Messages - Storage - File System - Errors"
            grep -ai "mount" ${msgFile}-File_System-Events 1>${msgFile}-File_System-Events-mount
            grep -ai "fail\|cannot" ${msgFile}-File_System-Events-mount 1>${msgFile}-File_System-Events-mount-errors
            grep -ai "corrupt\|corrupted\|data loss\|fsck" ${msgFile}-File_System-Events 1>${msgFile}-File_System-Events-corruption
            grep -a "File System Check\|fsck" ${msgFile}-File_System-Events-corruption 1>${msgFile}-File_System-Events-fsck-file_system_check
            echo -e "Processing: Messages - Storage - Device Events"
            grep -a "No space left" ${msgCombined} 1>${msgFile}-No_Space_Left
            grep -a "LUN assignments" ${msgCombined} 1>${msgFile}-LUN_Assignment_Changed
            grep -a "pipe failed.*for OS Report device" ${msgCombined} 1>${msgFile}-Pipe_failed_for_os_device
            echo -e "Processing: Messages - Storage - Device Status"
            grep -a "offline device" ${msgCombined} 1>${msgFile}-Offline_Device
            grep -a "Read Capacity" ${msgCombined} 1>${msgFile}-Read_Capacity
            # Veritas
            echo -e "Processing: Messages - Veritas - UMI Code Errors"
            grep -a "V-[[:digit:]]*-[[:digit:]]" ${msgCombined} 1>${msgFile}-UMI_Code_Messages
            grep -a "blk_update_request: critical target error" ${msgCombined} 1>${msgFile}-Blk_update_request_critical_target_error
            echo -e "Processing: Messages - Veritas - VxDMP - UMI V-5-#"
            grep -a "V-5-[[:digit:]]" ${msgCombined} 1>${msgFile}-DMP_Events
            grep -a "disabled path\|belonging to" ${msgCombined} 1>${msgFile}-DMP_Events-Disabled_Path
            echo -e "Processing: Messages - Veritas - VxDMP - Malloc Failed"
            grep -ai "memory allocation failed for size" ${msgCombined} 1>>${msgFile}-DMP_Events-Memory_Exhaustion 2>/dev/null
            echo -e "Processing: Messages - Veritas - MSDP - Events - Process: spad"
            grep -a "\sspad\s" ${msgCombined} 1>${msgFile}-MSDP-spad-events
            echo -e "Processing: Messages - Veritas - MSDP - Events - Process: spoold"
            grep -a "\sspoold\s" ${msgCombined} 1>${msgFile}-MSDP-spoold-events
            echo -e "Processing: Messages - Veritas - MSDP - Events - Containers"
            grep -ai "failed to close container" ${msgCombined} 1>${msgFile}-msdp-containers-failed_to_close
            eventCount=$(awk '/./{c++} END {print c+0}' ${msgFile}-msdp-containers-failed_to_close)
            if [ ${eventCount} -gt 0 ]; then
                awk '{print $(NF-3)}' ${msgFile}-msdp-containers-failed_to_close | sort -n | uniq -c 1>${msgFile}-msdp-containers-failed_to_close-DCID_List
            fi
            echo -e "Processing: Messages - Veritas - MSDP - Events - Records"
            grep -ai "failed to read records from dcid" ${msgCombined} 1>${msgFile}-msdp-containers-failed_to_read
            eventCount=$(awk '/./{c++} END {print c+0}' ${msgFile}-msdp-containers-failed_to_read)
            if [ ${eventCount} -gt 0 ]; then
                awk '{print $(NF-2)}' ${msgFile}-msdp-containers-failed_to_read | sort -n | uniq -c 1>${msgFile}-msdp-containers-failed_to_read-DCID_List
            fi
            echo -e "Processing: Messages - System - Audit - User Reboot"
            grep -a "User.*executed reboot" ${msgCombined} 1>${msgFile}-Reboot-By_User
            echo -e "Processing: Messages - Compression - gzip - Timeout: 5 minutes"
            timeout -s 9 300 gzip ${msgCombined}
            # Diagnostic Messages - dmesg
            mkdir ${msgDir}/dmesg
            dmesgFile=${msgDir}/dmesg/dmesg
            echo -e "Processing: Diagnostic - dmesg -H"
            timeout -s 9 120 dmesg -H 1>${dmesgFile}_-H 2>&1
            if [ ${?} -eq 0 ]; then
                echo -e "Processing: Diagnostic - dmesg -r"
                timeout -s 9 120 dmesg -r 1>${dmesgFile}_-r 2>&1
                echo -e "Processing: Diagnostic - dmesg -T -d"
                timeout -s 9 120 dmesg -T -d 1>${dmesgFile}_-T_-d 2>&1
                cmdOpts="kern user daemon auth syslog"
                for cmdOpt in ${cmdOpts}; do
                    echo -e "Processing: Diagnostic - dmesg -f ${cmdOpt}"
                    timeout -s 9 120 dmesg -f ${cmdOpt} 1>${dmesgFile}_-f_${cmdOpt} 2>&1
                done
            fi
        fi
        # Core Files
        echo -e "\n\n${p2}\nOS Report - Core Files\n${p2}"
        coreDir=${outputDir}/OS-Core_Files
        coreFile=${coreDir}
        mkdir ${coreDir} 
        corePath=$(sed 's![^/]*$!!' /proc/sys/kernel/core_pattern)
        timeout -s 9 10 cat /proc/sys/kernel/core_pattern 1>${coreFile}/Core_Pattern-file_path
        echo -e "Core Path: ${corePath}\n"
        if [ ! -d ${corePath} ]; then
            echo -e "Warning: The output directory for Core Files defined in '/proc/sys/kernel/core_pattern' does not exist." | tee ${coreFile}/Core_Files-config.txt
            echo -e "Warning: Core files will not be generated in event of crashing processes." | tee -a ${coreFile}/Core_Files-config.txt
        else
            timeout -s 9 30 find -L ${corePath} -type f 1>${coreFile}/Core_Files 2>/dev/null
            fileCount=$(timeout -s 9 10 awk '/./{c++} END {print c+0}' ${coreFile}/Core_Files)
            if [ ${fileCount} -eq 0 ]; then
                echo -e "Info: No core files present in ${corePath}." | tee ${coreFile}/Core_Files-status.txt
            else
                echo -e "Warning: Total of ${fileCount} core files present in ${corePath}." | tee ${coreFile}/Core_Files-status.txt
                for nDays in 7 14 30 60 90 180 365; do 
                    timeout -s 9 15 find -L ${corePath} -type f -mtime -${nDays} 1>${coreFile}/Core_Files-${nDays}-days 2>/dev/null
                done
            fi
        fi
        osMessagesReportComplete=1
    fi
	logTime
}
# Operation: Report - Storage
storageReport() {
    if [[ -n ${storageReportComplete} || ${storageReportComplete} -eq 1 ]]; then
        echo -e "\033[0;31m${p2}\nError - Duplicate Report\n${p2}\n"
        echo -e "Error: Storage Report has already been executed.\033[0m\n"
    elif [[ -z ${storageReportComplete} || ${storageReportComplete} -eq 0 ]]; then
        storageDir=${outputDir}/Storage
        mkdir ${storageDir}
        storageFile=${storageDir}
        echo -e "\n\n\n${p1}\nLHC - Processing - Report: Storage\n${p1}"
        # Utilization
        echo -e "Processing: Storage - Utilization - df -h"
        timeout -s 9 10 df -h 1>${storageFile}/df-h 2>/dev/null
        echo -e "Processing: Storage - Utilization - df -i"
        timeout -s 9 10 df -i 1>${storageFile}/df-i 2>/dev/null
        # Devices
        echo -e "Processing: Storage - Devices - lscpu"
        timeout -s 9 20 lscpu 1>${storageFile}/lscpu 2>/dev/null
        echo -e "Processing: Storage - Devices - lspci -vv"
        timeout -s 9 20 lspci -vv 1>${storageFile}/lspci-vv 2>/dev/null
        echo -e "Processing: Storage - Devices - lsscsci -dsig"
        timeout -s 9 20 lsscsi -dsig 1>${storageFile}/lsscsi-dsig 2>/dev/null
        echo -e "Processing: Storage - Devices - sg_map -i -x"
        timeout -s 9 20 sg_map -i -x 1>${storageFile}/sg_map-i-x 2>/dev/null
        echo -e "Processing: Storage - Devices - lsblk -ai"
        timeout -s 9 20 lsblk -ai 1>${storageFile}/lsblk-a 2>/dev/null
        echo -e "Processing: Storage - Devices - lsblk -aP"
        timeout -s 9 20 lsblk -aP 2>/dev/null | column -t 1>${storageFile}/lsblk-aP 
        echo -e "Processing: Storage - Devices - lsblk -l"
        timeout -s 9 20 lsblk -l 1>${storageFile}/lsblk-l 2>/dev/null
        # /proc/scsi
        echo -e "Processing: Storage - SCSI - /proc/scsi/scsi"
        timeout -s 9 10 cat /proc/scsi/scsi 1>${storageFile}/proc-scsi-scsi 2>/dev/null
        echo -e "Processing: Storage - SCSI - /proc/scsi/sg/device_strs"
        timeout -s 9 10 cat /proc/scsi/sg/device_strs 1>${storageFile}/proc-scsi-device_strs 2>/dev/null
        # Mount Points
        echo -e "Processing: Storage - Mounts - /bin/findmnt"
        timeout -s 9 10 /bin/findmnt 1>${storageFile}/file_system-mounts-findmnt 2>/dev/null
        echo -e "Processing: Storage - Mounts - /proc/mounts"
        timeout -s 9 10 cat /proc/mounts 1>${storageFile}/file_system-mounts-proc-mounts 2>/dev/null
        echo -e "Processing: Storage - Mounts - /etc/fstab"
        timeout -s 9 10 cat /etc/fstab 1>${storageFile}/file_system-mounts-etc-fstab 2>/dev/null
        # Storage Statistics
        if [ -f /bin/vmstat ]; then
            echo -e "Processing: Storage - vmstat - vmstat -D"
            timeout -s 9 10 /bin/vmstat -D 1>${storageFile}/vmstat-D
            echo -e "Processing: Storage - vmstat - vmstat -d"
            timeout -s 9 10 /bin/vmstat -dw 1>${storageFile}/vmstat-dw
        fi
        # VxVM Checkpoints
        if [ -f ${storageFile}/file_system-mounts-proc-mounts ]; then
            mountPoints=$(grep "\svxfs\s" ${storageFile}/file_system-mounts-proc-mounts | awk '{print $2}') 
            for mountPoint in ${mountPoints}; do
                echo -e "Processing: Storage - VxVM - Checkpoints - fsckptadm list ${mountPoint}"
                mountName=$(echo ${mountPoint} | awk -F'/' '{print $NF}')
                timeout -s 9 15 /opt/VRTS/bin/fsckptadm list ${mountPoint} 1>${storageFile}/fsckptadm_list-${mountName} 2>/dev/null
            done
        fi
        # VxVM Configuration
        if [ -f /sbin/vxprint ]; then
            echo -e "Processing: Storage - VxVM - Configuration - vxprint -ht"
            timeout -s 9 15 /sbin/vxprint 1>${storageFile}/vxprint
            if [ -d /etc/vx/cbr/bk ]; then
                timeout -s 9 10 ls -ltr $(find /etc/vx/cbr/bk/ -name "*cfgrec") 1>${storageFile}/vxprint-config_files 2>/dev/null
                for configFile in $(awk '{print $NF}' ${storageFile}/vxprint-config_files); do
                    fileTime=$(stat -c "%X" ${configFile})
                    vxvmDiskGroup=$(head ${configFile} | grep "^dg\s" | awk '{print $2}')
                    cat ${configFile} | timeout -s 9 15 /sbin/vxprint -D - -ht 1>${storageFile}/vxprint-ht-${fileTime}-${vxvmDiskGroup} 
                done
            fi
        fi
        # VxVM Device List
        if [ -f /sbin/vxdisk ]; then
            echo -e "Processing: Storage - VxVM - Storage - vxdisk list -eo alldgs"
            timeout -s 9 15 /sbin/vxdisk list -eo alldgs 1>${storageFile}/vxdisk_list_-eo_alldgs 2>&1
            echo -e "Processing: Storage - VxVM - Storage - vxdisk list -o cluster"
            timeout -s 9 15 /sbin/vxdisk list -o cluster 1>${storageFile}/vxdisk_list_-o_cluster 2>&1
            echo -e "Processing: Storage - VxVM - Storage - vxdisk list -o udid"
            timeout -s 9 15 /sbin/vxdisk list -o udid 1>${storageFile}/vxdisk_list_-o_udid 2>&1
        fi
        # VxVM Device Mapping
        if [ -d /dev/vx/dsk ]; then
            echo -e "Processing: Storage - VxVM - Device Mappings"
            timeout -s 9 15 find /dev/vx/dsk -type b 1>${storageFile}/vxvm-device-list
            while read device; do
                deviceID=$(timeout -s 9 5 ls -l ${device} | awk '{print $6}')
                echo -e "${device} \t\t VxVM${deviceID}";
            done <${storageFile}/vxvm-device-list | column -t 1>${storageFile}/vxvm-device-mappings
        fi
        # VxVM Disk Info
        if [ -f /etc/vx/disk.info ]; then
            echo -e "Processing: Storage - VxVM - /etc/vx/disk.info"
            timeout -s 9 5 cat /etc/vx/disk.info 1>${storageFile}/vxvm-disk.info
        fi
        # VxVM Task List
        if [ -f /sbin/vxtask ]; then
            timeout -s 9 5 /sbin/vxtask list 1>${storageFile}/vxtask_list
            timeout -s 9 5 /sbin/vxtask monitor 1>${storageFile}/vxtask_monitor
        fi
        # VxVM Volume Config
        if [ -f /sbin/vxdctl ]; then
            echo -e "Processing: Storage - VxVM - Volume Configuration"
            timeout -s 9 10 /sbin/vxdctl -c mode 1>${storageFile}/vxdctl_-c_mode 2>&1
            timeout -s 9 10 /sbin/vxdctl list 1>${storageFile}/vxdctl_list 2>&1
        fi
        # VxVM Cluster Info
        if [ -f /opt/VRTS/bin/vxclustadm ]; then
            timeout -s 9 10 /opt/VRTS/bin/vxclustadm nidmap 1>${storageFile}/vxclustadm_nidmap 2>&1
            timeout -s 9 10 /opt/VRTS/bin/vxclustadm nodestate 1>${storageFile}/vxclustadm_nodestate 2>&1
        fi
        # VxVM Dynamic Multi-Pathing
        if [ -f /sbin/vxdmpadm ]; then
            echo -e "Processing: Storage - VxDMP - vxdmpadm getdmpnode"
            timeout -s 9 60 vxdmpadm getdmpnode 1>${storageFile}/vxdmpadm_getdmpnode
            echo -e "Processing: Storage - VxDMP - vxdmpadm getsubpaths"
            timeout -s 9 60 vxdmpadm getsubpaths 1>${storageFile}/vxdmpadm_getsubpaths
            echo -e "Processing: Storage - VxDMP - vxdmpadm list dmpnode all"
            timeout -s 9 60 vxdmpadm list dmpnode all 1>${storageFile}/vxdmpadm_vxdmpadm_list_dmpnode_all
        fi
        # QLogic Commands - qaucli
        if [ -f /bin/nohup ]; then
            if [ -f /opt/QLogic_Corporation/QConvergeConsoleCLI/qaucli ]; then
                echo -e "Processing: Storage - QLogic - qaucli -pr fc -z"
                nohup timeout -s 9 300 /opt/QLogic_Corporation/QConvergeConsoleCLI/qaucli -pr fc -z 2>>${storageFile}/qaucli.err 1>${storageFile}/qaucli-pr-fc-z &
                echo -e "$!" 1>>${storageFile}/qaucli.pid
                echo -e "Processing: Storage - QLogic - qaucli -g"
                nohup timeout -s 9 300 /opt/QLogic_Corporation/QConvergeConsoleCLI/qaucli -g 2>>${storageFile}/qaucli.err 1>${storageFile}/qaucli-g &
                echo -e "$!" 1>>${storageFile}/qaucli.pid
                echo -e "Processing: Storage - QLogic - qaucli -i"
                nohup timeout -s 9 300 /opt/QLogic_Corporation/QConvergeConsoleCLI/qaucli -i 2>>${storageFile}/qaucli.err 1>${storageFile}/qaucli-i &
                echo -e "$!" 1>>${storageFile}/qaucli.pid
                if [ -f ${storageFile}/qaucli.pid ]; then
                    echo -e "\nWaiting for 'qaucli' commands to complete... Timeout: 5 minutes"
                    pidList=$(cat ${storageFile}/qaucli.pid)
                    startCmdTime=$(date +%s.%N)
                    wait ${pidList}
                    endCmdTime=$(date +%s.%N)
                    totalCmdTime=$(echo -e "${endCmdTime} - ${startCmdTime}" | bc -l)
                    echo -e "${totalCmdTime}" 1>${storageFile}/qaucli.1.runtime
                    echo -e "\nWaiting for 'qaucli' commands to complete... Done.\n"
                fi
                hbaInstances=$(timeout -s 9 10 grep "^HBA Instance" ${storageFile}/qaucli-i | awk '{print $NF}' | sort -n)
                hbaInstancesCount=$(echo ${hbaInstances} | wc -l)
                if [ ${hbaInstancesCount} -gt 0 ]; then
                    for hbaInstance in ${hbaInstances}; do
                        echo -e "Processing: Storage - QLogic - qaucli -l ${hbaInstance}"
                        nohup timeout -s 9 300 /opt/QLogic_Corporation/QConvergeConsoleCLI/qaucli -l ${hbaInstance} 2>>${storageFile}/qaucli.err 1>${storageFile}/qaucli-l-${hbaInstance} & 
                        echo -e "$!" 1>>${storageFile}/qaucli.instance.pid
                        echo -e "Processing: Storage - QLogic - qaucli -c ${hbaInstance}"
                        nohup timeout -s 9 300 /opt/QLogic_Corporation/QConvergeConsoleCLI/qaucli -c ${hbaInstance} 2>>${storageFile}/qaucli.err 1>${storageFile}/qaucli-c-${hbaInstance} &
                        echo -e "$!" 1>>${storageFile}/qaucli.instance.pid
                        echo -e "Processing: Storage - QLogic - qaucli -t ${hbaInstance}"
                        nohup timeout -s 9 300 /opt/QLogic_Corporation/QConvergeConsoleCLI/qaucli -t ${hbaInstance} 2>>${storageFile}/qaucli.err 1>${storageFile}/qaucli-t-${hbaInstance} &
                        echo -e "$!" 1>>${storageFile}/qaucli.instance.pid
                    done
                    if [ -f ${storageFile}/qaucli.instance.pid ]; then
                        echo -e "\nWaiting for 'qaucli' commands to complete... Timeout: 5 minutes"
                        pidList=$(cat ${storageFile}/qaucli.instance.pid)
                        startCmdTime=$(date +%s.%N)
                        wait ${pidList}
                        endCmdTime=$(date +%s.%N)
                        totalCmdTime=$(echo -e "${endCmdTime} - ${startCmdTime}" | bc -l)
                        echo -e "${totalCmdTime}" 1>${storageFile}/qaucli.2.runtime
                        echo -e "\nWaiting for 'qaucli' commands to complete... Done."
                    fi
                fi
            fi
        fi
        storageReportComplete=1
    fi
	logTime
}
# Operation: Report - Memory
memoryReport() {
    if [[ -n ${memoryReportComplete} || ${memoryReportComplete} -eq 1 ]]; then
        echo -e "\033[0;31m${p2}\nError - Duplicate Report\n${p2}\n"
        echo -e "Error: Memory Report has already been executed.\033[0m\n"
    elif [[ -z ${memoryReportComplete} || ${memoryReportComplete} -eq 0 ]]; then
        echo -e "\n\n\n${p1}\nLHC - Processing - Report: Memory\n${p1}"
        memoryDir=${outputDir}/Memory
        memoryFile=${memoryDir}
        memoryReport=${memoryFile}
        mkdir ${memoryDir}
        # Memory - dmidecode
        if [[ -f /sbin/dmidecode && ${appInst} -eq 0 ]]; then
            timeout -s 9 30 /sbin/dmidecode -t17 1>${memoryReport}/dmidecode-memory_modules 2>&1
            if [ ${?} -ne 0 ]; then
                echo -e "Error: Failed to execute command: /sbin/dmidecode -t17" | tee ${memoryReport}/dmidecode-memory_modules.err
            else
                echo -e "${p2}\nMemory Modules - All\n${p2}"
                grep 'Size:\|Locator:\|Type:' ${memoryReport}/dmidecode-memory_modules | \
                grep -v "Configured.*Speed:\|Range\|Bank Locator\|Non-Volatile Size:\|Volatile Size:\|Cache Size:\|Logical Size:" | sed 's/[[:blank:]]*$//;s/\t//;s/$/,/g' | \
                awk '{ORS=NR % 3? " ": "\n"; print}' | sed -e 's/^ *//g;s/No Module Installed/None/g;s/^\t//g;s/\tType/ Type/g' 1>${memoryReport}/dmidecode-memory_modules-parsed-all.csv
                column -t -s, ${memoryReport}/dmidecode-memory_modules-parsed-all.csv 1>${memoryReport}/dmidecode-memory_modules-parsed-all.txt
                cat ${memoryReport}/dmidecode-memory_modules-parsed-all.txt
                echo -e "\n${p2}\nMemory Modules - Installed\n${p2}"
                grep "Size:\|Locator:\|Type:\|Speed:\|Serial Number:\|Manufacturer:\|Part Number:" ${memoryReport}/dmidecode-memory_modules | sed 's/[[:blank:]]*$//;s/\t//;s/$/,/g' | \
                grep -v "Configured.*Speed:\|Range" | grep "Part Number:" -B7 | grep -v "^\-\-" | \
                awk '{ORS=NR % 8? " ": "\n"; print}' 1>${memoryReport}/dmidecode-memory_modules-parsed-installed.csv
                usedSlots=$(awk '/./{c++} END {print c+0}' ${memoryReport}/dmidecode-memory_modules-parsed-installed.csv)
                echo -e "Used Slots: ${usedSlots}\n"
                column -t -s, ${memoryReport}/dmidecode-memory_modules-parsed-installed.csv 1>${memoryReport}/dmidecode-memory_modules-parsed-installed.txt
                cat ${memoryReport}/dmidecode-memory_modules-parsed-installed.txt
                echo -e "\n${p2}\nMemory Modules - Empty\n${p2}"
                grep "Size: None" ${memoryReport}/dmidecode-memory_modules-parsed-all.csv 1>${memoryReport}/dmidecode-memory_modules-parsed-empty.csv
                emptySlots=$(awk '/./{c++} END {print c+0}' ${memoryReport}/dmidecode-memory_modules-parsed-empty.csv)
                echo -e "Empty Slots: ${emptySlots}\n"
                if [ ${emptySlots} -gt 0 ]; then
                    column -t -s, ${memoryReport}/dmidecode-memory_modules-parsed-empty.csv 1>${memoryReport}/dmidecode-memory_modules-parsed-empty.txt
                    cat ${memoryReport}/dmidecode-memory_modules-parsed-empty.txt
                else
                    echo "Physical Memory Modules are fully populed. No empty slots available."
                fi
                echo -e "Used Slots: ${usedSlots}\nEmpty Slots: ${emptySlots}" 1>${memoryReport}/dmidecode-memory_modules-populated
                echo -e "Used_Slots=${usedSlots}\nEmpty_Slots=${emptySlots}" 1>${memoryReport}/dmidecode-memory_modules-populated.cfg
            fi | tee ${memoryReport}/dmidecode-memory_modules.txt
            cp ${memoryReport}/dmidecode-memory_modules.txt ${reportDir}/Hardware-dmidecode-memory_modules.txt
            echo -e "\n\n"
        fi
        # Process Statistics
        echo -e "${p2}\nMemory - Process Level Data\n${p2}"
        echo -e "${p3}\nData Collection\n${p3}"
        # Process Statistics - top
        echo -e "Processing: Host - top -b -n1"
        timeout -s 9 20 top -b -n1 1>${memoryReport}/top 2>/dev/null
        echo -e "Processing: Host - top -b -n1 -o %CPU"
        timeout -s 9 20 top -b -n1 -o %CPU 1>${memoryReport}/top-cpu 2>/dev/null
        echo -e "Processing: Host - top -b -n1 -o %MEM"
        timeout -s 9 20 top -b -n1 -o %MEM 1>${memoryReport}/top-mem 2>/dev/null
        # Process Statistics - ps
        psOut=${memoryReport}/process-full-ps-aux
        psOutTree=${memoryReport}/process-tree-ps-axjf
        psOutThread=${memoryReport}/process-thread-ps-Lef
        echo -e "Processing: Host - ps -Hej"
        timeout -s 9 20 ps -Hej 1>${memoryReport}/process-tree-ps-Hej
        echo -e "Processing: Host - ps -Lef"
        timeout -s 9 20 ps -Lef 1>${psOutThread}
        grep "[o]penv\|[n]b\|[b]p" ${psOutThread} | awk '{print $10}' | sort | uniq -c | sort -nr 1>${psOutThread}-count
        echo -e "Processing: Host - ps -axjf"
        timeout -s 9 20 ps -axjf 1>${psOutTree} 2>/dev/null
        echo -e "Processing: Host - ps aux --sort=pid"
        timeout -s 9 20 ps aux --sort=pid 1>${psOut} 2>/dev/null
        echo -e "Processing: Host - ps aux --sort=-time"
        timeout -s 9 20 ps aux --sort=-time 1>${psOut}-TIME 2>/dev/null
        echo -e "Processing: Host - ps aux --sort=-pcpu"
        timeout -s 9 20 ps aux --sort=-pcpu 1>${psOut}-PCPU 2>/dev/null
        timeout -s 9 20 cut -c1-150 ${psOut}-PCPU 1>${psOut}-PCPU-cut
        echo -e "Processing: Host - ps aux --sort=-pmem"
        timeout -s 9 20 ps aux --sort=-pmem 1>${psOut}-PMEM 2>/dev/null
        timeout -s 9 20 cut -c1-150 ${psOut}-PMEM 1>${psOut}-PMEM-cut
        echo -e "Processing: Host - ps aux --sort=-rss"
        timeout -s 9 20 ps aux --sort=-rss 1>${psOut}-RSS 2>/dev/null
        timeout -s 9 20 cut -c1-150 ${psOut}-RSS 1>${psOut}-RSS-cut
        echo -e "Processing: Host - ps aux --sort=-vsz"
        timeout -s 9 20 ps aux --sort=-vsz 1>${psOut}-VSZ 2>/dev/null
        timeout -s 9 20 cut -c1-150 ${psOut}-VSZ 1>${psOut}-VSZ-cut
        # Memory Overview
        echo -e "Processing: Host - free -k"
        timeout -s 9 15 free -k 1>${memoryReport}/free-k 2>/dev/null
        echo -e "Processing: Host - free -m"
        timeout -s 9 15 free -m 1>${memoryReport}/free-m 2>/dev/null
        echo -e "Processing: Host - free -g"
        timeout -s 9 15 free -g 1>${memoryReport}/free-g 2>/dev/null
        echo -e "Processing: Host - free -htl"
        timeout -s 9 15 free -htl 1>${memoryReport}/free-htl 2>/dev/null
        echo -e "Processing: Host - free -htlw"
        timeout -s 9 15 free -htlw 1>${memoryReport}/free-htlw 2>/dev/null
        # /proc/meminfo
        echo -e "Processing: Host - /proc/meminfo"
        timeout -s 9 10 cat /proc/meminfo 1>${memoryReport}/proc-meminfo 2>/dev/null
        if [ -f ${memoryReport}/proc-meminfo ]; then
            sort -nrk2 ${memoryReport}/proc-meminfo 1>${memoryReport}/proc-meminfo-sort
        fi
        # /proc/zoneinfo
        echo -e "Processing: Host - /proc/zoneinfo"
        timeout -s 9 10 cat /proc/zoneinfo 1>${memoryReport}/proc-zoneinfo 2>/dev/null
        # /proc/slabinfo
        echo -e "Processing: Host - /proc/slabinfo"
        timeout -s 9 10 cat /proc/slabinfo 1>${memoryReport}/proc-slabinfo 2>/dev/null
        # /proc/zoneinfo
        echo -e "Processing: Host - /proc/zoneinfo"
        timeout -s 9 10 cat /proc/zoneinfo 1>${memoryReport}/proc-zoneinfo 2>/dev/null
        # /proc/buddyinfo
        echo -e "Processing: Host - /proc/buddyinfo"
        timeout -s 9 10 cat /proc/buddyinfo 1>${memoryReport}/proc-buddyinfo 2>/dev/null
        if [ -f ${memoryReport}/proc-buddyinfo ]; then
            # /proc/buddyinfo - Header
            echo -e "Processing: Host - /proc/buddyinfo - Report"
            echo -e "\n\n      Order           |    0      1      2      3      4      5      6      7      8      9     10 |\n      Zone 4k Pages   |    1      2      4      8     16     32     64    128    256    512   1024 |\n      Zone Byte Size  |  4kB    8kB   16kB   32kB   64kB  128kB  256kB  512kB 1024kB 2048kB 4096kB |\nNode             Zone |$(printf ' %.0s' {0..75})|\n----------------------+$(printf '\055%-.0s' {0..75})+" 1>${memoryReport}/proc-buddyinfo-header
            cat ${memoryReport}/proc-buddyinfo 1>>${memoryReport}/proc-buddyinfo-header
            # /proc/buddyinfo - Total
            echo -e "Processing: Host - /proc/buddyinfo - Sum"
            echo -e "\n\n$(printf ' %.0s' {0..23})Order          |    0      1      2      3      4      5      6      7      8      9     10 |\n$(printf ' %.0s' {0..23})Zone 4k Pages  |    1      2      4      8     16     32     64    128    256    512   1024 |\n$(printf ' %.0s' {0..23})Zone Byte Size |  4kB    8kB   16kB   32kB   64kB  128kB  256kB  512kB 1024kB 2048kB 4096kB |\nTotal            Node             Zone |$(printf ' %.0s' {0..75})|\n$(printf '\055%-.0s' {0..38})+$(printf '\055%-.0s' {0..75})+" 1>${memoryReport}/proc-buddyinfo-total
            cat ${memoryReport}/proc-buddyinfo | awk '{ sum = $5 * 2**0 * 4096 + $6 * 2**1 * 4096 + $7 * 2**2 * 4096 + $8 * 2**3 * 4096 + $9 * 2**4 * 4096 + $10 * 2**5 * 4096 + $11 * 2**6 * 4096 + $12 * 2**7 * 4096 + $13 * 2**8 * 4096 + $14 * 2**9 * 4096 + $15 * 2**10 * 4096; printf "%10.2f MiB   ", sum / 1024 / 1024; print }' 1>>${memoryReport}/proc-buddyinfo-total
        fi
        # /proc/pagetypeinfo
        echo -e "Processing: Host - /proc/pagetypeinfo"
        timeout -s 9 10 cat /proc/pagetypeinfo 1>${memoryReport}/proc-pagetypeinfo 2>/dev/null
        if [ -f ${memoryReport}/proc-pagetypeinfo ]; then
            # /proc/pagetypeinfo - Header
            echo -e "Processing: Host - /proc/pagetypeinfo - Report"
            echo -e "\n\n\t\t\t    Order           |    0      1      2      3      4      5      6      7      8      9     10 |\n\t\t\t    Zone 4k Pages   |    1      2      4      8     16     32     64    128    256    512   1024 |\n\t\t\t    Zone Byte Size  |  4kB    8kB   16kB   32kB   64kB  128kB  256kB  512kB 1024kB 2048kB 4096kB |\nNode \t\t    Zone    \t       Type |$(printf ' %.0s' {0..75})|\n$(printf '\055%-.0s' {0..43})+$(printf '\055%-.0s' {0..75})+" 1>${memoryReport}/proc-pagetypeinfo-header
            cat ${memoryReport}/proc-pagetypeinfo 1>>${memoryReport}/proc-pagetypeinfo-header
        fi
        # /proc/vmallocinfo
        echo -e "Processing: Host - /proc/vmallocinfo"
        timeout -s 9 10 cat /proc/vmallocinfo 1>${memoryReport}/proc-vmallocinfo 2>/dev/null
        if [ -f ${memoryReport}/proc-vmallocinfo ]; then
            sort -nrk 2 ${memoryReport}/proc-vmallocinfo | column -t 1>${memoryReport}/proc-vmallocinfo-sort
            awk '{print $3}' ${memoryReport}/proc-vmallocinfo | awk -F+ '{print $1}' | sort | uniq -c | sort -nr 1>${memoryReport}/proc-vmallocinfo-count
        fi
        # /sys/kernel/debug/extfrag/extfrag_index
        echo -e "Processing: Host - /sys/kernel/debug/extfrag/extfrag_index"
        cat /sys/kernel/debug/extfrag/extfrag_index 1>${memoryReport}/sys-kernel-debug-extfrag-extfrag_index 2>&1
        # Swap Report
        echo -e "Processing: Host - Swap Use"
        for smaps in /proc/*/smaps; do
            swapused=$(awk 'BEGIN { total = 0 } /^Swap:[[:blank:]]*[1-9]/ { total = total + $2 } END { print total }' ${smaps} 2>/dev/null || echo 0)
            if [[ -n ${swapused} && ${swapused} -gt 0 ]]; then
                pid=$(echo ${smaps} | awk -F'/' '{print $(NF-1)')
                processCMD=$(cat ${pid}/cmdline)
                echo -e "${swapused}k \t ${processCMD}"
            fi
        done 1>${memoryReport}/swap-process_list 2>/dev/null
        if [ -f ${memoryReport}/swap-process_list ]; then
            sort -nr ${memoryReport}/swap-process_list 1>${memoryReport}/swap-process_list-sort
        fi
        memTotalGB=$(grep "^MemTotal:" ${memoryReport}/proc-meminfo | awk '{sum=$2} END {print sum/1000/1000}')
        # Host Memory Host - NetBackup Software Summary
        if [ ${nbuHost} -eq 1 ]; then 
            echo -e "Processing: Host - Memory Use - NetBackup"
            grep "\/[o]penv" ${psOut} 1>${memoryReport}/Summary-netbackup-process-list
            if [ -f ${memoryReport}/Summary-netbackup-process-list ]; then
                awk '{print $11}' ${memoryReport}/Summary-netbackup-process-list | sort | uniq -c | sort -nr 1>${memoryReport}/Summary-netbackup-process-list-count
                nbuMemUseGB=$(awk -v OFMT='%.2f' '{total+=$6} END {print total / 1000 / 1000 }' ${memoryReport}/Summary-netbackup-process-list)
                nbuMemUsePct=$(echo "scale=2; ${nbuMemUseGB} / ${memTotalGB} * 100" | bc -l)
                echo -e "NetBackup - Memory Size: ${nbuMemUseGB} GB\nNetBackup - Memory Percent: ${nbuMemUsePct} %" 1>${memoryReport}/Summary-netbackup-process-memory-total
                echo -e "MemTotalGB=${memTotalGB}\nNetBackupMemUseGB=${nbuMemUseGB}\nNetBackupMemUsePct=${nbuMemUsePct}%" 1>${memoryReport}/Summary-netbackup-process-memory-summary
            fi
        fi
        # NetBackup Appliance - AutoSupport Summary
        if [ ${nbApp} -eq 1 ]; then 
            # AutoSupport - Report Values
            echo -e "Processing: Host - Memory Use - AutoSupport"
            grep "beam\|mongo\|tomcat-vxos\|alertmanager\|analyzer\|collector\|transmission\|callhome" ${psOut} | sort -nk5 1>${memoryReport}/Summary-autosupport-process_list
            grep "[c]ollector" ${psOut} 1>${memoryReport}/Summary-autosupport-process_list-collector
            awk '{print $11}' ${memoryReport}/Summary-autosupport-process_list-collector | sort | uniq -c | sort -nr 1>${memoryReport}/Summary-autosupport-process_list-collector-count
            # AutoSupport - Calculate Total
            asMemUseGB=$(awk '{total+=$6}END{print total / 1000 / 1000 }' OFMT="%.2f" ${memoryReport}/Summary-autosupport-process_list)
            asMemUsePct=$(echo "scale=2; ${asMemUseGB} / ${memTotalGB}" | bc -l)
            echo -e "AutoSupport - Memory Size: ${asMemUseGB} GB\nAutoSupport - Memory Percent: ${asMemUsePct} %" 1>${memoryReport}/Summary-autosupport-memory-total
            echo -e "MemTotalGB=${memTotalGB}\nAutoSupportMemUseGB=${asMemUseGB}\nAutoSupportMemUsePct=${asMemUsePct}" 1>${memoryReport}/Summary-autosupport-memory-summary
        fi
        # Process Level - Reports
        if [[ -f ${psOut} && -f ${memoryReport}/proc-meminfo ]]; then
            memDir=${memoryFile}/Memory-Process_Level_Data
            mkdir ${memDir}
            echo -e "\n\n${p2}\nMemory - Process Level Data\n${p2}"
            memValues=${memoryFile}/Memory-Process_Level-Total
            memSummary=${memoryFile}/Memory-Process_Level-Summary
            memSummarySortRSS=${memSummary}-Sort_RSS
            memSummarySortVSZ=${memSummary}-Sort_VSZ
            memSummarySortCount=${memSummary}-Sort_Count
            memReport=${memoryFile}/Memory-Process_Level
            memVeritas=${memReport}-Veritas
            memVeritasDetail=${memVeritas}-Detail
            memVeritasTotal=${memVeritas}-Total
            # Memory - Processes - Total/VSZ/RSS
            echo -e "${p3}\nMemory - Utilization - Total/RSS/VSZ\n${p3}"
            memTotal=$(grep "^MemTotal:" ${memoryReport}/proc-meminfo | awk '{print $2}')
            sed '1d' ${psOut} | awk -v memTotal=${memTotal} -v OFS=',' '{vsz +=$5; rss +=$6} END {print memTotal, rss, vsz }' 1>${memValues}.csv 2>/dev/null
            totalRSS=$(awk -F',' '{print $2}' ${memValues}.csv)
            totalVSZ=$(awk -F',' '{print $3}' ${memValues}.csv)
            echo -e "MemTotal,MemUsed_RSS,MemUsed_VSZ,\n$(cat ${memValues}.csv)" | column -t -s, 1>${memValues}.txt
            cat ${memValues}.txt
            cp ${memValues}.txt ${reportDir}
            # Memory - Processes - Summary - Count
            echo -e "\n${p3}\nMemory - Utilization - Process Summary\n${p3}"
            echo -e "${p4}\nProcessing\n${p4}"
            procList=$(grep "\/openv\|bpdm\s\|bptm\s\|bpbrm\s\|\/VRTS" ${psOut} | awk '{print $11}' | sort -u)
            for procName in ${procList}; do
                procNameShort=$(echo ${procName} | awk -F'/' '{print $NF}' | tr -d ',')
                echo -e "Processing: ${procNameShort}"
                procCount=$(grep -c "${procName}" ${psOut})
                if [ ${procCount} -gt 0 ]; then
                    procMem=$(grep "${procName}" ${psOut} | awk -v OFS=', ' -v CONVFMT='%3.3f' -v OFMT='%3f' -v procName=${procName} -v procNameShort=${procNameShort} -v procCount=${procCount} -v totalMem=${memTotal} -v totalVSZ=${totalVSZ} -v totalRSS=${totalRSS} '{vsz +=$5; rss +=$6} END {print 'procNameShort', 'procCount', rss / totalMem * 100 "%", rss / totalRSS * 100 "%", vsz / totalVSZ * 100 "%", rss / 1000000, vsz / 1000000, 'procName' }' 2>/dev/null)
                    echo -e "${procMem}" 1>>${memSummary}
                fi 
            done
            # Memory - Processes - Summary - Sort
            echo -e "\n\n${p2}\nMemory - Utilization - Summary\n${p2}"
            sort -nrk2 ${memSummary} 1>${memSummarySortCount}.csv
            sort -nrk6 ${memSummary} 1>${memSummarySortRSS}.csv
            sort -nrk7 ${memSummary} 1>${memSummarySortVSZ}.csv
            echo -e "Process, Count, %Mem, %RSS, %VSZ, RSS_GB, VSZ_GB, CMD\n$(cat ${memSummarySortCount}.csv)" | column -t -s, 1>${memSummarySortCount}.txt
            echo -e "Process, Count, %Mem, %RSS, %VSZ, RSS_GB, VSZ_GB, CMD\n$(cat ${memSummarySortRSS}.csv)" | column -t -s, 1>${memSummarySortRSS}.txt
            echo -e "Process, Count, %Mem, %RSS, %VSZ, RSS_GB, VSZ_GB, CMD\n$(cat ${memSummarySortVSZ}.csv)" | column -t -s, 1>${memSummarySortVSZ}.txt
            cat ${memSummarySortRSS}.txt 
            cp ${memSummarySortRSS}.txt ${reportDir}
            # Memory - Processes - Detail - Total
            echo -e "\n\n${p2}\nMemory - Utilization - Process Detail - Total\n${p2}"
            timeout -s 9 10 grep "\/openv\|bpdm\s\|bptm\s\|bpbrm\s\|\/VRTS" ${psOut} 1>${memVeritasTotal}-data
            procCount=$(awk '/./{c++} END {print c+0}' ${memVeritasTotal}-data)
            if [ ${procCount} -gt 0 ]; then
                echo -e "${p3}\nMemory - NetBackup - Total\n${p3}"
                grep "\/openv\|bpdm\s\|bptm\s\|bpbrm\s\|\/VRTS" ${psOut} | awk -v CONVFMT='%3.3f' -v OFMT='%3f'  -v procCount=${procCount} -v totalMem=${memTotal} -v totalVSZ=${totalVSZ} -v totalRSS=${totalRSS} -v p3=${p3} '{vsz +=$5; rss +=$6} END {print "Process_Count:", procCount, "\nProcess_%Mem: " rss / totalMem * 100 "%\n" p3, "\nPercent_RSS:", rss / totalRSS * 100 "%, ", rss / 1000000, "GB,", "\nPercent_VSZ: " vsz / totalVSZ* 100 "%, ", vsz / 1000000, "GB," }' 2>/dev/null
                echo -e "${p3}"
                grep "[C]OMMAND" ${psOut}
                grep "\/openv\|bpdm\s\|bptm\s\|bpbrm\s\|\/VRTS" ${psOut} | sort -nrk6
                echo -e ""
            fi 1>${memVeritasTotal}.txt
            cat ${memVeritasTotal}.txt | cut -c1-200
            cp ${memVeritasTotal}.txt ${reportDir}
            # Memory - Processes - Detail - Full
            echo -e "\n${p2}\nMemory - Utilization - Process Detail - Full\n${p2}"
            procList=$(awk -F',' '{print $NF}' ${memSummarySortRSS}.csv)
            for procName in ${procList}; do
                procNameShort=$(echo ${procName} | awk -F'/' '{print $NF}')
                procCount=$(grep -c "${procName}" ${psOut})
                if [ ${procCount} -gt 0 ]; then
                    echo -e "${p3}\nProcess: ${procNameShort}\n${p3}"
                    awk -v procName=${procName} '$11 == procName' ${psOut} | awk -v CONVFMT='%3.3f' -v OFMT='%3f' -v procCount=${procCount} -v totalMem=${memTotal} -v totalVSZ=${totalVSZ} -v totalRSS=${totalRSS} -v p3=${p3} '{vsz +=$5; rss +=$6} END {print "Process_Count:", procCount, "\nProcess_%Mem: " rss / totalMem * 100 "%\n" p3, "\nPercent_RSS:", rss / totalRSS * 100 "%, ", rss / 1000000, "GB, ", "\nPercent_VSZ: " vsz / totalVSZ* 100 "%, ", vsz / 1000000, "GB," }' 2>/dev/null
                    echo -e "${p3}"
                    grep "[C]OMMAND" ${psOut}
                    awk -v procName=${procName} '$11 == procName' ${psOut} | sort -nrk6
                    echo -e "\n"
                fi | tee -a ${memDir}/Memory-Process_Level-${procNameShort}
            done 1>${memVeritasDetail}.txt
            cat ${memVeritasDetail}.txt | cut -c1-200
            cp ${memVeritasDetail}.txt ${reportDir}
        fi | tee ${memoryFile}/Memory-Process_Level-Full_Report.txt
        cp ${memoryFile}/Memory-Process_Level-Full_Report.txt ${reportDir}
        memoryReportComplete=1
    fi
	logTime
}
# Operation: Report - Network
networkReport() {
    if [[ -n ${networkReportComplete} || ${networkReportComplete} -eq 1 ]]; then
        echo -e "\033[0;31m${p2}\nError - Duplicate Report\n${p2}\n"
        echo -e "Error: Network Report has already been executed.\033[0m\n"
    elif [[ -z ${networkReportComplete} || ${networkReportComplete} -eq 0 ]]; then
        echo -e "\n\n\n${p1}\nLHC - Processing - Report: Network\n${p1}"
        networkDir=${outputDir}/Network
        networkFile=${networkDir}/Network
        mkdir ${networkDir}
        echo -e "${p2}\nNetwork - State\n${p2}"
        # General
        echo -e "Processing: Network - route -n"
        timeout -s 9 10 /sbin/route -n 1>${networkDir}/route_-n 2>&1
        echo -e "Processing: Network - netstat -nr"
        timeout -s 9 10 /bin/netstat -nr 1>${networkDir}/netstat_nr 2>&1
        for cmdOpt in statistics interfaces; do
            echo -e "Processing: Network - netstat --${cmdOpt}"
            timeout -s 9 10 /bin/netstat --${cmdOpt} 1>${networkDir}/netstat_--${cmdOpt} 2>&1
        done
        timeout -s 9 10 column -t ${networkDir}/netstat_--interfaces 1>${networkDir}/netstat_--interfaces.txt
        timeout -s 9 10 grep "failed\|reset\|retransmit\|pruned\|collapsed\|Lost\|Timeout" ${networkDir}/netstat_--statistics 1>${networkDir}/netstat_--statistics-errors
        # ifconfig
        echo -e "Processing: Network - ifconfig -s"
        timeout -s 9 10 ifconfig | column -t 1>${networkDir}/ifconfig 2>&1
        echo -e "Processing: Network - ifconfig -s"
        timeout -s 9 10 ifconfig -s | column -t 1>${networkDir}/ifconfig_-s 2>&1
        # ip
        echo -e "Processing: Network - ip a"
        timeout -s 9 10 ip a 1>${networkDir}/ip_a 2>&1
        if [[ ${?} -eq 0 && -f ${networkDir}/ip_a ]]; then
            interfaceList=$(timeout -s 9 10 grep "^[0-9]" ${networkDir}/ip_a | awk '{print $2}' | tr -d ':')
            linkDir=${networkDir}/ip_link
            mkdir ${linkDir}
            for interfaceName in ${interfaceList}; do
                timeout -s 9 10 ip link show 1>${linkDir}/ip_link_show_${interfaceName} 2>&1
            done
        fi
        echo -e "Processing: Network - ip -s tcp_metrics"
        timeout -s 9 10 ip -s tcp_metrics 2>&1 | column -t 1>${networkDir}/ip_-s_tcp_metrics
        for cmdOpt in route neigh; do
            echo -e "Processing: Network - ip -s ${cmdOpt}"
            timeout -s 9 10 ip -s ${cmdOpt} 2>&1 | column -t 1>${networkDir}/ip_-s_${cmdOpt}
        done
        for cmdOpt in link maddress; do
            echo -e "Processing: Network - ip -s ${cmdOpt}"
            timeout -s 9 10 ip -s ${cmdOpt} 1>${networkDir}/ip_-s_${cmdOpt} 2>&1
        done
        # lsof -i
        echo -e "Processing: Network - lsof -i"
        timeout -s 9 60 /sbin/lsof -i 1>${networkDir}/lsof-i 2>&1
        # /proc/net/
        echo -e "Processing: Network - /proc/net/"
        timeout -s 9 15 cp -RL /proc/net/ ${networkDir} 2>/dev/null
        timeout -s 9 10 cat /proc/net/snmp | column -t 1>${networkDir}/net/snmp.txt
        # Socket Status
        echo -e "\n${p2}\nNetwork - Socket State\n${p2}"
        if [ -f /usr/sbin/ss ]; then
            for cmdOpt in s a i t u 4 6 m e o l; do 
                echo -e "Processing: Network - ss -${cmdOpt}"
                timeout -s 9 10 /usr/sbin/ss -${cmdOpt} 1>${networkDir}/ss-${cmdOpt} 2>&1
            done
        fi
        # ethtool
        echo -e "\n${p2}\nNetwork - Interfaces - ethtool\n${p2}"
        networkInterfaces=$(ls -1 /proc/sys/net/ipv4/conf/ | grep -v "all\|default\|lo\|bond\|veth\|enp\|autosupport\|docker\|podman\|br-\|mgmt0" | sort -uV | awk 'NF' | tr -s ' ')
        ethtoolDir=${networkDir}/ethtool
        mkdir ${ethtoolDir}
        echo -e "Interface: TX: Current Max RX: Current Max LRO: State" 1>${ethtoolDir}/ethtool-ring_buffer-summary
        for networkInterface in ${networkInterfaces}; do
            echo -e "${p3}\nInterface: ${networkInterface}\n${p3}"
            # ethtool
            echo -e "Processing: Network - ethtool ${networkInterface}"
            timeout -s 9 10 ethtool ${networkInterface} 1>${ethtoolDir}/ethtool_${networkInterface} 2>&1
            if [ ${?} -eq 0 ]; then
                grep "Link detected\|Duplex\|Speed\|Auto-negotiation" ${ethtoolDir}/ethtool_${networkInterface} 1>${ethtoolDir}/ethtool_${networkInterface}-parsed
                for cmdOpt in g i k l m n P S x; do
                    echo -e "Processing: Network - ethtool -${cmdOpt} ${networkInterface}"
                    timeout -s 9 10 ethtool -${cmdOpt} ${networkInterface} 1>${ethtoolDir}/ethtool_-${cmdOpt}-${networkInterface} 2>&1
                done
                echo -e ""
                grep "Link detected\|Duplex\|Speed\|Auto-negotiation" ${ethtoolDir}/ethtool_${networkInterface} 1>${ethtoolDir}/ethtool_${networkInterface}-parsed
                grep "Vendor\|Date\|Conn\|Transceiver type" ${ethtoolDir}/ethtool_-m-${networkInterface} 1>${ethtoolDir}/ethtool_-m-${networkInterface}-parsed
                # Summary
                echo -e "\n${p3}\n${networkInterface}\n${p3}" 1>>${ethtoolDir}/ethtool-summary-${networkInterface}.txt
                cat ${ethtoolDir}/ethtool_-m-${networkInterface}-parsed ${ethtoolDir}/ethtool_${networkInterface}-parsed 1>>${ethtoolDir}/ethtool-summary-${networkInterface}.txt
                # Ring Buffer
                currentLRO=$(timeout -s 9 10 grep large-receive-offload ${ethtoolDir}/ethtool_-k-${networkInterface} | awk '{print $2}');
                maxRX=$(timeout -s 9 10 grep "RX:" ${ethtoolDir}/ethtool_-g-${networkInterface} | head -n1 | awk '{print $NF}');
                maxTX=$(timeout -s 9 10 grep "TX:" ${ethtoolDir}/ethtool_-g-${networkInterface} | head -n1 | awk '{print $NF}');
                currentRX=$(timeout -s 9 10 grep "RX:" ${ethtoolDir}/ethtool_-g-${networkInterface} | tail -n1 | awk '{print $NF}');
                currentTX=$(timeout -s 9 10 grep "TX:" ${ethtoolDir}/ethtool_-g-${networkInterface} | tail -n1 | awk '{print $NF}');
                echo -e "${networkInterface} \t TX: ${currentTX} ${maxTX}  \t  RX: ${currentRX} ${maxRX} \t LRO: ${currentLRO}" 1>>${ethtoolDir}/ethtool-ring_buffer-summary
            fi
        done
        echo -e "\n${p2}\nNetwork - Interfaces - Ring Buffer Settings\n${p2}"
        column -t ${ethtoolDir}/ethtool-ring_buffer-summary 1>${ethtoolDir}/ethtool-ring_buffer-summary.txt
        cat ${ethtoolDir}/ethtool-ring_buffer-summary.txt
        echo ""
        # Network - Configuration Files - 
        echo -e "\n${p2}\nConfiguration Files\n${p2}"
        # /proc/net
        mkdir -p ${networkDir}/proc/net/bonding
        echo -e "Processing: Configuration - /proc/net/route" 
        timeout -s 9 10 cp /proc/net/route ${networkDir}/proc/net
        # Link Aggregation / Bonding
        configFiles=$(timeout -s 9 10 ls -1 /proc/net/bonding/* 2>/dev/null)
        if [ ${?} -eq 0 ]; then
            ls -l timeout -s 9 10 ls -1 /proc/net/bonding/* 1>${networkDir}/bonding-file_list.txt 2>&1
            for configFile in ${configFiles}; do
                echo -e "Processing: Configuration - ${configFile}"
                fileName=$(echo ${configFile} | awk -F'/' '{print $NF}')
                filePath=${networkDir}/proc/net/bonding/${fileName}
                timeout -s 9 10 cp ${configFile} ${filePath} 2>/dev/null
                namePattern=$(timeout -s 9 10 grep Interface ${filePath} | awk -F':' '{print $2}' | sed -e 's/[[:blank:]]//g;s/^\(.\{3\}\).*/\1/' | head -n1)
                if [ -n "${namePattern}" ]; then
                    echo -e "${p3}\n${fileName}\n${p3}" 1>${filePath}-link-report
                    timeout -s 9 10 echo -e "Interface, Speed Mbps, Duplex, FailureCount, Key, Priority, Number, State, Priority, Number, State" 1>>${filePath}-link-report
                    timeout -s 9 10 grep "Slave Interface:\|Speed:\|Duplex:\|Link Failure Count:\|port key:\|port priority:\|port number:\|port state:" ${filePath} | awk -F':' '{print $2}' | sed -z "s/\n/,  /g;s/${namePattern}/\n&/g" | awk 'NF' | sort -nk3 1>>${filePath}-link-report
                    timeout -s 9 10 column -t ${filePath}-link-report 1>${filePath}-link-report.txt
                    cp ${filePath}-link-report.txt ${reportDir}/Network-${fileName}-link-report.txt
                fi
                timeout -s 9 10 grep "Slave Interface:\|Speed:\|Duplex:\|Link Failure Count:\|port key:\|port priority:\|port number:\|port state:" ${filePath} | sed -z 's/[[:blank:]][[:blank:]]//g;s/\n/,  /g;s/Slave Interface/\n&/g' | awk 'NF' 1>${filePath}-link-report-alt.txt
            done
        fi
        # /usr/openv/netbackup/bp.conf
        if [ -f /usr/openv/netbackup/bp.conf ]; then
            configFiles=$(ls -1 /usr/openv/netbackup/bp.conf 2>/dev/null)
            ls -l ${configFiles} 1>>${networkDir}/network-file_list.txt
            for configFile in ${configFiles}; do
                echo -e "Processing: Configuration - ${configFile}" 
                timeout -s 9 10 cp ${configFile} ${networkDir} 2>/dev/null;
            done
        fi
        # /etc/sysconfig
        mkdir -p ${networkDir}/etc/sysconfig
        configFiles=$(ls -1 /etc/sysconfig/iptables /etc/sysconfig/samba /etc/sysconfig/docker-network /etc/sysconfig/authconfig /etc/sysconfig/clock /etc/sysconfig/nfs /etc/sysconfig/postfix /etc/sysconfig/kernel /etc/sysconfig/network /etc/sysconfig/static-routes 2>/dev/null) 
        ls -l ${configFiles} 1>>${networkDir}/network-file_list.txt
        for configFile in ${configFiles}; do
            echo -e "Processing: Configuration - ${configFile}" 
            timeout -s 9 10 cp ${configFile} ${networkDir}/etc/sysconfig 2>/dev/null;
        done
        # /etc/sysconfig/network-scripts
        mkdir -p ${networkDir}/etc/sysconfig/network-scripts
        configFiles=$(ls -1 /etc/sysconfig/network-scripts/ifcfg-* 2>/dev/null) 
        ls -l ${configFiles} 1>>${networkDir}/network-file_list.txt
        for configFile in ${configFiles}; do
            echo -e "Processing: Configuration - ${configFile}" 
            timeout -s 9 10 cp ${configFile} ${networkDir}/etc/sysconfig/network-scripts 2>/dev/null;
        done
        # /etc/
        configFiles=$(ls -1 /etc/hosts /etc/hostname /etc/resolv.conf /etc/nsswitch.conf /etc/sysctl.conf /etc/ntp.conf /etc/services 2>/dev/null)
        ls -l ${configFiles} 1>>${networkDir}/network-file_list.txt
        for configFile in ${configFiles}; do
            echo -e "Processing: Configuration - ${configFile}" 
            timeout -s 9 10 cp ${configFile} ${networkDir}/etc 2>/dev/null;
        done
        # Network - DNS - Domain Name Resolution
        echo -e "\n\n${p2}\nDNS - Domain Name Resolution\n${p2}"
        dnsServers=$(timeout -s 9 10 grep nameserver /etc/resolv.conf | awk '{print $2}')
        for dnsServer in ${dnsServers}; do 
            timeout -s 9 10 nc -w2 -z ${dnsServer} 53
            if [ ${?} -eq 0 ]; then
                echo -e "Processing: Network - DNS - Server Status: ${dnsServer}: ONLINE / OK"
                echo -e "DNS_Server: ${dnsServer}\nConnection: ESTABLISHED" 1>>${networkDir}/DNS-server-${dnsServer}
                echo -e "DNS_Server: ${dnsServer}\t\tConnection: ESTABLISHED" 1>>${networkDir}/DNS-server-status.txt
                echo -e "DNS_Server=${dnsServer}, Connection=ESTABLISHED" 1>>${networkDir}/DNS-server-status.cfg
            else
                echo -e "Processing: Network - DNS - Server Status: ${dnsServer}: OFFLINE / FAILED"
                echo -e "DNS_Server: ${dnsServer}\nConnection: FAILED" 1>>${networkDir}/DNS-server-${dnsServer}
                echo -e "DNS_Server: ${dnsServer}\t\tConnection: FAILED" 1>>${networkDir}/DNS-server-status.txt
                echo -e "DNS_Server=${dnsServer}, Connection=FAILED" 1>>${networkDir}/DNS-server-status.cfg
            fi
        done
        cp ${networkDir}/DNS-server-status.txt ${reportDir}
        # Network - DNS - Forward Lookup
        echo -e "Processing: Network - DNS - Forward Lookup - ${hostnameFull}"
        timeout -s 9 10 dig ${hostnameFull} 1>${networkDir}/DNS-forward_lookup-fqdn
        echo -e "Processing: Network - DNS - Forward Lookup - ${hostnameShort}"
        timeout -s 9 10 dig ${hostnameShort} 1>${networkDir}/DNS-forward_lookup-short
        echo -e "Processing: Network - DNS - Forward Lookup - ${hostnameShortForce}"
        timeout -s 9 10 dig ${hostnameShortForce} 1>${networkDir}/DNS-forward_lookup-short-force
        # Network - DNS - Reverse Lookup
        if [ -f ${networkDir}/ip_a ]; then
            interfaceIPs=$(timeout -s 9 10 grep "\sinet\s" ${networkDir}/ip_a | awk '{print $2}' | awk -F '/' '{print $1}' | grep -v "127.0.0.1\|192.168.229.233")
            for interfaceIP in ${interfaceIPs}; do 
                echo -e "Processing: Network - DNS - Reverse Lookup - ${interfaceIP}"
                timeout -s 9 10 dig -x ${interfaceIP} 1>${networkDir}/DNS-reverse_lookup-${interfaceIP} 2>/dev/null
                grep "PTR\|SOA\|Query\|SERVER" ${networkDir}/DNS-reverse_lookup-${interfaceIP} 1>${networkDir}/DNS-reverse_lookup-${interfaceIP}-parsed
            done
        fi
        networkReportComplete=1
    fi
	logTime
}
# Operation: Report - NetBackup - Initialization
nbuInit() {
    # Output
    nbuDir=${outputDir}/NetBackup_Software
    mkdir ${nbuDir}
    if [ ${?} -ne 0 ]; then echo -e "Error: Exiting. Failed to create folder(s): ${msdpDir}."; escape; fi
    nbuFile=${nbuDir}
    # Configuration
    nbuInitComplete=1
	logTime
}
# Operation: Report - NetBackup - Environment Report
nbuEnvironmentReport() {
    if [[ -n ${nbuEnvironmentReportComplete} || ${nbuEnvironmentReportComplete} -eq 1 ]]; then
        echo -e "\033[0;31m${p2}\nError - Duplicate Report\n${p2}\n"
        echo -e "Error: NetBackup Environment Report has already been executed.\033[0m\n"
    elif [[ -z ${nbuEnvironmentReportComplete} || ${nbuEnvironmentReportComplete} -eq 0 ]]; then
        echo -e "\n${p1}\nNetBackup Environment Report\n${p1}"
        if [[ ${nbuHost} -eq 1 ]]; then
            if [ -z ${nbuInitComplete} ]; then nbuInit; fi
            # Environment Report
            envOverview=${nbuFile}/NetBackup-Environment_Report.txt
            touch ${envOverview}
            if [[ -f ${envOverview} && -f /usr/openv/netbackup/bin/admincmd/nbdevquery ]]; then
                echo -e "${p3}\nHost Information\n${p3}"
                # 'bp.conf'
                cp /usr/openv/netbackup/bp.conf ${nbuFile}/configuration-bp.conf
                egrep 'MODE' ${nbuFile}/configuration-bp.conf 1>${nbuFile}/configuration-bp.conf-mode
                egrep 'EMM' ${nbuFile}/configuration-bp.conf 1>${nbuFile}/configuration-bp.conf-emm
                egrep 'SERVER' ${nbuFile}/configuration-bp.conf 1>${nbuFile}/configuration-bp.conf-server
                egrep 'VERBOSE' ${nbuFile}/configuration-bp.conf 1>${nbuFile}/configuration-bp.conf-verbose
                egrep 'MODE|EMM|SERVER|VERBOSE' ${nbuFile}/configuration-bp.conf 1>${nbuFile}/configuration-bp.conf-Summary
                cat ${nbuFile}/configuration-bp.conf-Summary
                # Primary Server
                primaryHostname=$(grep "^SERVER =" ${nbuFile}/configuration-bp.conf-server | head -n 1 | awk '{print $3}')
                # Domain Hosts
                echo -e "\n${p3}\nDomain Information\n${p3}\nTimeout: 30 seconds\n${p3}"
                timeout -s 9 30 /usr/openv/netbackup/bin/admincmd/nbemmcmd -getemm 1>${nbuFile}/nbemmcmd-getemm 2>&1
                if [ ${?} -eq 0 ]; then
                    primaryVersion=$(grep "^MASTER\s" ${nbuFile}/nbemmcmd-getemm | awk '{print $2}')
                    grep "^MEDIA\s" ${nbuFile}/nbemmcmd-getemm | awk '{print $2}' | sort -nr 1>${nbuFile}/nbemmcmd-getemm-version-media_servers
                    versionLatest=$(head -n1 ${nbuFile}/nbemmcmd-getemm-version-media_servers)
                    versionOldest=$(tail -n1 ${nbuFile}/nbemmcmd-getemm-version-media_servers)
                    mediaCount=$(awk '/./{c++} END {print c+0}' ${nbuFile}/nbemmcmd-getemm-version-media_servers)
                else
                    primaryVersion="Timeout"
                    versionLatest="Timeout"
                    versionOldest="Timeout"
                    mediaCount="Timeout"
                fi
                echo -e "Primary Server Version: ${primaryVersion}\nMedia Highest Version: ${versionLatest}\nMedia Lowest Version: ${versionOldest}\nMedia Server Count: ${mediaCount}"
                # Hostname & IP Address
                echo -e "\n${p3}\nLocal Host Information\n${p3}"
                echo -e "Local IP Address: ${hostnameIP}\nLocal Short Hostname: ${hostnameShort}\nLocal Full Hostname: ${hostnameFull}" | tee ${nbuFile}/hostname.txt
                # Version & Timestamp
                if [ ${nbuHost} -eq 1 ]; then
                    timeout -s 9 10 cp /usr/openv/netbackup/version ${nbuFile}/nbu-version
                    if [ ${?} -eq 0 ]; then
                        nbuVersion=$(timeout -s 9 5 awk '/VERSION/{gsub("VERSION ",""); print $0}' ${nbuFile}/nbu-version)
                        echo ${nbuVersion} 
                    else
                        echo "Error"
                    fi 1>${nbuFile}/nbu-version-release.txt
                    nbuVersionTimestamp=$(timeout -s 9 5 stat -c "%y" /usr/openv/netbackup/version)
                    if [ ${?} -eq 0 ]; then
                        echo ${nbuVersionTimestamp} 
                    else
                        echo "Error"
                    fi 1>${nbuFile}/nbu-version-release-timestamp.txt
                    echo -e "NetBackup Version: ${nbuVersion}\nUpgrade Timestamp: ${nbuVersionTimestamp}" | tee ${nbuFile}/nbu_version.txt
                fi
                # License Keys
                echo -e "\n${p3}\nLicense and Registration Keys\n${p3}"
                timeout -s 9 15 /usr/openv/netbackup/bin/admincmd/bpminlicense -verbose -list_keys 1>${nbuFile}/bpminlicense-verbose-list_keys
                if [ ${?} -ne 0 ]; then 
                    echo -e "Error: Failed to execute command: /usr/openv/netbackup/bin/admincmd/bpminlicense -verbose -list_keys" 1>>${nbuFile}/bpminlicense-verbose-list_keys
                else
                    grep "Expiration\|.*-.*-.*-.*-.*" ${nbuFile}/bpminlicense-verbose-list_keys 1>${nbuFile}/bpminlicense-verbose-list_keys-expiration
                    expiredKeys=$(awk '/Expired/{c++} END {print c+0}' ${nbuFile}/bpminlicense-verbose-list_keys)
                    if [ ${expiredKeys} -gt 0 ]; then
                        echo -e "WARNING: Found ${expiredKeys} expired license keys.\n" | tee ${nbuFile}/bpminlicense-verbose-list_keys-expired
                        grep -B1 "Expired" ${nbuFile}/bpminlicense-verbose-list_keys-expiration | tee -a ${nbuFile}/bpminlicense-verbose-list_keys-expired
                        echo -e "\n"
                    fi
                fi
                cat ${nbuFile}/bpminlicense-verbose-list_keys-expiration
                # Touch Files
                echo -e "\n${p3}\nTouch Files\n${p3}"
                timeout -s 9 10 /usr/openv/netbackup/bin/goodies/bpconverttouch -f 1>${nbuFile}/bpconverttouch-f 2>&1
                if [ ${?} -ne 0 ]; then echo -e "Error: Failed to execute command: /usr/openv/netbackup/bin/goodies/bpconverttouch -f" 1>>${nbuFile}/bpconverttouch-f; fi
                cat ${nbuFile}/bpconverttouch-f
                # Domain Status - DV / DP / STS
                echo -e "\n\n"
                domainStatus=${nbuFile}/NetBackup-Domain_Status.txt
                echo -e "${p1}\nNetBackup Domain Status (DV|DP|STS)\n${p1}" | tee ${domainStatus}
                startCmdTime=$(date +%s.%N)
                timeout -s 9 80 /usr/openv/netbackup/bin/admincmd/nbdevquery -liststs 1>${nbuFile}/nbdevquery-liststs 2>&1
                exitStatus=${?}
                endCmdTime=$(date +%s.%N)
                totalCmdTime=$(echo -e "${endCmdTime} - ${startCmdTime}" | bc -l)
                echo -e "${totalCmdTime}" 1>${nbuFile}/nbdevquery-liststs-runtime
                if [ ${exitStatus} -ne 0 ]; then
                    echo -e "Error: Failed to execute command: /usr/openv/netbackup/bin/admincmd/nbdevquery -liststs" | tee ${nbuFile}/nbdevquery-liststs.err
                else
                    stsTypes=$(awk '{print $3}' ${nbuFile}/nbdevquery-liststs | sort | uniq)
                    for stsType in ${stsTypes}; do 
                        echo -e "${p2}\n${stsType}\n${p2}"
                        echo -e "${p3}\nDisk Volumes\n${p3}"
                        timeout -s 9 20 /usr/openv/netbackup/bin/admincmd/nbdevquery -listdv -stype ${stsType} -U 1>${nbuFile}/nbdevquery-${stsType}-listdv
                        if [ ${?} -eq 0 ]; then
                            grep "^Disk Pool Name\|^Disk Volume Name\|^Disk Media ID\|^Status" ${nbuFile}/nbdevquery-${stsType}-listdv | cut -d: -f2 | awk '{ORS=NR % 4?", ": ",\n"; print}' | sed 's/ \{1,\}/ /g;s/^ //' 1>${nbuFile}/nbdevquery-${stsType}-listdv-parsed.csv
                            echo -e "Disk_Pool_Name, Disk_Volume_Name, Disk_Media_ID, Status,\n$(cat ${nbuFile}/nbdevquery-${stsType}-listdv-parsed.csv)" | column -t -s, 1>${nbuFile}/nbdevquery-${stsType}-listdv-parsed.txt
                            cat ${nbuFile}/nbdevquery-${stsType}-listdv-parsed.txt
                            sed 's/ //g' ${nbuFile}/nbdevquery-${stsType}-listdv-parsed.csv 2>/dev/null | column -J --table-columns 4 -N Disk_Pool_Name,Disk_Volume_Name,Disk_Media_ID,Status -n Disk_Volumes -s, 1>${nbuFile}/nbdevquery-${stsType}-listdv-parsed.json 2>/dev/null
                        else
                            echo -e "Error: Timeout" | tee ${nbuFile}/nbdevquery-${stsType}-listdv-parsed.txt
                        fi
                        echo -e "\n${p3}\nDisk Pools\n${p3}"
                        timeout -s 9 20 /usr/openv/netbackup/bin/admincmd/nbdevquery -listdp -stype ${stsType} -U 1>${nbuFile}/nbdevquery-${stsType}-listdp
                        if [ ${?} -eq 0 ]; then
                            grep "Disk Pool Name\|Status\|Max IO Streams" ${nbuFile}/nbdevquery-${stsType}-listdp | cut -d: -f2 | awk '{ORS=NR % 3?",": ",\n"; print}' | sed 's/ \{1,\}/ /g;s/^ //' 1>${nbuFile}/nbdevquery-${stsType}-listdp-parsed.csv
                            echo -e "Disk_Pool_Name, Status, Max_IO_Streams,\n$(cat ${nbuFile}/nbdevquery-${stsType}-listdp-parsed.csv)" | column -t -s, 1>${nbuFile}/nbdevquery-${stsType}-listdp-parsed.txt
                            cat ${nbuFile}/nbdevquery-${stsType}-listdp-parsed.txt
                            sed 's/ //g' ${nbuFile}/nbdevquery-${stsType}-listdp-parsed.csv 2>/dev/null | column -J --table-columns 3 -N Disk_Pool_Name,Status,Max_IO_Streams -n Disk_Pools -s, 1>${nbuFile}/nbdevquery-${stsType}-listdv-parsed.json 2>/dev/null
                        else
                            echo -e "Error: Timeout" | tee ${nbuFile}/nbdevquery-${stsType}-listdp-parsed.txt
                        fi
                        echo -e "\n${p3}\nStorage Servers\n${p3}"
                        timeout -s 9 80 /usr/openv/netbackup/bin/admincmd/nbdevquery -liststs -stype ${stsType} -U 1>${nbuFile}/nbdevquery-${stsType}-liststs
                        if [ ${?} -eq 0 ]; then
                            grep "Storage Server\|Storage Server Type\|State" ${nbuFile}/nbdevquery-${stsType}-liststs | cut -d: -f2 | awk '{ORS=NR % 3?",": ",\n"; print}' | sed 's/ \{1,\}/ /g;s/^ //' 1>${nbuFile}/nbdevquery-${stsType}-liststs-parsed.csv
                            echo -e "Storage_Server, Storage_Server_Type, State,\n$(cat ${nbuFile}/nbdevquery-${stsType}-liststs-parsed.csv)" | column -t -s, 1>${nbuFile}/nbdevquery-${stsType}-liststs-parsed.txt
                            cat ${nbuFile}/nbdevquery-${stsType}-liststs-parsed.txt
                            sed 's/ //g' ${nbuFile}/nbdevquery-${stsType}-liststs-parsed.csv 2>/dev/null | column -J --table-columns 3 -N Storage_Server,Storage_Server_Type,Status -n Storage_Servers -s, 1>${nbuFile}/nbdevquery-${stsType}-liststs-parsed.json 2>/dev/null
                            echo -e ""
                        else
                            echo -e "Error: Timeout\n" | tee ${nbuFile}/nbdevquery-${stsType}-liststs-parsed.txt
                        fi
                    done | tee -a ${domainStatus}
                    # Domain Status - STU
                    echo -e "${p2}\nStorage Units\n${p2}" | tee -a ${domainStatus}
                    timeout -s 9 20 /usr/openv/netbackup/bin/admincmd/bpstulist -U 1>${nbuFile}/bpstulist-U
                    if [ ${?} -eq 0 ]; then
                        grep "Label\|Concurrent\|Disk Pool" ${nbuFile}/bpstulist-U | grep "Disk Pool" -B2 | grep -v "\--" | cut -d: -f2 | awk '{ORS=NR % 3?",": ",\n"; print}' | sed 's/ \{1,\}/ /g;s/^ //' 1>${nbuFile}/bpstulist-U-parsed.csv
                        echo -e "Label, Concurrent_Jobs, Disk_Pool,\n$(cat ${nbuFile}/bpstulist-U-parsed.csv)" | column -t -s, 1>${nbuFile}/bpstulist-U-parsed.txt
                        cat ${nbuFile}/bpstulist-U-parsed.txt
                        sed 's/ //g' ${nbuFile}/bpstulist-U-parsed.csv 2>/dev/null | column -J --table-columns 3 -N Label,Concurrent_Jobs,Disk_Pool -n Storage_Units -s, 1>${nbuFile}/bpstulist-U-parsed.json 2>/dev/null
                    else
                        echo -e "Error: Timeout" | tee ${nbuFile}/bpstulist-U-parsed
                    fi | tee -a ${domainStatus}
                    # Domain Status - Servers
                    echo -e "\n${p2}\nServer Status\n${p2}" | tee -a ${domainStatus}
                    timeout -s 9 20 /usr/openv/volmgr/bin/vmoprcmd -devmon 1>${nbuFile}/vmoprcmd_devmon 2>&1
                    timeout -s 9 20 /usr/openv/volmgr/bin/vmoprcmd -devmon hs 1>${nbuFile}/vmoprcmd_devmon_-hs 2>&1
                    if [ ${?} -eq 0 ]; then
                        sed -e '1,/====/ d' ${nbuFile}/vmoprcmd_devmon_-hs | sed 's/ \{1,\}/, /g;s/^ //;s/$/,/' 1>${nbuFile}/vmoprcmd_devmon_-hs.csv
                        echo -e "Host_Name, Version, Host_Status,\n$(cat ${nbuFile}/vmoprcmd_devmon_-hs.csv)" | column -t -s, 1>${nbuFile}/vmoprcmd_devmon_-hs.txt
                        cat ${nbuFile}/vmoprcmd_devmon_-hs.txt | tee -a ${domainStatus}
                        sed 's/ //g' ${nbuFile}/vmoprcmd_devmon_-hs.csv 2>/dev/null | column -J --table-columns 3 -N Host_Name,Version,Host_Status -n Server_Status -s, 1>${nbuFile}/vmoprcmd_devmon_-hs.json 2>/dev/null
                    fi
                    cp ${domainStatus} ${reportDir}
                fi
                # nbcertcmd
                echo -e "\n\n${p2}\nNetBackup - Communication\n${p2}"
                if [ -f /usr/openv/netbackup/bin/nbcertcmd ]; then
                    echo -e "${p3}\nnbcertcmd -ping\n${p3}"
                    echo -e "Processing: nbcertcmd -ping"
                    startCmdTime=$(date +%s.%N)
                    timeout -s 9 20 /usr/openv/netbackup/bin/nbcertcmd -ping 1>${nbuFile}/nbcertcmd-ping 2>&1
                    exitStatus=${?}
                    endCmdTime=$(date +%s.%N)
                    totalCmdTime=$(echo -e "${endCmdTime} - ${startCmdTime}" | bc -l)
                    echo -e "${totalCmdTime}" 1>${nbuFile}/nbcertcmd-ping-runtime
                    cat ${nbuFile}/nbcertcmd-ping
                    if [ ${exitStatus} -ne 0 ]; then
                        echo ${exitStatus} > ${nbuFile}/nbcertcmd-ping.err
                    fi
                fi
            fi | tee -a ${envOverview} 2>/dev/null
            cp ${envOverview} ${reportDir}
            nbuEnvironmentReportComplete=1
        fi
    fi
	logTime
}
# Operation: Report - NetBackup - Configuration
nbuConfigurationReport() {
    if [[ -n ${nbuConfigurationReportComplete} || ${nbuConfigurationReportComplete} -eq 1 ]]; then
        echo -e "\033[0;31m${p2}\nError - Duplicate Report\n${p2}\n"
        echo -e "Error: NetBackup Configuration Report has already been executed.\033[0m\n"
    elif [[ -z ${nbuConfigurationReportComplete} || ${nbuConfigurationReportComplete} -eq 0 ]]; then
        echo -e "\n${p1}\nNetBackup Configuration Report\n${p1}"
        if [[ ${nbuHost} -eq 1 ]]; then
            if [ -z ${nbuInitComplete} ]; then nbuInit; fi
            # Version
            if [ -f /usr/openv/netbackup/version ]; then
                echo -e "${p2}\nNetBackup - Version\n${p2}"
                echo -e "Processing: NBU - Version"
                timeout -s 9 5 cp /usr/openv/netbackup/version ${nbuFile}/NBU-Version
                echo -e "\n"
            fi
            # EEBs
            if [ -f /usr/openv/pack/pack.summary ]; then
                echo -e "${p2}\nNetBackup - EEBs\n${p2}"
                echo -e "Processing: NBU - EEB List - pack.summary"
                timeout -s 9 5 cp /usr/openv/pack/pack.summary ${nbuFile}/NBU-EEBs
                echo -e "\n"
            fi
            # certmapinfo.json
            if [ -f /usr/openv/var/vxss/certmapinfo.json ]; then
                echo -e "${p2}\nNetBackup - Certificates\n${p2}"
                echo -e "Processing: NBU - Certificates - certmapinfo.json"
                timeout -s 9 10 cp /usr/openv/var/vxss/certmapinfo.json ${nbuFile}/configuration-certmapinfo.json
                echo -e "\n"
            fi
            # retention
            if [ -f /usr/openv/netbackup/bin/admincmd/bpretlevel ]; then
                echo -e "${p2}\nNetBackup - Retention\n${p2}"
                echo -e "Processing: NBU - Settings - Retention Level - bpretlevel -s"
                timeout -s 9 15 /usr/openv/netbackup/bin/admincmd/bpretlevel -s 1>${nbuFile}/settings-bpretlevel_-s 2>&1
                echo -e "Processing: NBU - Settings - Retention Level - bpretlevel -l"
                timeout -s 9 15 /usr/openv/netbackup/bin/admincmd/bpretlevel -l 1>${nbuFile}/settings-bpretlevel_-l 2>&1
                echo -e "\n"
            fi
            # bpstsinfo
            if [[ -f /usr/openv/netbackup/bin/admincmd/nbdevquery && /usr/openv/netbackup/bin/admincmd/bpstsinfo ]]; then
                echo -e "${p2}\nNetBackup - STS Information\n${p2}"
                echo -e "Processing: NBU - Communication - bpstsinfo"
                if [ -f ${nbuFile}/nbdevquery-liststs.err ]; then
                    nbuOffline=1
                    cat ${nbuFile}/nbdevquery-liststs.err
                else
                    if [ -f ${nbuFile}/nbdevquery-liststs ]; then
                        timeout -s 9 80 /usr/openv/netbackup/bin/admincmd/nbdevquery -liststs 1>${nbuFile}/nbdevquery-liststs 2>&1
                        nbuOffline=${?}
                    fi
                fi
                if [ ${nbuOffline} -eq 0 ]; then
                    while read stsVer stsName stsType stsClass; do
                        echo -e "Processing: NBU - Communication - bpstsinfo -lsuinfo -storage_server ${stsName} -stype ${stsType}" 
                        timeout -s 9 30 /usr/openv/netbackup/bin/admincmd/bpstsinfo -lsuinfo -storage_server ${stsName} -stype ${stsType} 1>${nbuFile}/bpstsinfo_-lsuinfo_-storage_server_${stsName}_-stype_${stsType} 2>&1
                        echo -e "Processing: NBU - Communication - bpstsinfo -plugininfo -storage_server ${stsName} -stype ${stsType}"
                        timeout -s 9 30 /usr/openv/netbackup/bin/admincmd/bpstsinfo -plugininfo -storage_server ${stsName} -stype ${stsType} 1>${nbuFile}/bpstsinfo_-plugininfo_-storage_server_${stsName}_-stype_${stsType} 2>&1
                    done <${nbuFile}/nbdevquery-liststs
                fi
            fi
            # STS Config - getconfig
            echo -e "\n${p2}\nNetBackup - STS Configuration\n${p2}"
            if [ ${nbuOffline} -eq 0 ]; then
                echo -e "${p3}\nnbdevconfig -getconfig\n${p3}"
                echo -e "Processing: nbdevconfig -getconfig"
                awk '{print $2, $3}' ${nbuFile}/nbdevquery-liststs | grep -v "AdvancedDisk\|BasicDisk" | \
                while read stsName stsType; do
                    echo -e "Processing: nbdevconfig -getconfig -storage_server ${stsName} -stype ${stsType}"
                    timeout -s 9 20 /usr/openv/netbackup/bin/admincmd/nbdevconfig -getconfig -storage_server ${stsName} -stype ${stsType} 1>${nbuFile}/nbdevconfig-getconfig-${stsName}-${stsType} 2>&1
                    if [ ${?} -gt 0 ]; then
                        echo -e "\nProcessing: Error: Command Failed: nbdevconfig -getconfig -storage_server ${stsName} -stype ${stsType}"
                    fi
                done
            else
                echo -e "\nError: Failed to get list of NetBackup Storage Servers."
            fi
        fi
        nbuConfigurationReportComplete=1
    fi
	logTime
}
# Operation: Report - NetBackup - SLP
nbuSLPReport() {
    if [[ -n ${nbuSLPReportComplete} || ${nbuSLPReportComplete} -eq 1 ]]; then
        echo -e "\033[0;31m${p2}\nError - Duplicate Report\n${p2}\n"
        echo -e "Error: NetBackup SLP Report has already been executed.\033[0m\n"
    elif [[ -z ${nbuSLPReportComplete} || ${nbuSLPReportComplete} -eq 0 ]]; then
        echo -e "\n${p1}\nNetBackup SLP Report\n${p1}"
        if [[ ${nbuHost} -eq 1 ]]; then
            if [ -z ${nbuInitComplete} ]; then nbuInit; fi
            slpDir=${nbuDir}/NetBackup-SLP_Report
            slpFile=${slpDir}/${sourceDate}-NetBackup-SLP_Report
            mkdir -p ${slpDir}/policy
            imgIncomplete=${slpFile}-Image_List
            imgIncompleteCSV=${imgIncomplete}-detail.csv
            echo -e "${p2}\nInitialization\n${p2}"
            echo -e "Processing: NetBackup - SLP Backlog - nbstlutil report - Timeout: 2 minutes"
            timeout -s 9 120 /usr/openv/netbackup/bin/admincmd/nbstlutil report 1>${slpFile}-Summary.txt 2>${slpFile}-Summary.err
            echo -e "Processing: NetBackup - SLP Backlog - nbstlutil stlilist -image_incomplete - Timeout: 2 minutes"
            timeout -s 9 120 /usr/openv/netbackup/bin/admincmd/nbstlutil stlilist -image_incomplete 1>${imgIncomplete} 2>${imgIncomplete}.err
            echo -e "\n\n${p2}\nProcessing\n${p2}"
            imgIncompleteCount=$(awk '/./{c++} END {print c+0}' ${imgIncomplete})
            if [ ${imgIncompleteCount} -eq 0 ]; then
                echo -e "Error: No images in output file: ${imgIncomplete}" | tee ${slpFile}-Error.txt
            elif [ ${imgIncompleteCount} -gt 0 ]; then
                echo -e "Processing: Making CSV File"
                awk -v OFS=', ' '$2=="I" {ctime=$3; sub(/.*_/, "", ctime); date=strftime("%Y-%m-%d, %H:%M:%S", ctime); print date, ctime, $3, $4}' ${imgIncomplete} 1>${imgIncompleteCSV}
                # Make Policy List
                echo -e "Processing: Making Policy List"
                awk -F, '{print $NF}' ${imgIncompleteCSV} | sort -u 1>${slpFile}-Policy_List
                # Make Policy Reports
                echo -e "\n\n"
                echo -e "${p2}\nPolicy Summary\n${p2}" | tee ${slpFile}-Policy_Summary.txt
                while read slpName; do
                    policyFile=${slpDir}/policy/${sourceDate}-NetBackup-SLP_Report-Image_List-detail-${slpName}.csv
                    grep "${slpName}" ${imgIncompleteCSV} > ${policyFile}
                    policyImageCount=$(awk '/./{c++} END {print c+0}' ${policyFile})
                    echo -e "\n${p3}\n${slpName}\n${p3}\nTotal: ${policyImageCount}\n${p3}"
                    head ${policyFile}
                    echo -e "---"
                    tail ${policyFile}
                done <${slpFile}-Policy_List | tee -a ${slpFile}-Policy_Summary.txt
            fi
            nbuSLPReportComplete=1
        fi
    fi
	logTime
}
# Operation: Report - Appliance - NetBackup
nbuApplianceReport() {
    if [[ -n ${nbuApplianceReportComplete} || ${nbuApplianceReportComplete} -eq 1 ]]; then
        echo -e "\033[0;31m${p2}\nError - Duplicate Report\n${p2}\n"
        echo -e "Error: NBU Appliance Report has already been executed.\033[0m\n"
    elif [[ -z ${nbuApplianceReportComplete} || ${nbuApplianceReportComplete} -eq 0 ]]; then
        echo -e "\n\n${p1}\nNetBackup Appliance Report\n${p1}"
        nbuaDir=${outputDir}/NetBackup_Appliance
        nbuaFile=${nbuaDir}/NetBackup_Appliance
        mkdir ${nbuaDir}
        echo -e "${p2}\nHost Status\n${p2}" 
        echo -e "Processing: NetBackup Appliance - Host - File System - Checkpoints"
        timeout -s 9 30 /opt/NBUAppliance/scripts/checkpoint.pl --skipxhost -listcheckpoints 1>${nbuaFile}-file_system-checkpoints
        echo -e "Processing: NetBackup Appliance - Host - Test Hardware"
        timeout -s 9 30 /opt/autosupport/scripts/asc_monitor.py --node localhost --loglevel info --object all --item all 1>${nbuaFile}-test_hardware
        echo -e "Processing: NetBackup Appliance - Host - Test Hardware - Errors"
        timeout -s 9 30 /opt/autosupport/scripts/asc_monitor.py --node localhost --loglevel info --object all --item all --showErrors True 1>${nbuaFile}-test_hardware-errors
        echo -e "\n${p2}\nConfiguration\n${p2}" 
        echo -e "Processing: NetBackup Appliance - Configuration - IPSec"
        if [ -r /etc/racoon/setkey.conf ]; then
            echo -e "IPSec Enabled.\n" 1>>${nbuaFile}-ipsec-state;
            cp /etc/racoon/setkey.conf ${nbuaFile}-ipsec-racoon-setkey.conf;
        else
            echo -e "IPSec Disabled.\n" 1>>${nbuaFile}-ipsec-state; 
        fi
        timeout -s 9 30 /opt/NBUAppliance/scripts/ipsec/ipsec_utils.pl -s 1>>${nbuaFile}-ipsec 2>&1
        echo -e "Processing: NetBackup Appliance - Configuration - LDAP"
        timeout -s 9 30 /opt/NBUAppliance/scripts/security/user_management.pl -list --ldap 1>${nbuaFile}-authentication-ldap 2>&1
        echo -e "Processing: NetBackup Appliance - Configuration - Active Directory"
        timeout -s 9 30 /opt/NBUAppliance/scripts/security/user_management.pl -list --activedirectory 1>${nbuaFile}-authentication-activedirectory 2>&1
        echo -e "Processing: NetBackup Appliance - Configuration - Kerberos"
        timeout -s 9 30 /opt/NBUAppliance/scripts/security/user_management.pl -list --kerberos 1>${nbuaFile}-authentication-kerberos 2>&1
        echo -e "Processing: NetBackup Appliance - Configuration - iSCSI - Targets"
        timeout -s 9 30 /opt/NBUAppliance/clients/iscsi/scripts/iscsi.py target --show all 1>${nbuaFile}-iscsi-target 2>&1
        echo -e "Processing: NetBackup Appliance - Configuration - iSCSI - Initiators"
        timeout -s 9 30 /opt/NBUAppliance/clients/iscsi/scripts/iscsi.py iqn show 1>${nbuaFile}-iscsi-initiator 2>&1
        echo -e "Processing: NetBackup Appliance - Configuration - FC HBAs - Timeout: 1 minute"
        timeout -s 9 60 /opt/NBUAppliance/scripts/fc_hba_config.pl --report 1>${nbuaFile}-fc-hba_config_report 2>&1
        echo -e "\n${p2}\nPlatform\n${p2}"
        echo -e "Processing: NetBackup Appliance - Platform - Model"
        nbaModel=$(timeout -s 9 15 /opt/IMAppliance/platform/bin/platform model 2>/dev/null)
        echo -e "Processing: NetBackup Appliance - Platform - Motherboard"
        nbaMotherboard=$(timeout -s 9 15 /opt/IMAppliance/platform/bin/platform baseboard 2>/dev/null)
        echo -e "Processing: NetBackup Appliance - Platform - IO Model"
        nbaIOModel=$(timeout -s 9 15 /opt/IMAppliance/platform/bin/platform io-model 2>/dev/null)
        echo -e "Appliance_Model: ${nbaModel}" 1>${nbuaFile}-platform-model
        echo -e "Motherboard_Model: ${nbaMotherboard}" 1>${nbuaFile}-platform-motherboard
        echo -e "I/O_Configuration: ${nbaIOModel}" 1>${nbuaFile}-platform-io_model
        echo -e "Appliance_Model: ${nbaModel}\nMotherboard_Model: ${nbaMotherboard}\nI/O_Configuration: ${nbaIOModel}" | column -t 1>${nbuaFile}-platform-summary.txt
        echo -e "Processing: NetBackup Appliance - Platform - Version"
        timeout -s 9 15 /opt/NBUAppliance/scripts/patch.pl --showvers 1>${nbuaFile}-platform-version 2>&1
        cat ${nbuaFile}-platform-version 1>>${nbuaFile}-platform-summary.txt
        cp ${nbuaFile}-platform-summary.txt ${reportDir}
        echo -e "Processing: NetBackup Appliance - Platform - Install Timestamp"
        timeout -s 9 15 /opt/NBUAppliance/scripts/patch.pl --showappverdetails 1>${nbuaFile}-platform-timestamp 2>&1
        echo -e "Processing: NetBackup Appliance - Platform - PCI Devices"
        timeout -s 9 30 /opt/IMAppliance/platform/bin/platform pci 1>${nbuaFile}-platform-PCIe_Adapters 2>&1
        echo -e "Processing: NetBackup Appliance - Platform - EEBs"
        timeout -s 9 30 /opt/NBUAppliance/scripts/patch.pl --list=eebs 1>${nbuaFile}-platform-EEBs 2>&1
        echo -e "Processing: NetBackup Appliance - Platform - CallHome Settings"
        timeout -s 9 30 /opt/autosupport/legacy/scripts/hwmon/callhome_setup.pl --showsettings --callhomeproxy 1>${nbuaFile}-callhome-settings 2>&1
        nbuApplianceReportComplete=1
    fi
	logTime
}
# Operation: Report - Containers
containerReport() {
    if [[ -n ${containerReportComplete} || ${containerReportComplete} -eq 1 ]]; then
        echo -e "\033[0;31m${p2}\nError - Duplicate Report\n${p2}\n"
        echo -e "Error: Container Report has already been executed.\033[0m\n"
    elif [[ -z ${containerReportComplete} || ${containerReportComplete} -eq 0 ]]; then
        echo -e "\n\n${p1}\nContainer Report\n${p1}"
        ctDir=${outputDir}/Containers
        ctFile=${ctDir}
        mkdir ${ctDir}
        # overview
        echo -e "${p2}\nContainers\n${p2}"
        timeout -s 9 30 docker ps 1>${ctFile}/docker_ps 2>&1 
        if [ ${?} -ne 0 ]; then echo -e "Error: Failed executing 'docker ps' command." | tee ${ctFile}/docker_ps.err; return; else cat ${ctFile}/docker_ps; fi
        echo -e "\n${p2}\nSize\n${p2}"
        timeout -s 9 30 docker ps --size 2>&1 | tee ${ctFile}/docker_ps_--size
        echo -e "\n${p2}\nStatistics\n${p2}"
        timeout -s 9 30 docker stats --no-stream 2>&1 | tee ${ctFile}/docker_stats
        echo -e "\n${p2}\nStorage Volumes\n${p2}"
        timeout -s 9 30 docker volume ls 2>&1 | tee ${ctFile}/docker_volume_ls
        echo -e "\n${p2}\nNetwork\n${p2}"
        timeout -s 9 30 docker network ls 2>&1 | tee ${ctFile}/docker_network_ls
        # processing
        echo -e "\n${p2}\nProcessing\n${p2}"
        echo -e "Processing: Container: docker ps -q"
        timeout -s 9 20 docker ps -q 1>${ctFile}/docker_ps_-q 2>${ctFile}/docker_ps_-q.err
        # list
        while read containerID containerImage; do
            containerHostname=$(timeout -s 9 10 docker inspect -f '{{.Config.Hostname}}' ${containerID})
            containerImage=$(timeout -s 9 10 docker inspect -f '{{.Config.Image}}' ${containerID})
            containerImageString=$(echo "${containerImage}" | sed 's/\(\/\|\:\)/-/g')
            echo -e "${containerID} ${containerHostname} ${containerImage} ${containerImageString}" 1>>${ctFile}/container-list
            echo -e "${containerID}, ${containerHostname}, ${containerImage}, ${containerImageString}" 1>>${ctFile}/container-list.csv
        done <${ctFile}/docker_ps_-q
        timeout -s 9 10 awk '/netbackup/' ${ctFile}/container-list 1>${ctFile}/container-list-netbackup
        timeout -s 9 10 awk '/uss-engine/' ${ctFile}/container-list 1>${ctFile}/container-list-msdp
        # inspect
        while read containerID containerHostname containerImage containerImageString; do
            echo -e "Processing: Container: docker inspect ${containerID} - ${containerImageString} - ${containerHostname}"
            timeout -s 9 20 docker inspect ${containerID} 1>${ctFile}/docker_inspect_${containerImageString}_${containerID}_${containerHostname} 2>&1
        done <${ctFile}/container-list
        # top
        while read containerID containerHostname containerImage containerImageString; do
            echo -e "Processing: Container: docker top ${containerID} - ${containerImageString} - ${containerHostname}"
            timeout -s 9 20 docker top ${containerID} 1>${ctFile}/docker_top_${containerImageString}_${containerID}_${containerHostname} 2>&1
        done <${ctFile}/container-list
        # volumes
        echo -e "\n${p3}\nStorage Volumes\n${p3}"
        awk '!/VOLUME NAME/' ${ctFile}/docker_volume_ls | while read volumeDriver volumeName; do
            echo -e "Processing: Volume: docker volume inspect ${volumeName}"
            timeout -s 9 20 docker volume inspect ${volumeName} 1>${ctFile}/docker_volume_inspect_${volumeDriver}_${volumeName} 2>&1
        done
        # network
        echo -e "\n${p2}\nNetwork\n${p2}"
        awk '!/NETWORK ID/' ${ctFile}/docker_network_ls | while read networkID networkName networkDriver networkScope; do
            echo -e "Processing: Volume: docker network inspect ${networkName}"
            timeout -s 9 20 docker network inspect ${networkName} 1>${ctFile}/docker_network_inspect_${networkScope}_${networkDriver}_${networkName}_${networkID} 2>&1
        done
        # general
        echo -e "\n${p2}\nGeneral\n${p2}"
        echo -e "Processing: General: docker images"
        timeout -s 9 20 docker images 1>${ctFile}/docker_images 2>&1
        echo -e "Processing: General: docker info"
        timeout -s 9 20 docker info 1>${ctFile}/docker_info 2>&1
        # netbackup
        while read containerID containerHostname containerImage containerImageString; do
            ctOut=${ctFile}/${containerImageString}-${containerHostname}
            mkdir ${ctOut}
            echo -e "Processing: ${containerID}: NetBackup: version"
            timeout -s 9 10 docker exec ${containerID} cat /usr/openv/netbackup/version 1>${ctOut}/version
            echo -e "Processing: ${containerID}: NetBackup: bp.conf"
            timeout -s 9 10 docker exec ${containerID} cat /usr/openv/netbackup/bp.conf 1>${ctOut}/bp.conf
        done <${ctFile}/container-list-netbackup
        # msdp
        while read containerID containerHostname containerImage containerImageString; do
            ctOut=${ctFile}/${containerImageString}-${containerHostname}
            mkdir ${ctOut}
            # state
            echo -e "Processing: ${containerID}: MSDP: crcontrol --getmode"
            timeout -s 9 15 docker exec ${containerID} /usr/openv/pdde/pdcr/bin/crcontrol --getmode 1>${ctOut}/crcontrol_--getmode
            echo -e "Processing: ${containerID}: MSDP: crcontrol --dsstat"
            timeout -s 9 15 docker exec ${containerID} /usr/openv/pdde/pdcr/bin/crcontrol --dsstat 1>${ctOut}/crcontrol_--dsstat
            echo -e "Processing: ${containerID}: MSDP: crcontrol --taskstat"
            timeout -s 9 15 docker exec ${containerID} /usr/openv/pdde/pdcr/bin/crcontrol --taskstat 1>${ctOut}/crcontrol_--taskstat
            # test
            echo -e "Processing: ${containerID}: MSDP: spad --test"
            timeout -s 9 15 docker exec ${containerID} /usr/openv/pdde/pdcr/bin/spad --test 1>${ctOut}/test-spad 2>&1
            echo -e "Processing: ${containerID}: MSDP: spoold --test"
            timeout -s 9 15 docker exec ${containerID} /usr/openv/pdde/pdcr/bin/spoold --test 1>${ctOut}/test-spoold 2>&1
            # version
            echo -e "Processing: ${containerID}: MSDP: spad --version"
            timeout -s 9 15 docker exec ${containerID} /usr/openv/pdde/pdcr/bin/spad --version 1>${ctOut}/version-spad 2>&1
            echo -e "Processing: ${containerID}: MSDP: spoold --version"
            timeout -s 9 15 docker exec ${containerID} /usr/openv/pdde/pdcr/bin/spoold --version 1>${ctOut}/version-spoold 2>&1
            echo -e "Processing: ${containerID}: MSDP: crcontrol --version"
            timeout -s 9 15 docker exec ${containerID} /usr/openv/pdde/pdcr/bin/crcontrol --version 1>${ctOut}/version-crcontrol 2>&1
            # config
            pdregistryLink=$(timeout -s 9 10 docker exec ${containerID} stat -c '%N' /etc/pdregistry.cfg | sed "s/\('\|‘\|’\)//g")
            pdregistryCfg=$(echo -e "${pdregistryLink}" | awk '{print $NF}')
            spaCfg=$(timeout -s 9 10 docker exec ${containerID} awk -F'=' '/spa.cfg/{print $2}' /etc/pdregistry.cfg)
            crCfg=$(timeout -s 9 10 docker exec ${containerID} awk -F'=' '/contentrouter.cfg/{print $2}' /etc/pdregistry.cfg)
            agentCfg=$(timeout -s 9 10 docker exec ${containerID} awk -F'=' '/agent.cfg/{print $2}' /etc/pdregistry.cfg)
            spwsCfg=$(timeout -s 9 10 docker exec ${containerID} awk -F'=' '/spws.cfg/{print $2}' /etc/pdregistry.cfg)
            echo -e "Processing: ${containerID}: MSDP: Configuration: ${pdregistryCfg}"
            timeout -s 9 10 docker exec ${containerID} cat ${pdregistryCfg} 1>${ctOut}/configuration-pdregistry.cfg
            echo -e "Processing: ${containerID}: MSDP: Configuration: ${spaCfg}"
            timeout -s 9 10 docker exec ${containerID} cat ${spaCfg} 1>${ctOut}/configuration-spa.cfg
            echo -e "Processing: ${containerID}: MSDP: Configuration: ${crCfg}"
            timeout -s 9 10 docker exec ${containerID} cat ${crCfg} 1>${ctOut}/configuration-contentrouter.cfg
            echo -e "Processing: ${containerID}: MSDP: Configuration: ${agentCfg}"
            timeout -s 9 10 docker exec ${containerID} cat ${agentCfg} 1>${ctOut}/configuration-agent.cfg
            echo -e "Processing: ${containerID}: MSDP: Configuration: ${spwsCfg}"
            timeout -s 9 10 docker exec ${containerID} cat ${spwsCfg} 1>${ctOut}/configuration-spws.cfg
        done <${ctFile}/container-list-msdp
        containerReportComplete=1
    fi
    logTime
}
# Operation: Report - Appliance - Flex
flexApplianceReport() {
    if [[ -n ${flexApplianceReportComplete} || ${flexApplianceReportComplete} -eq 1 ]]; then
        echo -e "\033[0;31m${p2}\nError - Duplicate Report\n${p2}\n"
        echo -e "Error: Flex Appliance Report has already been executed.\033[0m\n"
    elif [[ -z ${flexApplianceReportComplete} || ${flexApplianceReportComplete} -eq 0 ]]; then
        echo -e "\n\n${p1}\nFlex Appliance\n${p1}"
        flexDir=${outputDir}/Flex
        flexFile=${flexDir}
        mkdir ${flexDir}
        # Lockdown Mode
        echo -e "${p2}\nConfiguration\n${p2}"
        echo -e "Processing: Check 'lockdown' mode"
        timeout -s 9 20 /opt/veritas/flex/tools/get-lockdown-mode 1>${flexFile}/security-lockdown_mode.json 2>&1
        echo -e "Processing: Check 'platform-config'"
        timeout -s 9 20 cat /etc/opt/veritas/flex/platform-config.json 1>${flexFile}/security-lockdown_mode.json 2>&1
        flexApplianceReportComplete=1
    fi
	logTime
}
# Operation: Report - Appliance - NBFS
nbfsApplianceReport() {
    if [[ -n ${nbfsApplianceReportComplete} || ${nbfsApplianceReportComplete} -eq 1 ]]; then
        echo -e "\033[0;31m${p2}\nError - Duplicate Report\n${p2}\n"
        echo -e "Error: NBFS Appliance Report has already been executed.\033[0m\n"
    elif [[ -z ${nbfsApplianceReportComplete} || ${nbfsApplianceReportComplete} -eq 0 ]]; then
        if [ ${nbfsApp} -eq 0 ]; then
            echo -e "Error: Host is not a NBFS system."
            redirect
        elif [ ${nbfsApp} -eq 1 ]; then
            echo -e "\n\n${p1}\nNBFS - Flex Scale Appliance\n${p1}"
            nbfsDir=${outputDir}/NBFS
            nbfsFile=${nbfsDir}
            mkdir ${nbfsDir}
            # Upgrade Logs
            echo -e "\n${p2}\nUpgrade Logs\n${p2}"
            timeout -s 9 60 find /log -type f -name 'upgrade_failure_*.tar.gz' -type f 1>${nbfsFile}/upgrade_logs-failures-list
            timeout -s 9 60 find /log -type f -name 'upgrade_failure_*.tar.gz' -type f -mtime 30 1>${nbfsFile}/upgrade_logs-failures-recent
            timeout -s 9 10 wc -l ${nbfsFile}/upgrade_logs-failures-list ${nbfsFile}/upgrade_logs-failures-recent
            nbfsApplianceReportComplete=1
        fi
    fi
	logTime
}
# Operation: Report - Appliance - IPMI / System Event Log
ipmiApplianceReport() {
    if [[ -n ${ipmiApplianceReportComplete} || ${ipmiApplianceReportComplete} -eq 1 ]]; then
        echo -e "\033[0;31m${p2}\nError - Duplicate Report\n${p2}\n"
        echo -e "Error: Storage Report has already been executed.\033[0m\n"
    elif [[ -z ${ipmiApplianceReportComplete} || ${ipmiApplianceReportComplete} -eq 0 ]]; then
        echo -e "\n\n${p1}\nIPMI - System Event Log\n${p1}"
        ipmiDir=${outputDir}/IPMI
        ipmiFile=${ipmiDir}/IPMI
        mkdir ${ipmiDir}
        cd ${ipmiDir}
        # Get sysinfo
        echo -e "${p2}\nData Collection - Sysinfo\n${p2}"
        if [ -f /usr/bin/sysinfo/sysinfo ]; then
            echo -e "Processing: Collecting 'sysinfo' - Timeout: 4 minutes"
            timeout -s 9 240 /usr/bin/sysinfo/sysinfo -ni 2>${ipmiFile}-sysinfo-ni-err.txt
        else
            echo -e "Error: Missing binary: /opt/PDOS/install/syscfg" | tee -a ${ipmiFile}-sysinfo-ni-err.txt
        fi
        # Get bmc debug
        echo -e "\n\n${p2}\nData Collection - BMC Debug\n${p2}"
        if [ -f /opt/PDOS/install/syscfg ]; then
            echo -e "\nProcessing: Collecting 'bmc debug' - Timeout: 4 minutes"
            timeout -s 9 240 /opt/PDOS/install/syscfg /sbmcdl public bmc_debug.zip 2>&1 | tee ${ipmiFile}-syscfg-sbmcdl-public.txt
        else
            echo -e "Error: Missing binary: /opt/PDOS/install/syscfg" 1>${ipmiFile}-syscfg-sbmcdl-public.txt
        fi
        # Get BIOS Report version
        echo -e "\n\n${p2}\nData Collection - BIOS Report Version\n${p2}"
        if [ -f /usr/bin/syscfg/syscfg ]; then
            timeout -s 9 20 /usr/bin/syscfg/syscfg /i 2>&1 | tee ${ipmiFile}-syscfg-bios
        else
            echo -e "Error: Missing binary: /usr/bin/syscfg/syscfg" | tee ${ipmiFile}-syscfg-bios
        fi
        if [ -f /usr/bin/ipmitool ]; then
            echo -e "\n\n${p2}\nData Collection - IPMI Tool\n${p2}"
            # Check Service IP
            echo -e "Processing: IPMI - ipmitool lan print 3"
            timeout -s 9 10 /usr/bin/ipmitool lan print 3 1>${ipmiFile}-ipmitool-lan-print-3 2>/dev/null 
            # Check User List
            echo -e "Processing: IPMI - ipmitool user list 3"
            timeout -s 9 10 /usr/bin/ipmitool user list 3 1>${ipmiFile}-ipmitool-user-list-3 2>/dev/null 
            # Check SDR elist
            echo -e "Processing: IPMI - ipmitool sdr elist"
            timeout -s 9 30 /usr/bin/ipmitool sdr elist 1>${ipmiFile}-ipmitool-sdr-elist 2>/dev/null 
            echo -e "Processing: IPMI - ipmitool sdr elist all"
            timeout -s 9 30 /usr/bin/ipmitool sdr elist all 1>${ipmiFile}-ipmitool-sdr-elist-all 2>/dev/null 
            echo -e "Processing: IPMI - ipmitool sdr elist event"
            timeout -s 9 30 /usr/bin/ipmitool sdr elist event 1>${ipmiFile}-ipmitool-sdr-elist-event 2>/dev/null 
        fi
        # Post Procesing
        if [ ! -d ${ipmiDir}/LogFiles ]; then
            mkdir ${ipmiDir}/LogFiles 2>/dev/null;
        fi
        selSize=$(du -x ${ipmiDir}/LogFiles | awk '{print $1}')
        if [ ${selSize} -gt 10 ]; then
            echo -e "\n\n${p1}\nIPMI - Memory Report\n${p1}"
            echo -e "${p2}\nMemory Error Check\n${p2}"
            grep -i " ECC\| Err\|POST Err" LogFiles/sysinfo_log.txt 2>/dev/null | awk '{$1=""; print $0}' | awk -F":" '{$2=$3=""; print $0 }' | sort | uniq -c | grep Channel 1>${ipmiFile}-sysinfo-memory_messages
            msgCount=$(timeout -s 9 10 awk '/./{c++} END {print c+0}' ${ipmiFile}-sysinfo-memory_messages)
            echo -e "Count: ${msgCount}"
            if [ ${msgCount} -eq 0 ]; then
                echo -e "Info: No memory error messages"
            else
                tail -n 20 ${ipmiFile}-sysinfo-memory_messages
            fi
            echo -e "\n\n${p2}\nMemory Layout\n${p2}"
            grep DIMM_ -A2 LogFiles/sysinfo_log.txt 2>/dev/null | grep -v "Slot\|==\|--\|\/20" | awk '{ORS=NR % 2? "    ": "\n"; print}' | awk 'NF' | tee ${ipmiFile}-sysinfo-memory_layout
            echo -e "\n\n${p2}\nMemory Information\n${p2}"
            grep "Slot:\|MemoryType:\|SerialNo:\|Manufacturer:\|PartNumber:\|Size:" LogFiles/sysinfo_log.txt 2>/dev/null | awk '{ORS=NR % 6? " ": "\n"; print}' | sed -e 's/\t/ /g' | column -t | tee ${ipmiFile}-sysinfo-memory_info
        else
            echo -e "\nError: IPMI System Event Log not collected.  Retry execution: /usr/bin/sysinfo/sysinfo -ni\n"
        fi | tee ${ipmiFile}-Memory_Report
        cp ${ipmiFile}-Memory_Report ${reportDir}
        ipmiApplianceReportComplete=1
    fi
	logTime
}
# Operation: Report - Appliance - VCS
vcsApplianceReport() {
    if [[ -n ${vcsReportComplete} || ${vcsReportComplete} -eq 1 ]]; then
        echo -e "\033[0;31m${p2}\nError - Duplicate Report\n${p2}\n"
        echo -e "Error: VCS Report has already been executed.\033[0m\n"
    elif [[ -z ${vcsReportComplete} ]]; then
        echo -e "\n\n${p1}\nVCS - Veritas Cluster Server\n${p1}"
        if [ ! -f /opt/VRTS/bin/hasys ]; then
            vcsState=9
            echo -e "Error: Failed to locate binary: /opt/VRTS/bin/hasys" | tee -a ${vcsReport}-Error.txt
        else
            vcsDir=${outputDir}/VCS-Veritas_Cluster_Server
            vcsFile=${vcsDir}
            vcsReport=${vcsDir}/VCS
            mkdir ${vcsDir}
            if [ ${?} -ne 0 ]; then
                echo -e "Error: Failed to create folder(s): ${vcsDir}" | tee -a ${vcsReport}-Error.txt
                escape
            fi
            timeout -s 9 10 /opt/VRTS/bin/hasys -list &>/dev/null
            if [ ${?} -eq 0 ]; then
                vcsState=0
            else
                vcsState=9
                echo -e "Error: Failed to execute command: /opt/VRTS/bin/hasys -list" | tee -a ${vcsReport}-Error.txt
            fi
        fi
        if [ ${vcsState} -ne 0 ]; then
            echo -e "Info: Skipping VCS report." | tee -a ${vcsReport}-Error.txt
        elif [ ${vcsState} -eq 0 ]; then
            if [ -f /sbin/lltstat ]; then
                echo -e "Processing: VCS - LLT - llstat"
                timeout -s 9 10 /sbin/lltstat 1>${vcsDir}/lltstat
                for cmdOpt in n l c t p H; do
                    echo -e "Processing: VCS - LLT - llstat -${cmdOpt}"
                    timeout -s 9 10 /sbin/lltstat -${cmdOpt} 1>${vcsDir}/lltstat-${cmdOpt}
                done
            fi
            if [ -f /sbin/lltconfig ]; then
                echo -e "Processing: VCS - LLT - lltconfig"
                timeout -s 9 10 /sbin/lltconfig 1>${vcsDir}/lltconfig
                echo -e "Processing: VCS - LLT - lltconfig -a list"
                timeout -s 9 10 /sbin/lltconfig -a list 1>${vcsDir}/lltconfig-a-list
                for cmdOpt in M V W; do
                    echo -e "Processing: VCS - LLT - lltconfig -${cmdOpt}"
                    timeout -s 9 10 /sbin/lltconfig -${cmdOpt} 1>${vcsDir}/lltconfig-${cmdOpt}
                done
            fi
            if [ -f /sbin/gabconfig ]; then
                for cmdOpt in a C v W l; do
                    echo -e "Processing: VCS - GAB - gabconfig -${cmdOpt}" 
                    timeout -s 9 10 /sbin/gabconfig -${cmdOpt} 1>${vcsDir}/gabconfig-${cmdOpt}
                done
            fi
            echo -e "Processing: VCS - /etc/llthosts"
            timeout -s 9 10 cp /etc/llthosts 1>${vcsDir}/etc-llthosts 2>&1
            echo -e "Processing: VCS - /etc/llttab"
            timeout -s 9 10 cp /etc/llttab 1>${vcsDir}/etc-llttab 2>&1
            echo -e "Processing: VCS - /etc/gabtab"
            timeout -s 9 10 cp /etc/gabtab 1>${vcsDir}/etc-gabtab 2>&1
            echo -e "Processing: VCS - hasys -state" 
            timeout -s 9 10 /opt/VRTS/bin/hasys -state 1>${vcsDir}/hasys-state
            echo -e "Processing: VCS - hasys -list" 
            timeout -s 9 10 /opt/VRTS/bin/hasys -list 1>${vcsDir}/hasys-list
            echo -e "Processing: VCS - hastatus -sum" 
            timeout -s 9 10 /opt/VRTS/bin/hastatus -sum 1>${vcsDir}/hastatus-sum
            echo -e "Processing: VCS - hagrp -state" 
            timeout -s 9 10 /opt/VRTS/bin/hagrp -state 1>${vcsDir}/hagrp-state
            echo -e "Processing: VCS - hares -state" 
            timeout -s 9 10 /opt/VRTS/bin/hares -state 1>${vcsDir}/hares-state
            if [ -f /etc/VRTSvcs/conf/config/main.cf ]; then
                echo -e "Processing: VCS - main.cf"
                timeout -s 9 10 cp /etc/VRTSvcs/conf/config/main.cf ${vcsDir}/main.cf
            fi
            vcsReportComplete=1
        fi
    fi
	logTime
}
# Operation: Report - MSDP - Initialization
msdpInit() {
    if [ -z ${msdpInitComplete} ]; then
        # Output Directory
        msdpDir=${outputDir}/MSDP
        mkdir ${msdpDir}
        if [ ${?} -ne 0 ]; then echo -e "Error: Exiting. Failed to create folder(s): ${msdpDir}."; escape; fi
        msdpFile=${msdpDir}
        echo -e "\n\n\n${p1}\nLHC - Processing - Report: MSDP - Configuration\n${p1}"
        # Find Configuration
        pdregistryLink=$(timeout -s 9 10 stat -c '%N' /etc/pdregistry.cfg | sed "s/\('\|‘\|’\)//g")
        pdregistryCfg=$(echo -e "${pdregistryLink}" | awk '{print $NF}')
        spaCfg=$(timeout -s 9 10 awk -F'=' '/spa.cfg/{print $NF}' /etc/pdregistry.cfg)
        crCfg=$(timeout -s 9 10 awk -F'=' '/contentrouter.cfg/{print $NF}' /etc/pdregistry.cfg)
        agentCfg=$(timeout -s 9 10 awk -F'=' '/agent.cfg/{print $NF}' /etc/pdregistry.cfg)
        spwsCfg=$(timeout -s 9 10 awk -F'=' '/spws.cfg/{print $NF}' /etc/pdregistry.cfg)
        # Find Storage
        if [[ -n ${crCfg} && -f ${crCfg} ]]; then
            fstabCfg=$(echo ${crCfg} | sed 's/contentrouter.cfg$/fstab.cfg/g')
            dataPaths=$(awk '$1 ~ "Path=" {print $1}' ${fstabCfg} | sed 's/Path=//;s/\%2F/\//g')
            historyPath=$(timeout -s 9 10 awk -F'=' '/^HistoryPath=/{print $NF}' ${crCfg})
            dbPath=$(timeout -s 9 10 awk -F'=' '/^Path=.*databases/{print $NF}' ${crCfg})
            queuePath=$(timeout -s 9 10 awk -F'=' '/^Path=.*queue/{print $NF}' ${crCfg})
        fi
        if [[ -n ${spaCfg} && -f ${spaCfg} ]]; then
            logPath=$(timeout -s 9 10 awk -F'=' '/^LogPath=/{print $NF}' ${spaCfg})
            shadowPath=$(timeout -s 9 10 awk -F'=' '/^CatalogShadowPath=/{print $NF}' ${spaCfg})
        fi
        if [[ -n ${logPath} && -d ${logPath} ]]; then
            basePath=$(echo ${logPath} | sed 's/\/log$//g')
            etcPath=$(echo ${logPath} | sed 's/log$/etc/g')
        fi
        # Find Logs
        if [[ -n ${logPath} && -d ${logPath} ]]; then
            spooldLogs=$(timeout -s 9 15 ls -1tr ${logPath}/spoold/spoold.log* 2>/dev/null)
            spadLogs=$(timeout -s 9 15 ls -1tr ${logPath}/spad/spad.log* 2>/dev/null)
        fi
        echo -e "${p2}\nMSDP - Configuration - Paths\n${p2}"
        # Copy './etc'
        if [[ -n ${etcPath} && ${etcPath} ]]; then
            timeout -s 9 10 find ${etcPath} -type f -ls 1>${msdpFile}/etc-files.txt
            etcSize=$(timeout -s 9 20 du --max-depth=0 ${etcPath} 2>/dev/null | awk '{print $1}')
            if [[ -n ${etcSize} && ${etcSize} -lt 5000 ]]; then
                cp -r ${etcPath} ${msdpFile}
            fi
        fi
        # MSDP - Configuration - PureDisk Registry
        if [ -f /etc/pdregistry.cfg ]; then
            timeout -s 9 10 cp /etc/pdregistry.cfg ${msdpFile}/configuration-pdregistry.cfg
            if [[ -n ${spaCfg} && -f ${spaCfg} ]]; then timeout -s 9 10 cp ${spaCfg} ${msdpFile}/configuration-spa.cfg; else spaCfg=Missing; fi
            if [[ -n ${crCfg} && -f ${crCfg} ]]; then timeout -s 9 10 cp ${crCfg} ${msdpFile}/configuration-contentrouter.cfg; else crCfg=Missing; fi
        else
            spaCfg=Missing
            crCfg=Missing
        fi
        # MSDP - Configuration - PureDisk Plugin
        if [ -f /usr/openv/lib/ost-plugins/pd.conf ]; then
            pdCfg=/usr/openv/lib/ost-plugins/pd.conf
            timeout -s 9 10 cp ${pdCfg} ${msdpFile}/configuration-pd.conf
        else
            pdCfg=Missing
        fi
        # MSDP - Configuration - Multi-Stream Agent
        if [ -f /usr/openv/lib/ost-plugins/mtstrm.conf ]; then
            mtstrmCfg=/usr/openv/lib/ost-plugins/mtstrm.conf
            timeout -s 9 10 cp ${mtstrmCfg} ${msdpFile}/configuration-mtstrm.conf
        else
            mtstrmCfg=Missing
        fi
        # MSDP Cloud - Configuration - cloud.json
        if [ -f ${etcPath}/puredisk/cloud.json ]; then
            timeout -s 9 5 cp ${etcPath}/puredisk/cloud.json ${msdpFile}/configuration-cloud.json
        else
            cloudJSON=Missing
        fi
        # MSDP Cloud - Configuration - cloudlsu.cfg
        if [ -f ${etcPath}/puredisk/cloudlsu.cfg ]; then
            timeout -s 9 5 cp ${etcPath}/puredisk/cloudlsu.cfg ${msdpFile}/configuration-cloudlsu.cfg
        else
            cloudlsuCfg=Missing
        fi
        # MSDP Cloud - Configuration - kms_cloud.cfg
        if [ -f ${etcPath}/puredisk/kms_cloud.cfg ]; then
            timeout -s 9 5 cp ${etcPath}/puredisk/kms_cloud.cfg ${msdpFile}/configuration-kms_cloud.cfg
        else
            kmsCloudCfg=Missing
        fi
        # MSDP Cloud - Configuration - XML
        fileNames="/usr/openv/var/global/wmc/cloud/CloudInstance.xml /usr/openv/var/global/wmc/cloud/CloudProvider.xml"
        for fileName in ${fileNames}; do
            if [ -f ${fileName} ]; then
                fileNameShort=$(echo ${fileName} | awk -F'/' '{print $NF}')
                timeout -s 9 10 cp ${fileName} ${msdpFile}/configuration-${fileNameShort}
            fi
        done
        # Display Configuration
        echo -e "${p3}\nConfiguration Files\n${p3}"
        echo -e "PD_Registry: ${pdregistryCfg}\nStorage_Pool_Authority_Daemon: ${spaCfg}\nStorage_Pool_Daemon: ${crCfg}\nPureDisk_Plugin: ${pdCfg}\nMulti-Stream_Agent: ${mtstrmCfg}" | column -t | tee -a ${msdpFile}/configuration-environment_settings
        # Storage Paths
        echo -e "\n${p3}\nStorage Paths\n${p3}"
        echo -e "Database_Path: ${dbPath}\nLog_Path: ${logPath}\nQueue_Path: ${queuePath}\nHistory_Path: ${historyPath}\nShadow_Path: ${shadowPath}" | column -t | tee -a ${msdpFile}/configuration-environment_settings
        echo -e "\n${p2}\nMSDP - Services - Status\n${p2}"
        # CR Checks
        echo -e "Processing: crcontrol --getmode"
        timeout -s 9 30 /usr/openv/pdde/pdcr/bin/crcontrol --getmode 1>${msdpFile}/crcontrol-getmode 2>&1
        if [ ${?} -ne 0 ]; then echo -e "Error: Failed to check content router modes: /usr/openv/pdde/pdcr/bin/crcontrol --getmode" 1>${msdpFile}/crcontrol-getmode-err; fi
        echo -e "Processing: crcontrol --dsstat"
        timeout -s 9 30 /usr/openv/pdde/pdcr/bin/crcontrol --dsstat 1>${msdpFile}/crcontrol-dsstat 2>&1
        if [ ${?} -ne 0 ]; then echo -e "Error: Failed to check data store statistics: /usr/openv/pdde/pdcr/bin/crcontrol --dsstat" 1>${msdpFile}/crcontrol-dsstat-err; fi
        echo -e "Processing: crcontrol --taskstat 0 1"
        timeout -s 9 30 /usr/openv/pdde/pdcr/bin/crcontrol --taskstat 0 1 1>${msdpFile}/crcontrol-taskstat 2>&1
        if [ ${?} -ne 0 ]; then echo -e "Error: Failed to check task statistics: /usr/openv/pdde/pdcr/bin/crcontrol --taskstat" 1>${msdpFile}/crcontrol-taskstat-err; fi
        errCount=$(timeout -s 9 5 ls -1 ${msdpFile}/crcontrol-*-err 2>/dev/null)
        if [ -n "${errCount}" ]; then cat ${errCount}; fi
        msdpInitComplete=1
    fi
	logTime
}
# Operation: Report - MSDP - Veritas Deduplication Engine
msdpOverviewReport() {
    if [[ -n ${msdpOverviewReportComplete} || ${msdpOverviewReportComplete} -eq 1 ]]; then
        echo -e "\033[0;31m${p2}\nError - Duplicate Report\n${p2}\n"
        echo -e "Error: MSDP Overview Report has already been executed.\033[0m\n"
    elif [[ -z ${msdpOverviewReportComplete} || ${msdpOverviewReportComplete} -eq 0 ]]; then
        if [ -z ${msdpInitComplete} ]; then msdpInit; fi
        if [[ ${msdpHost} -eq 1 && -d ${msdpDir} ]]; then
            echo -e "\n\n\n${p1}\nLHC - Processing - Report: MSDP Overview\n${p1}"
            # MSDP - Memory Utilization Report
            echo -e "${p2}\nMSDP - Memory Utilization - VSZ/VIRT and RSS\n${p2}" 1>${msdpFile}/MSDP-Memory-Process_Level-Count_VSZ_RSS.txt
            psOut=${msdpFile}/ps-aux
            timeout -s 9 20 ps aux --sort=pmem 1>${psOut} 2>/dev/null
            if [ ${?} -eq 0 ]; then
                procList="spad spoold vpfsd spws ocsd"
                for procName in ${procList}; do
                    echo -e "${p3}\nProcess: ${procName}\n${p3}"
                    procCount=$(grep -c "[/]${procName}\b" ${psOut})
                    if [ ${procCount} -gt 0 ]; then
                        procVSZ=$(grep "[/]${procName}\b" ${psOut} | awk '{sum +=$5} END {print sum / 1000000 }')
                        procRSS=$(grep "[/]${procName}\b" ${psOut} | awk '{sum +=$6} END {print sum / 1000000 }')
                        echo -e "Process_Count: ${procCount}\nMemory_VSZ: ${procVSZ} GB\nMemory_RSS: ${procRSS} GB"
                        echo -e "${p3}"
                        grep "[C]OMMAND\|[/]${procName}\b" ${psOut} | column -t
                        echo -e ""
                    fi | tee ${msdpFile}/MSDP-Memory-Process_Level-Count_VSZ_RSS-${procName}
                done 1>>${msdpFile}/MSDP-Memory-Process_Level-Count_VSZ_RSS.txt
                memReportCount=$(timeout -s 9 5 awk '/./{c++} END {print c+0}' ${msdpFile}/MSDP-Memory-Process_Level-Count_VSZ_RSS.txt)
                if [[ -n ${memReportCount} && ${memReportCount} -gt 18 ]]; then
                    cat ${msdpFile}/MSDP-Memory-Process_Level-Count_VSZ_RSS.txt
                    cp ${msdpFile}/MSDP-Memory-Process_Level-Count_VSZ_RSS.txt ${reportDir}
                else
                    echo -e "Error: MSDP Services are not running." | tee ${msdpFile}/MSDP-Memory-Process_Level-Count_VSZ_RSS-ERR.txt
                    cp ${msdpFile}/MSDP-Memory-Process_Level-Count_VSZ_RSS-ERR.txt ${reportDir}
                fi
            fi
            # Configuration Items
            if [[ -n ${spaCfg} && -f ${spaCfg} ]]; then
                echo -e "\n\n${p2}\nMSDP - Configuration - Overview\n${p2}"
                echo -e "${p3}\nConfiguration - spad\n${p3}"
                timeout -s 9 10 grep "BufferSize\|WorkerThreads\|DefaultSegmentSize" ${spaCfg} 1>${msdpFile}/configuration-spad
                cat ${msdpFile}/configuration-spad
            fi
            if [[ -n ${crCfg} && -f ${crCfg} ]]; then
                echo -e "\n${p3}\nConfiguration - spoold\n${p3}"
                MaxCacheSize=$(timeout -s 9 10 /usr/openv/pdde/pdag/bin/pdcfg --read=${crCfg} --section=Cache --option=MaxCacheSize 2>/dev/null)
                AllocationUnitSize=$(timeout -s 9 10 /usr/openv/pdde/pdag/bin/pdcfg --read=${crCfg} --section=Cache --option=AllocationUnitSize 2>/dev/null)
                echo -e "MaxCacheSize=${MaxCacheSize}\nAllocationUnitSize=${AllocationUnitSize}" 1>${msdpFile}/configuration-spoold
                cat ${msdpFile}/configuration-spoold
            fi
            if [[ -n ${spaCfg} && -f ${spaCfg} ]]; then
                echo -e "\n${p3}\nConfiguration - Cloud - spad\n${p3}"
                timeout -s 9 10 grep "Cloud.*=" ${spaCfg} 1>${msdpFile}/configuration-spad-cloud
                cat ${msdpFile}/configuration-spad-cloud
            fi
            if [[ -n ${crCfg} && -f ${crCfg} ]]; then
                echo -e "\n${p3}\nConfiguration - Cloud - spoold\n${p3}"
                timeout -s 9 10 grep "UsableMemoryLimit=\|MaxCacheSize=\|MaxCloudCacheSize=\|CloudUploadCacheSize=" ${crCfg} 1>${msdpFile}/configuration-spoold-cloud
                cat ${msdpFile}/configuration-spoold-cloud
                echo -e "\n${p3}\nConfiguration - Cache - spoold\n${p3}"
                timeout -s 9 10 grep "Cache.*=" ${crCfg} | grep -v ';' 1>${msdpFile}/configuration-spoold-cache
                cat ${msdpFile}/configuration-spoold-cache
            fi
            if [[ -n ${spaCfg} && -f ${spaCfg} ]]; then
                echo -e "\n${p3}\nConfiguration - Cache - spad\n${p3}"
                timeout -s 9 10 grep "EnableLocalPredictiveSamplingCache" ${spaCfg} 1>${msdpFile}/configuration-spad-cache
                cfgItemList=${msdpFile}/configuration-spad-cache
                cfgItemCount=$(awk '/./{c++} END {print c+0}' ${cfgItemList})
                if [ ${cfgItemCount} -eq 0 ]; then
                    echo -e "Info: No results present";
                else
                    cat ${msdpFile}/configuration-spad-cache
                fi
            fi
            # MSDP - State Validation
            echo -e "\n\n${p2}\nMSDP - Services - State Validation\n${p2}"
            echo -e "Processing: ps -wlfp \$(pidof spad spoold ocsd)"
            timeout -s 9 20 ps -wlfp $(pidof spad spoold ocsd) 1>${msdpFile}/process-ids 2>&1
            if [[ -n ${crCfg} && -f ${crCfg} ]]; then
                # CRQP Checks
                echo -e "Processing: crcontrol --compactstate"
                timeout -s 9 20 /usr/openv/pdde/pdcr/bin/crcontrol --compactstate 1>${msdpFile}/crcontrol-compactstate 2>&1
                echo -e "Processing: crcontrol --crccheckstate"
                timeout -s 9 20 /usr/openv/pdde/pdcr/bin/crcontrol --crccheckstate 1>${msdpFile}/crcontrol-crccheckstate 2>&1
                echo -e "Processing: crcontrol --rebasestate"
                timeout -s 9 20 /usr/openv/pdde/pdcr/bin/crcontrol --rebasestate 1>${msdpFile}/crcontrol-rebasestate 2>&1
                echo -e "Processing: crcontrol --queueinfo"
                timeout -s 9 20 /usr/openv/pdde/pdcr/bin/crcontrol --queueinfo 1>${msdpFile}/crcontrol-queueinfo 2>&1
                # Validations
                echo -e "Processing: crcontrol --os-test"
                timeout -s 9 20 /usr/openv/pdde/pdcr/bin/crcontrol --os-test 1>${msdpFile}/crcontrol-os-test 2>&1
                echo -e "Processing: crcontrol --features"
                timeout -s 9 20 /usr/openv/pdde/pdcr/bin/crcontrol --features 1>${msdpFile}/crcontrol-features 2>&1
                # Replication Jobs
                echo -e "Processing: cacontrol --rep query"
                timeout -s 9 60 /usr/openv/pdde/pdcr/bin/cacontrol --rep query 1>${msdpFile}/cacontrol-rep-query 2>&1
                # Storage Statistics
                echo -e "Processing: pddecfg -a getstatistics"
                timeout -s 9 20 /usr/openv/pdde/pdcr/bin/pddecfg -a getstatistics 1>${msdpFile}/pddecfg-getstatistics 2>&1
                timeout -s 9 10 sed 's/;/\n/g;s/returned: /&\n/g' ${msdpFile}/pddecfg-getstatistics 1>${msdpFile}/pddecfg-getstatistics.txt
                # MSDP Cloud - List Cloud LSUs
                echo -e "Processing: pddecfg -a listcloudlsu"
                timeout -s 9 30 /usr/openv/pdde/pdcr/bin/pddecfg -a listcloudlsu 1>${msdpFile}/pddecfg-listcloudlsu 2>&1
                lsuErrors=$(timeout -s 9 10 awk '/Error/{c++} END {print c+0}' ${msdpFile}/pddecfg-listcloudlsu)
                if [ ${lsuErrors} -gt 0 ]; then
                    echo -e "\nWarning: Error returned from command: /usr/openv/pdde/pdcr/bin/pddecfg -a listcloudlsu\n"
                    timeout -s 9 10 grep "Error" ${msdpFile}/pddecfg-listcloudlsu 1>${msdpFile}/pddecfg-listcloudlsu.err
                    cloudErrCount=$(awk '/Error.*cloud.json/ && !/cloud.json does not exist/ {c++} END {print c+0}' ${msdpFile}/pddecfg-listcloudlsu)
                    if [ ${cloudErrCount} -gt 0 ]; then
                        timeout -s 9 10 awk '/Error.*cloud.json/ && !/cloud.json does not exist/' ${msdpFile}/pddecfg-listcloudlsu 1>${msdpFile}/pddecfg-listcloudlsu.err-cloud.json
                    fi
                fi
                # CR Stats
                echo -e "Processing: crstats --convert-size --verbose"
                timeout -s 9 60 /usr/openv/pdde/pdcr/bin/crstats --convert-size --verbose 1>${msdpFile}/crstats-convert-size-dsid-2 2>&1
                # CR Stats - Cloud
                cloudDSIDs=$(timeout -s 9 10 awk -F',' '!/Error|lsuname/ && /,/ {gsub(" ","");print $1}' ${msdpFile}/pddecfg-listcloudlsu)
                if [ -n "${cloudDSIDs}" ]; then
                    for cloudDSID in ${cloudDSIDs}; do
                        echo -e "Processing: crstats --convert-size --verbose --cloud-dsid ${cloudDSID}"
                        timeout -s 9 60 /usr/openv/pdde/pdcr/bin/crstats --convert-size --verbose --cloud-dsid ${cloudDSID} 1>${msdpFile}/crstats-convert-size-dsid-${cloudDSID} 2>&1
                    done
                fi
                # MSDP Cloud - csconfig
                if [ -f /usr/openv/netbackup/bin/admincmd/csconfig ]; then
                    echo -e "Processing: csconfig cldinstance -l - Timeout: 2 minutes"
                    startCmdTime=$(date +%s.%N)
                    timeout -s 9 120 /usr/openv/netbackup/bin/admincmd/csconfig cldinstance -l 1>${msdpFile}/csconfig_cldinstance_-l 2>&1
                    endCmdTime=$(date +%s.%N)
                    totalCmdTime=$(echo -e "${endCmdTime} - ${startCmdTime}" | bc -l)
                    echo -e "${totalCmdTime}" 1>${msdpFile}/csconfig_cldinstance_-l
                    echo -e "Processing: csconfig cldinstance -i - Timeout: 2 minutes"
                    startCmdTime=$(date +%s.%N)
                    timeout -s 9 120 /usr/openv/netbackup/bin/admincmd/csconfig cldinstance -i 1>${msdpFile}/csconfig_cldinstance_-i 2>&1
                    endCmdTime=$(date +%s.%N)
                    totalCmdTime=$(echo -e "${endCmdTime} - ${startCmdTime}" | bc -l)
                    echo -e "${totalCmdTime}" 1>${msdpFile}/csconfig_cldinstance_-i
                fi
            fi
            # Configuration Test
            echo -e "Processing: spad --test"
            timeout -s 9 30 /usr/openv/pdde/pdcr/bin/spad --test 1>${msdpFile}/test-spad 2>&1
            echo -e "Processing: spoold --test"
            timeout -s 9 30 /usr/openv/pdde/pdcr/bin/spoold --test 1>${msdpFile}/test-spoold 2>&1
            # Version
            echo -e "Processing: spad --version"
            timeout -s 9 20 /usr/openv/pdde/pdcr/bin/spad --version 1>${msdpFile}/version-spad 2>&1
            echo -e "Processing: spoold --version"
            timeout -s 9 20 /usr/openv/pdde/pdcr/bin/spoold --version 1>${msdpFile}/version-spoold 2>&1
            echo -e "Processing: crcontrol --version"
            timeout -s 9 20 /usr/openv/pdde/pdcr/bin/crcontrol --version 1>${msdpFile}/version-crcontrol 2>&1
            # Communication
            echo -e "Processing: Communication - Port Test - spad/10102"
            timeout --foreground -s 9 3 curl -v telnet://localhost:10102 1>${msdpFile}/communication-port_test-spad-10102 2>&1
            echo -e "Processing: Communication - Port Test - spoold/10082"
            timeout --foreground -s 9 3 curl -v telnet://localhost:10082 1>${msdpFile}/communication-port_test-spoold-10082 2>&1
            # Process Maps 
            spadPid=$(pidof spad)
            spooldPid=$(pidof spad)
            if [[ -n ${spadPid} && -f /bin/pmap ]]; then
                echo -e "Processing: Process Map - spad - pmap ${spadPid}"
                timeout -s 9 20 /bin/pmap ${spadPid} 1>${msdpFile}/MSDP-Memory-process-spad-pmap 2>&1
                echo -e "Processing: Process Map - spad - pmap -X ${spadPid}"
                timeout -s 9 20 /bin/pmap -X ${spadPid} 1>${msdpFile}/MSDP-Memory-process-spad-pmap-X 2>&1
            fi
            if [[ -n ${spooldPid} && -f /bin/pmap ]]; then
                echo -e "Processing: Process Map - spoold - pmap ${spooldPid}"
                timeout -s 9 20 /bin/pmap ${spooldPid} 1>${msdpFile}/MSDP-Memory-process-spoold-pmap 2>&1
                echo -e "Processing: Process Map - spoold - pmap -X ${spooldPid}"
                timeout -s 9 20 /bin/pmap -X ${spooldPid} 1>${msdpFile}/MSDP-Memory-process-spoold-pmap-X 2>&1
            fi
            # Log Review
            if [ -d ${logPath} ]; then
                echo -e "\n${p2}\nLog Review\n${p2}"
                if [ -n "${spooldLogs}" ]; then
                    echo -e "Processing: MSDP - Events - spoold - FP Cache Load - Global"
                    timeout -s 9 30 grep -i "complete cache\|incomplete cache" ${spooldLogs} 1>${msdpFile}/events-spoold-fingerprint_cache-complete 2>/dev/null
                    echo -e "Processing: MSDP - Events - spoold - FP Cache Size - Global"
                    timeout -s 9 30 grep "Memory usage of global fingerprint cache" ${spooldLogs} 1>${msdpFile}/events-spoold-fingerprint_cache-size 2>/dev/null
                    echo -e "Processing: MSDP - Events - spoold - FP Cache Size - Cloud"
                    timeout -s 9 30 grep "Memory usage of cache for dsid" ${spooldLogs} 2>/dev/null | sed 's/[0-9][0-9]:.*cache for//g;s/in total,/used/g;s/://g' | uniq 1>${msdpFile}/events-spoold-fingerprint_cache-size-cloud 
                    echo -e "Processing: MSDP - Events - spoold - Memory Use"
                    timeout -s 9 30 grep "Memory Usage.*%" ${spooldLogs} 1>${msdpFile}/events-spoold-memory_use 2>/dev/null
                    echo -e "Processing: MSDP - Events - spoold - Memory Exhaustion"
                    timeout -s 9 30 grep -i "exhaustion\|no enough" ${spooldLogs} 1>${msdpFile}/events-spoold-memory_exhaustion 2>/dev/null
                    echo -e "Processing: MSDP - Events - spoold - Service Startup / Shutdown"
                    timeout -s 9 30 grep "Startup.*occurred\|Shutdown.*completed" ${spooldLogs} 1>${msdpFile}/events-spoold-startup_occurred 2>/dev/null
                fi
                if [ -n "${spadLogs}" ]; then
                    echo -e "Processing: MSDP - Events - spad - Service Startup"
                    timeout -s 9 30 grep "Startup.*occurred\|Shutdown.*completed" ${spadLogs} 1>${msdpFile}/events-spad-startup_occurred 2>/dev/null
                fi
                # MSDP - Memory Allocation Errors
                if [ -f ${logPath}/spoold/storaged.log ]; then
                    echo -e "Processing: MSDP - Resources - Processing"
                    timeout -s 9 30 grep -H "Could not process spool entry" ${logPath}/spoold/storaged.log* 1>>${msdpFile}/events-memory_exhaustion-storaged 2>/dev/null
                    echo -e "Processing: MSDP - Resources - Memory"
                    timeout -s 9 30 grep -H "out of memory" ${logPath}/spoold/storaged.log* 1>>${msdpFile}/events-memory_exhaustion-storaged 2>/dev/null
                    timeout -s 9 30 grep -H "Failed to add entry" ${logPath}/spoold/storaged.log* 1>>${msdpFile}/events-memory_exhaustion-storaged 2>/dev/null
                    echo -e "Processing: MSDP - Resources - Exception"
                    timeout -s 9 30 grep -H "exception happens while" ${logPath}/spoold/storaged.log* 1>>${msdpFile}/events-memory_exhaustion-storaged 2>/dev/null
                    echo -e "Processing: MSDP - Resources - RefDB"
                    timeout -s 9 30 grep -H "Failed to update refdb" ${logPath}/spoold/storaged.log* 1>>${msdpFile}/events-memory_exhaustion-storaged 2>/dev/null
                    echo -e "Processing: MSDP - Resources - Tlog"
                    timeout -s 9 30 grep -H "Could not process tlog" ${logPath}/spoold/storaged.log* 1>>${msdpFile}/events-memory_exhaustion-storaged 2>/dev/null
                    echo -e "Processing: MSDP - Resources - Write Prepare"
                    timeout -s 9 30 grep -H "write_prepare fail to prepare" ${logPath}/spoold/storaged.log* 1>>${msdpFile}/events-memory_exhaustion-storaged 2>/dev/null
                    echo -e "Processing: MSDP - Resources - Write Malloc"
                    timeout -s 9 30 grep -H "write_prepare fail to malloc" ${logPath}/spoold/storaged.log* 1>>${msdpFile}/events-memory_exhaustion-storaged 2>/dev/null
                    echo -e "Processing: MSDP - Resources - Fail Malloc"
                fi
                if [ -f ${logPath}/spoold/spoold.log ]; then
                    timeout -s 9 30 grep -H "could not allocate memory" ${logPath}/spoold/spoold.log* 1>>${msdpFile}/events-memory_exhaustion-storaged 2>/dev/null
                fi
                # MSDP - CheckCRCd Log
                if [ -f ${logPath}/spoold/checkcrcd.log ]; then
                    echo -e "Processing: MSDP - CheckCRCd - Log Files"
                    timeout -s 9 10 ls -ltr ${logPath}/spoold/checkcrcd* 1>${msdpFile}/checkcrcd-files 2>/dev/null
                    echo -e "Processing: MSDP - CheckCRCd - Check Finished"
                    timeout -s 9 30 grep Finished ${logPath}/spoold/checkcrcd* 2>/dev/null | awk '{ $3=$4=$5=$12=""; print $0 }' | uniq -c 1>${msdpFile}/checkcrcd-finished
                    timeout -s 9 30 grep days ${logPath}/spoold/checkcrcd* 2>/dev/null | awk '{ $2=$3=$5=$11=""; print $0}' | uniq -c 1>${msdpFile}/checkcrcd-not_running
                    echo -e "Processing: MSDP - CheckCRCd - Check Errors"
                    timeout -s 9 30 grep "ERR\|WARN\|errors\|failed" ${logPath}/spoold/checkcrcd* 2>/dev/null | grep -v days 1>${msdpFile}/checkcrcd-errors-full
                    timeout -s 9 30 grep "CRC check found errors" ${logPath}/spoold/checkcrcd* 2>/dev/null | awk '{$3=""; $12="container(DCID)"; print $0}' | sort | uniq -c 1>${msdpFile}/checkcrcd-errors-Summary
                fi
                # MSDP - Replication Log
                if [ -f ${logPath}/spad/replication.log ]; then
                    echo -e "Processing: MSDP - Replication - Check Error - CRC mismatch for data"
                    timeout -s 9 30 grep "CRC mismatch for data" ${logPath}/spad/replication.log* 1>${msdpFile}/replication-crc_mismatch 2>/dev/null
                    echo -e "Processing: MSDP - Replication - Check Error - Failed to replicate non-existing SOs"
                    timeout -s 9 30 grep "failed to replicate non-existing SOs" ${logPath}/spad/replication.log* 1>${msdpFile}/replication-non-existing_so 2>/dev/null
                    echo -e "Processing: MSDP - Replication - Check Error - CRReplicate of batch failed (data corrupt)"
                    timeout -s 9 30 grep "CRReplicate of batch failed (data corrupt)" ${logPath}/spad/replication.log* 1>${msdpFile}/replication-data_corrupt 2>/dev/null
                    echo -e "Processing: MSDP - Replication - Check Error - Could not receive DO to replicate: no route found"
                    timeout -s 9 30 grep "Could not receive DO to replicate: no route found" ${logPath}/spad/replication.log* 1>${msdpFile}/replication-no_route_found 2>/dev/null
                    echo -e "Processing: MSDP - Replication - Check Error - Could not read SO"
                    timeout -s 9 30 grep "Could not read SO" ${logPath}/spad/replication.log* 1>${msdpFile}/replication-could_not_read_so 2>/dev/null
                fi
            fi
            # MSDP - Affected Image List
            echo -e "Processing: MSDP - Catalog - Affected Image List - Timeout: 5 minutes"
            timeout -s 9 300 /usr/openv/pdde/pdcr/bin/catdbutil --list --status=CORRUPT 1>${msdpFile}/catdbutil-corrupt
            if [ ${?} -ne 0 ]; then echo -e "\tError: Timeout reached."; fi
            if [ -f ${msdpFile}/catdbutil-corrupt ]; then
                grep "|6|" ${msdpFile}/catdbutil-corrupt | awk -F'|' '{print $2, $3}' 1>${msdpFile}/catdbutil-corrupt-parsed
                while read nameClientPolicy nameImage; do
                    nameClient=$(echo ${nameClientPolicy} | awk -F'/' '{print $2}')
                    namePolicy=$(echo ${nameClientPolicy} | awk -F'/' '{print $3}')
                    nameImage=$(echo ${nameImage} | sed 's/_C[0-9]_.*//g')
                    echo -e "${namePolicy} ${nameClient} ${nameImage}"
                done <${msdpFile}/catdbutil-corrupt-parsed | sort -u 1>${msdpFile}/catdbutil-corrupt-unique
                imageCount=$(awk '/./{c++} END {print c+0}' ${msdpFile}/catdbutil-corrupt-unique)
                if [ ${imageCount} -gt 0 ]; then
                    while read namePolicy nameClient nameImage; do
                        imageTime=$(echo ${nameImage} | awk -F'_' '{print $NF}')
                        imageDate=$(date -d @${imageTime} 2>/dev/null)
                        echo -e "${imageDate}, ${imageTime}, ${nameImage}, ${nameClient}, ${namePolicy}" 1>>${msdpFile}/catdbutil-corrupt-report.txt
                    done <${msdpFile}/catdbutil-corrupt-unique
                fi
            fi
            echo -e "Processing: MSDP - Catalog - Affected Backup List"
            timeout -s 9 10 ls -l ${dbPath}/datacheck/AffectedBackup.lst 1>${msdpFile}/datacheck-affectedbackup.lst-timestamp 2>/dev/null
            timeout -s 9 10 awk '/./{c++} END {print c+0}' ${dbPath}/datacheck/AffectedBackup.lst 1>${msdpFile}/datacheck-affectedbackup.lst-count 2>/dev/null
            timeout -s 9 10 cat ${dbPath}/datacheck/AffectedBackup.lst 1>${msdpFile}/datacheck-affectedbackup.lst-list 2>/dev/null 
            echo -e "Processing: MSDP - Catalog - Datacheck List"
            timeout -s 9 10 ls -lh ${dbPath}/datacheck/ 1>${msdpFile}/datacheck-list 2>/dev/null
            echo -e "Processing: MSDP - Catalog - File List - Timeout: 5 minutes"
            timeout -s 9 300 find ${dbPath} -type f -ls 1>${msdpFile}/catalog-file_list.txt 2>/dev/null
        fi
    fi
	logTime
}
# Option: Report - MSDP - Client Session Logs
msdpSessionReport() {
    if [[ -n ${msdpSessionReportComplete} || ${msdpSessionReportComplete} -eq 1 ]]; then
        echo -e "\033[0;31m${p2}\nError - Duplicate Report\n${p2}\n"
        echo -e "Error: MSDP Client Session Log Report has already been executed.\033[0m\n"
    elif [[ -z ${msdpSessionReportComplete} || ${msdpSessionReportComplete} -eq 0 ]]; then
        if [ -z ${msdpInitComplete} ]; then msdpInit; fi
        echo -e "\n\n\n${p1}\nLHC - Processing - Report: MSDP - Performance - Client Session Log\n${p1}"
        if [[ ! -d ${logPath} ]]; then
            echo -e "Error: The MSDP Log Path could not be found. Check '/etc/pdregistry.cfg' file."
        elif [[ -d ${logPath} && -d ${msdpDir} ]]; then 
            # Initialization
            echo -e "${p2}\nInitialization\n${p2}"
            cslReport=${msdpFile}/${filePrefix}-MSDP-Performance-Client_Session_Log_Report
            mkdir -p ${cslReport}/data
            if [ ${?} -ne 0 ]; then echo -e "Error: Failed to create folder(s): ${cslReport}" | tee -a ${msdpFile}-Error.txt; fi
            clientList=${cslReport}/${sourceDate}-client_list
            timeout -s 9 120 find ${logPath}/spoold -mindepth 1 -maxdepth 1 -type d | awk -F'/' '{print $NF}' 1>${clientList}
            countTotal=$(awk '/./{c++} END {print c+0}' ${clientList})
            sessionLogsDays=14
            # Process Logs
            countNum=-1
            while read clientName; do
                ((countNum++)); if ! (( ${countNum} % 10 )) ; then 
                    pctProgress=$(expr ${countNum} \* 100 / ${countTotal})
                    echo -e "Progress: ${countNum} of ${countTotal}..  ${pctProgress}% Complete."
                fi
                mkdir ${cslReport}/data/${clientName}
                if [ ${?} -ne 0 ]; then
                    echo -e "Error: Failed to create directory: ${cslReport}/data/${clientName}"
                    return 9
                fi
                SOput=${cslReport}/data/${clientName}/${clientName}-spoold-SO_PUT.log
                bytesSent=${cslReport}/data/${clientName}/${clientName}-spoold-bytes_sent-tx.log
                bytesReceived=${cslReport}/data/${clientName}/${clientName}-spoold-bytes_receive-rx.log
                connectionTMO=${cslReport}/data/${clientName}/${clientName}-connection-TCP_Timeout-TMO.log
                connectionRST=${cslReport}/data/${clientName}/${clientName}-connection-TCP_Reset-RST.log
                sessionLogs=$(timeout -s 9 20 find ${logPath}/spoold/${clientName} -type f -mtime -${sessionLogsDays})
                if [ ${?} -ne 0 ]; then echo -e "Error: Failed to find files(s): ${logPath}/spoold/${clientName}" | tee -a ${msdpFile}-Error.txt; return; fi
                sessionLogsCount=$(echo ${sessionLogs} | awk '!/^[[:space:]]*$/ {x++} END {print (x ? x : 0)}')
                if [ ${sessionLogsCount} -eq 0 ]; then
                    echo -e "Error: No MSDP Session Logs for for client: ${clientName}" | tee -a ${msdpFile}-Error.txt
                elif [ ${sessionLogsCount} -gt 0 ]; then
                    grep -R "SO PUT" ${sessionLogs} 1>${SOput} 2>/dev/null
                    grep -R "Bytes Sent" ${sessionLogs} 1>${bytesSent} 2>/dev/null
                    grep -R "Bytes Received" ${sessionLogs} 1>${bytesReceived} 2>/dev/null
                    grep -Ri "timed out" ${sessionLogs} 1>${connectionTMO} 2>/dev/null
                    grep -Ri "connection reset" ${sessionLogs} 1>${connectionRST} 2>/dev/null
                    sentTotal=$(awk '{sum +=$(NF)} END {print sum / 1024000}' ${bytesSent} 2>/dev/null)
                    recvTotal=$(awk '{sum +=$(NF)} END {print sum / 1024000}' ${bytesReceived} 2>/dev/null)
                    tmoTotal=$(awk '/./{c++} END {print c+0}' ${connectionTMO})
                    rstTotal=$(awk '/./{c++} END {print c+0}' ${connectionRST})
                    range1=$(awk '$(NF-1)>=10 && $(NF-1)<=20' ${SOput} | wc -l)
                    range2=$(awk '$(NF-1)>=20 && $(NF-1)<=30' ${SOput} | wc -l)
                    range3=$(awk '$(NF-1)>=30 && $(NF-1)<=60' ${SOput} | wc -l)
                    range4=$(awk '$(NF-1)>=60 && $(NF-1)<=120' ${SOput} | wc -l)
                    range5=$(awk '$(NF-1)>=120 && $(NF-1)<=180' ${SOput} | wc -l)
                    range6=$(awk '$(NF-1)>=180 && $(NF-1)<=240' ${SOput} | wc -l)
                    range7=$(awk '$(NF-1)>=240 && $(NF-1)<=300' ${SOput} | wc -l)
                    range8=$(awk '$(NF-1)>=300 && $(NF-1)<=1000' ${SOput} | wc -l)
                    range9=$(awk '$(NF-1)>=1000 && $(NF-1)<=10000' ${SOput} | wc -l)
                    echo -e "${clientName} \t ${range1} \t ${range2} \t ${range3} \t ${range4} \t ${range5} \t ${range6} \t ${range7} \t ${range8} \t ${range9} \t Timeout=${tmoTotal} \t Reset=${rstTotal} \t ${sentTotal} \t ${recvTotal}" 1>>${cslReport}/${sourceDate}-Data
                    echo -e "${clientName} \t ${sentTotal} MB.sent \t ${recvTotal} MB.recv" 1>>${cslReport}/${sourceDate}-Data_Transmit-Total
                fi
            done <${clientList}
            # Create Summary - Column
            if [ -f ${cslReport}/${sourceDate}-Data ]; then
                timeout -s 9 15 echo -e "Seconds 10-20 20-30 30-60 60-120 120-180 180-240 240-300 300-1000 1000-10000 Timeout Reset Sent_MB Received_MB\n$(cat ${cslReport}/${sourceDate}-Data)" | column -t 1>${cslReport}/MSDP-Performance-Client_Session_Logs-Report.txt
                timeout -s 9 15 grep -v "Timeout=0.*Reset=0" ${cslReport}/MSDP-Performance-Client_Session_Logs-Report.txt 1>${cslReport}/MSDP-Performance-Client_Session_Logs-Report-Connection_Errors.txt
                cp ${cslReport}/MSDP-Performance-Client_Session_Logs*.txt ${reportDir}
                # Create Summary - Transmit
                reportTransmit=${cslReport}/${sourceDate}-Data_Transmit-Total
                timeout -s 9 10 sort -nrk2 ${reportTransmit} | column -t 1>${reportTransmit}-sort-SENT
                timeout -s 9 10 sort -nrk4 ${reportTransmit} | column -t 1>${reportTransmit}-sort-RECV
                # Display Summary
                echo -e "\n${p2}\nResuls\n${p2}\n"
                cat ${cslReport}/MSDP-Performance-Client_Session_Logs-Report.txt
                echo -e "\n"
            fi
            msdpSessionReportComplete=1
        fi
    fi
	logTime
}
# Option: Report - MSDP - Historical Dedupe Rates
msdpDedupeReport() {
    if [[ -n ${msdpDedupeReportComplete} || ${msdpDedupeReportComplete} -eq 1 ]]; then
        echo -e "\033[0;31m${p2}\nError - Duplicate Report\n${p2}\n"
        echo -e "Error: MSDP Historical Dedupe Report has already been executed.\033[0m\n"
    elif [[ -z ${msdpDedupeReportComplete} || ${msdpDedupeReportComplete} -eq 0 ]]; then
        if [ -z ${msdpInitComplete} ]; then msdpInit; fi
        echo -e "\n\n\n${p1}\nLHC - Processing - Report: MSDP - Historical Dedupe Rate Report\n${p1}"
        if [[ ! -d ${historyPath}/jobstats ]]; then
            echo -e "ERROR: The '${historyPath}/jobstats' directory does not exist."
        elif [[ -d ${historyPath}/jobstats && -d ${msdpDir} ]]; then
            # Set Variables
            crstatsPath=${historyPath}/crstats
            jobstatsPath=${historyPath}/jobstats
            spacereclamationPath=${historyPath}/spacereclamation
            # Initialization
            dedupeDir=${msdpFile}/${filePrefix}-MSDP-Storage-Historical_Dedupe_Rates
            dedupeFile=${dedupeDir}/MSDP
            mkdir ${dedupeDir}
            # MSDP - History - jobstats - collect
            echo -e "${p2}\nCollect Files\n${p2}"
            jobstatsFilesAll=$(timeout -s 9 10 ls -1tr ${historyPath}/jobstats/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9])
            echo -e "Collecting Files... Timeout: 2 minutes"
            timeout -s 9 120 tar czf ${dedupeDir}/${filePrefix}-MSDP-Dedupe_Rates-jobstats_files.tgz ${jobstatsFilesAll} 2>/dev/null
            echo -e "Collecting Files... Done."
            # MSDP - History - jobstats - combine
            echo -e "\n${p2}\nCombine Files\n${p2}"
            jobstatsCombined=${dedupeFile}-Dedupe_Rates
            for jobstatsFile in ${jobstatsFilesAll}; do
                echo -e "Processing: ${jobstatsFile}"
                fileType=$(timeout -s 9 10 file ${jobstatsFile} | awk '{print $2}')
                if [[ -n ${fileType} && ${fileType} == "ASCII" ]]; then
                    jobstatsFiles+="${jobstatsFile} "
                    cat ${jobstatsFile} 1>>${jobstatsCombined}
                else
                    echo -e "Error: Empty or not ASCII file: ${jobstatsFile}. Skipping." 1>>${dedupeDir}/${filePrefix}-MSDP-Dedupe_Rates-jobstats_files-error.txt
                fi
            done
            # MSDP - History - jobstats - parse
            echo -e "\n${p2}\nProcess Data\n${p2}"
            if [ -z "${jobstatsFiles}" ]; then
                echo -e "Error: No records present in 'jobstats' data files." | tee -a ${dedupeDir}/${filePrefix}-MSDP-Dedupe_Rates-jobstats_files-error.txt
            else
                # Processing
                echo -e "${p3}\nProcessing\n${p3}"
                echo -e "Processing: Cleanup records"
                grep "policy=UNKNOWN\|policy=UNKN" ${jobstatsCombined} 1>${jobstatsCombined}-addendum
                sed -i '/policy=UNKNOWN/d;/policy=UNKN/d' ${jobstatsCombined}
                echo -e "Processing: Convert CTIME"
                awk -F"," '{OFS=","; $1=strftime("%Y-%m-%d, %H:%M:%S", $1); $2="";} NF==10' ${jobstatsCombined} 1>${jobstatsCombined}-date_convert
                echo -e "Processing: Sanitize data"
                sed 's/\(image_name=\|dedup=\|compression_space_saving=\|dedupe_space_saving=\|backup_ksize=\|dsid=\|client=\|policy=\)//g;s/,,/, /g' ${jobstatsCombined}-date_convert 1>${jobstatsCombined}-csv
                echo -e "Processing: Calculate data written"
                awk -F',' '{OFS=", "; OFMT="%f"; written=($7 * ((100 - $4) * .01)); print $0, $7, written, $7 / 1024000, written / 1024000}' ${jobstatsCombined}-csv 1>${jobstatsCombined}-csv-written
                echo -e "Processing: Sort by start time"
                echo -e "Date, Time, BackupID, Dedupe_Rate, Compression_Savings, Dedupe_Saings, Size, DSID, Client, Policy, Size_KB, Written_KB, Size_GB, Written_GB" 1>${jobstatsCombined}-Report
                cat ${jobstatsCombined}-csv-written 1>>${jobstatsCombined}-Report
                column -t ${jobstatsCombined}-Report 1>${jobstatsCombined}-Report-Sort_by_date.txt
                echo -e "Processing: Sort by data written"
                sort -nrk12 ${jobstatsCombined}-csv-written 1>${jobstatsCombined}-csv-written-sort
                echo -e "Processing: Sort by data written - Column headers"
                echo -e "Date, Time, BackupID, Dedupe_Rate, Compression_Savings, Dedupe_Saings, Size, DSID, Client, Policy, Size_KB, Written_KB, Size_GB, Written_GB" 1>${jobstatsCombined}-Report
                cat ${jobstatsCombined}-csv-written-sort 1>>${jobstatsCombined}-Report
                column -t ${jobstatsCombined}-Report 1>${jobstatsCombined}-Report-Sort_by_size.txt
                # MSDP - History - jobstats - detail summary - processing
                mkdir ${dedupeDir}/client ${dedupeDir}/policy ${dedupeDir}/client_policy
                reportName=${jobstatsCombined}-Report-Sort_by_date.txt
                echo -e "Processing: Policy Names"
                awk -F',' '{print $10}' ${reportName} | sed '1d;s/[[:space:]]//g' | sort -u > ${dedupeDir}/policy_names
                echo -e "Processing: Client Names"
                awk -F',' '{print $9}' ${reportName} | sed '1d;s/[[:space:]]//g' | sort -u > ${dedupeDir}/client_names
                echo -e "Processing: Client+Policy Names"
                awk -F',' '{print $9, $10}' ${reportName} | sed '1d;s/ \+/ /g;s/^ //g' | sort -u > ${dedupeDir}/client_policy_names
                # Summaries
                echo -e "\n${p3}\nSummaries\n${p3}"
                # Policy Report
                echo -e "Processing: Policy Summary"
                while read policyName; do
                    awk -v policyName="${policyName}," '$10 == policyName' ${reportName} > ${dedupeDir}/policy/${policyName}
                    imageCount=$(wc -l ${dedupeDir}/policy/${policyName} | awk '{print $1}')
                    dedupeRates=$(awk -v OFS=',' -v CONVFMT='%2.2f' -v OFMT='%2f' -v imageCount=${imageCount} '{sumSize+=$(NF-1); sumWritten+=$NF} END {printf sumSize ", " sumWritten ", "100 - sumWritten / sumSize * 100 "%, " imageCount "\n"; }' ${dedupeDir}/policy/${policyName})
                    echo -e "${policyName}, ${dedupeRates}"
                done <${dedupeDir}/policy_names > ${dedupeFile}-Data_Written-Policy.csv
                sort -nrk3 ${dedupeFile}-Data_Written-Policy.csv > ${dedupeFile}-Data_Written-Policy-Sort.csv
                sed -i '1s/^/Policy, Total_GB, Written_GB, Dedupe, Image_Count\n/' ${dedupeFile}-Data_Written-Policy.csv
                sed -i '1s/^/Policy, Total_GB, Written_GB, Dedupe, Image_Count\n/' ${dedupeFile}-Data_Written-Policy-Sort.csv
                column -t ${dedupeFile}-Data_Written-Policy.csv > ${dedupeFile}-Data_Written-Policy.txt
                column -t ${dedupeFile}-Data_Written-Policy-Sort.csv > ${dedupeFile}-Data_Written-Policy-Sort.txt
                # Process Client
                echo -e "Processing: Client Summary"
                while read clientName; do
                    awk -v clientName="${clientName}," '$9 == clientName' ${reportName} > ${dedupeDir}/client/${clientName}
                    imageCount=$(wc -l ${dedupeDir}/client/${clientName} | awk '{print $1}')
                    dedupeRates=$(awk -v OFS=',' -v CONVFMT='%2.2f' -v OFMT='%2f' -v imageCount=${imageCount} '{sumSize+=$(NF-1); sumWritten+=$NF} END {printf sumSize ", " sumWritten ", "100 - sumWritten / sumSize * 100 "%, " imageCount "\n"; }' ${dedupeDir}/client/${clientName})
                    echo -e "${clientName}, ${dedupeRates}"
                done <${dedupeDir}/client_names > ${dedupeFile}-Data_Written-Client.csv
                sort -nrk3 ${dedupeFile}-Data_Written-Client.csv > ${dedupeFile}-Data_Written-Client-Sort.csv
                sed -i '1s/^/Client, Total_GB, Written_GB, Dedupe, Image_Count\n/' ${dedupeFile}-Data_Written-Client.csv
                sed -i '1s/^/Client, Total_GB, Written_GB, Dedupe, Image_Count\n/' ${dedupeFile}-Data_Written-Client-Sort.csv
                column -t ${dedupeFile}-Data_Written-Client.csv > ${dedupeFile}-Data_Written-Client.txt
                column -t ${dedupeFile}-Data_Written-Client-Sort.csv > ${dedupeFile}-Data_Written-Client-Sort.txt
                # Process Client/Policy
                echo -e "Processing: Client+Policy Summary"
                while read clientName policyName; do
                    awk -v clientName="${clientName}," -v policyName="${policyName}," '$9 == clientName && $10 == policyName' ${reportName} > ${dedupeDir}/client_policy/${clientName},${policyName}
                    imageCount=$(wc -l ${dedupeDir}/client_policy/${clientName},${policyName} | awk '{print $1}')
                    dedupeRates=$(awk -v OFS=',' -v CONVFMT='%2.2f' -v OFMT='%2f' -v imageCount=${imageCount} '{sumSize+=$(NF-1); sumWritten+=$NF} END {printf sumSize ", " sumWritten ", "100 - sumWritten / sumSize * 100 "%, " imageCount "\n"; }' ${dedupeDir}/client_policy/${clientName},${policyName})
                    echo -e "${clientName}, ${policyName}, ${dedupeRates}"
                done <${dedupeDir}/client_policy_names > ${dedupeFile}-Data_Written-Client_Policy.csv
                sort -nrk4 ${dedupeFile}-Data_Written-Client_Policy.csv > ${dedupeFile}-Data_Written-Client_Policy-Sort.csv
                sed -i '1s/^/Client, Policy, Total_GB, Written_GB, Dedupe, Image_Count\n/' ${dedupeFile}-Data_Written-Client_Policy.csv
                sed -i '1s/^/Client, Policy, Total_GB, Written_GB, Dedupe, Image_Count\n/' ${dedupeFile}-Data_Written-Client_Policy-Sort.csv
                column -t ${dedupeFile}-Data_Written-Client_Policy.csv > ${dedupeFile}-Data_Written-Client_Policy.txt
                column -t ${dedupeFile}-Data_Written-Client_Policy-Sort.csv > ${dedupeFile}-Data_Written-Client_Policy-Sort.txt
                # MSDP - History - jobstats - workload summary - processing
                echo -e "Processing: Summary - Jobs per policy"
                awk -F',' '{print $NF}' ${jobstatsCombined}-csv | sort | uniq -c | sort -nr 1>${jobstatsCombined}-Summary-Jobs_per_policy.txt   
                echo -e "Processing: Summary - Jobs per client"
                awk -F',' '{print $(NF-1)}' ${jobstatsCombined}-csv | sort | uniq -c | sort -nr 1>${jobstatsCombined}-Summary-Jobs_per_client.txt
                echo -e "Processing: Summary - Jobs per client-policy"
                awk -F',' '{print $9, $10}' ${jobstatsCombined}-csv | sort | uniq -c | sort -nr | column -t 1>${jobstatsCombined}-Summary-Jobs_per_client-policy.txt
                # MSDP - History - jobstats - workload summary - report
                if [ -f ${jobstatsCombined}-Report-Sort_by_size.txt ]; then
                    echo -e "\n${p2}\nMSDP - Historical Dedupe Rate Report - Summary\n${p2}"
                    echo -e "${p3}\nHost Information\n${p3}\nHostname: ${hostnameFull}\nStorage:"
                    grep -v "to get" ${msdpFile}/crcontrol-dsstat
                    # Jobs per Policy
                    echo -e "${p3}\nPolicy Summary - Top 30\n${p3}"
                    head -n 30 ${dedupeFile}-Data_Written-Policy-Sort.txt
                    # Jobs per Client
                    echo -e "\n${p3}\nClient Summary - Top 30\n${p3}"
                    head -n 30 ${dedupeFile}-Data_Written-Client-Sort.txt
                    # Jobs per Client / Policy
                    echo -e "\n${p3}\nClient+Policy Summary - Top 30\n${p3}"
                    head -n 30 ${dedupeFile}-Data_Written-Client_Policy-Sort.txt
                    # Storage Utilization
                    echo -e "\n${p3}\nStorage Utilization - Top 100\n${p3}"
                    jobstatsReport=$(echo -e "${jobstatsCombined}-Report-Sort_by_size.txt" | awk -F'/' '{print $NF}')
                    recordCount=$(awk '/./{c++} END {print c+0}' ${jobstatsCombined}-csv-written-sort)
                    echo -e "File: ${jobstatsReport}\nRecords: ${recordCount}\n${p3}"
                    head -n 100 ${jobstatsCombined}-Report-Sort_by_size.txt
                fi | tee ${jobstatsCombined}-Report-Summary.txt
                timeout -s 9 10 cp ${jobstatsCombined}-Report-Summary.txt ${reportDir}
                # MSDP - History - jobstats - cleanup
                cleanupFiles="${jobstatsCombined} ${jobstatsCombined}-date_convert ${jobstatsCombined}-csv ${jobstatsCombined}-csv-written ${jobstatsCombined}-Report"
                for fileName in ${cleanupFiles}; do
                    if [ -f ${fileName} ]; then
                        rm ${fileName}
                    fi
                done
                # MSDP - History - jobstats - image size
                echo -e "\n${p1}\nMSDP - Image Size Distribution\n${p1}"
                echo -e "${p2}\nProcessing\n${p2}"
                isdReport=${dedupeFile}-Image_Size_Distribution
                echo -e "Date, Total, OptDupe, <128_kb, <1_mb, <10_mb, <100_mb, <1_gb, <10_gb, <100_gb, <1_tb, <10_tb, <100_tb" 1>${isdReport}.csv
                for jobstatsFile in ${jobstatsFiles}; do
                    echo -e "Processing: ${jobstatsFile}"
                    fileName=$(echo ${jobstatsFile} | awk -F'/' '{print $NF}')
                    total=$(awk '/./{c++} END {print c+0}' ${jobstatsFile})
                    optDup=$(awk '/client=OPT-DUP/{c++} END {print c+0}' ${jobstatsFile})
                    awk -F',' '{print $7}' ${jobstatsFile} | awk -F'=' '{print $2}' 1>${isdReport}.tmp
                    range1=$(awk '$1>=0 && $1<=128' ${isdReport}.tmp | wc -l)
                    range2=$(awk '$1>=128 && $1<=1024' ${isdReport}.tmp | wc -l)
                    range3=$(awk '$1>=1024 && $1<=10240' ${isdReport}.tmp | wc -l)
                    range4=$(awk '$1>=10240 && $1<=102400' ${isdReport}.tmp | wc -l)
                    range5=$(awk '$1>=102400 && $1<=1024000' ${isdReport}.tmp | wc -l)
                    range6=$(awk '$1>=1024000 && $1<=10240000' ${isdReport}.tmp | wc -l)
                    range7=$(awk '$1>=10240000 && $1<=102400000' ${isdReport}.tmp | wc -l)
                    range8=$(awk '$1>=102400000 && $1<=1024000000' ${isdReport}.tmp | wc -l)
                    range9=$(awk '$1>=1024000000 && $1<=10240000000' ${isdReport}.tmp | wc -l)
                    range10=$(awk '$1>=1024000000 && $1<=102400000000' ${isdReport}.tmp | wc -l)
                    echo -e "${fileName}, ${total}, ${optDup}, ${range1}, ${range2}, ${range3}, ${range4}, ${range5}, ${range6}, ${range7}, ${range8}, ${range9}, ${range10}," 1>>${isdReport}.csv
                    if [ -f "${isdReport}.tmp" ]; then
                        rm ${isdReport}.tmp
                    fi
                done  
                column -t -s, ${isdReport}.csv 1>${isdReport}.txt
                echo -e "\n${p2}\nImage Size Distribution\n${p2}"
                cat ${isdReport}.txt
                echo -e "\n\n"
            fi
            msdpDedupeReportComplete=1
        fi
    fi
	logTime
}
# Operation: Report - MSDP - Cloud Storage - OCSD
msdpCloudReport() {
    if [[ -n ${msdpCloudReportComplete} || ${msdpCloudReportComplete} -eq 1 ]]; then
        echo -e "\033[0;31m${p2}\nError - Duplicate Report\n${p2}\n"
        echo -e "Error: MSDP Cloud Report has already been executed.\033[0m\n"
    elif [[ -z ${msdpCloudReportComplete} || ${msdpCloudReportComplete} -eq 0 ]]; then
        if [ -z ${msdpInitComplete} ]; then msdpInit; fi
        echo -e "\n\n\n${p1}\nLHC - Processing - Report: MSDP - Performance - Cloud Storage - OCSD Report\n${p1}"
        # Path
        ocsdLogPath=${logPath}/ocsd_storage
        if [ ! -d ${ocsdLogPath} ]; then
            echo -e "Error: Unable to locate 'ocsd_storage' logs: ${ocsdLogPath}"
            return
        fi
        # Quantity
        ocsdLogCount=45
        # Initialization
        if [ ${msdpHost} -eq 1 ]; then
            ocsdLogList=${msdpFile}/logs-ocsd_storage
            ocsdLogListSort=${msdpFile}/logs-ocsd_storage-sort
            timeout -s 9 120 find ${ocsdLogPath} -type f -name 'ocsd.*.log' 1>${ocsdLogList} 2>/dev/null
            ocsdLogListCount=$(timeout -s 9 10 awk '/./{c++} END {print c+0}' ${ocsdLogList})
            if [[ -n ${ocsdLogListCount} && ${ocsdLogListCount} -gt 0 ]]; then
                timeout -s 9 20 sort -Vr ${ocsdLogList} 1>${ocsdLogListSort}
                ocsdLogs=$(tail -n ${ocsdLogCount} ${ocsdLogListSort} 2>/dev/null)
                ocsdReport=y
            else
                echo -e "Error: Cannot find the 'ocsd_storage' logs."
                ocsdReport=n
            fi
        else
            echo -e "Error: Local host is not a MSDP Storage Server."
            ocsdReport=n
        fi
        if [ ${ocsdReport} == y ]; then
            # Output
            ocsdDir=${msdpFile}/${filePrefix}-MSDP-Cloud-OCSD_Report
            ocsdFile=${ocsdDir}/MSDP-Cloud-OCSD_Report
            mkdir -p ${ocsdDir}
            # Temporary Files
            logdataSample=${ocsdFile}-Log_Data-Sample
            secRange=${ocsdFile}-Log_Data-Parsed
            # OCSD - Report
            echo -e "${p1}\nMSDP - Cloud Storage - OCSD Report\n${p1}" 1>${ocsdFile}-Summary.txt
            # Upload Duration       
            echo -e "${p2}\nMSDP Cloud - Report - Performance - File Upload / Download\n${p2}" | tee -a ${ocsdFile}-Summary.txt
            echo -e "${p3}\nUpload Duration in Seconds\n${p3}" | tee -a ${ocsdFile}-Performance-Upload_Duration.txt
            echo -e "Log, Date, 0-1, 1-2, 2-3, 3-4, 4-5, 5-10, 10-20, 20-30, 30-60, 60+, Total_MB" 1>>${ocsdFile}-Performance-Upload_Duration.csv
            for logFile in ${ocsdLogs}; do
                fileName=$(echo ${logFile} | awk -F'/' '{print $NF}')
                fileDate=$(stat -c "%y" ${logFile} | awk '{print $1}')
                echo -e "Processing: OCSD - Upload Duration - ${fileName}"
                awk -F"\"" '/Upload is done/ {print $20, $16, $17, $10, $12}' ${logFile} | sed 's/,/ /g; s/File size :/Size /g;' 1>${logdataSample}
                msRange=$(grep -c "[0-9]ms$" ${logdataSample})
                minRange=$(grep -c "[0-9]m$\|[0-9]m[0-9]" ${logdataSample})
                totalSizeMB=$(awk -v OFMT="%.2f" '{sum +=$3} END {print sum / 10000000 }' ${logdataSample})
                grep "[0-9]s$" ${logdataSample} | grep -v "[0-9]m.\|[0-9]m[0-9]" | sed 's/.$//g' 1>${secRange}
                awk -v OFS=', ' -v totalSizeMB=${totalSizeMB} -v fileName=${fileName} -v fileDate=${fileDate} -v msRange=${msRange} -v minRange=${minRange} '{
                    if ($NF >= 1 && $NF <= 2) a++;
                    else if ($NF > 2 && $NF <= 3) b++;
                    else if ($NF > 3 && $NF <= 4) c++;
                    else if ($NF > 4 && $NF <= 5) d++;
                    else if ($NF > 5 && $NF <= 10) e++;
                    else if ($NF > 10 && $NF <= 20) f++;
                    else if ($NF > 20 && $NF <= 30) g++;
                    else if ($NF > 30 && $NF <= 60) h++;
                } END {
                    print fileName, fileDate, msRange, a+0, b+0, c+0, d+0, e+0, f+0, g+0, h+0, minRange, totalSizeMB
                }' ${secRange} 1>>${ocsdFile}-Performance-Upload_Duration.csv
            done
            sed 's/,//g' ${ocsdFile}-Performance-Upload_Duration.csv | column -t 1>>${ocsdFile}-Performance-Upload_Duration.txt
            cat ${ocsdFile}-Performance-Upload_Duration.txt 1>>${ocsdFile}-Summary.txt
            echo -e "" | tee -a ${ocsdFile}-Summary.txt
            # Download Duration
            echo -e "${p3}\nDownload Duration in Seconds\n${p3}" | tee -a ${ocsdFile}-Performance-Download_Duration.txt
            echo -e "Log, Date, 0-1, 1-2, 2-3, 3-4, 4-5, 5-10, 10-20, 20-30, 30-60, 60+, Total_MB" 1>>${ocsdFile}-Performance-Download_Duration.csv
            for logFile in ${ocsdLogs}; do
                fileName=$(echo ${logFile} | awk -F'/' '{print $NF}')
                fileDate=$(stat -c "%y" ${logFile} | awk '{print $1}')
                echo -e "Processing: OCSD - Download Duration - ${fileName}"
                awk -F"\"" '/Download is done/ {print $20, $16, $17, $10, $12}' ${logFile} | sed 's/,/ /g; s/File size :/Size /g;' 1>${logdataSample}
                msRange=$(grep -c "[0-9]ms$" ${logdataSample})
                minRange=$(grep -c "[0-9]m$\|[0-9]m[0-9]" ${logdataSample})
                totalSizeMB=$(awk -v OFMT="%.2f" '{sum +=$3} END {print sum / 10000000 }' ${logdataSample})
                grep "[0-9]s$" ${logdataSample} | grep -v "[0-9]m.\|[0-9]m[0-9]" | sed 's/.$//g' 1>${secRange}
                awk -v OFS=', ' -v totalSizeMB=${totalSizeMB} -v fileName=${fileName} -v fileDate=${fileDate} -v msRange=${msRange} -v minRange=${minRange} '{
                    if ($NF >= 1 && $NF <= 2) a++;
                    else if ($NF > 2 && $NF <= 3) b++;
                    else if ($NF > 3 && $NF <= 4) c++;
                    else if ($NF > 4 && $NF <= 5) d++;
                    else if ($NF > 5 && $NF <= 10) e++;
                    else if ($NF > 10 && $NF <= 20) f++;
                    else if ($NF > 20 && $NF <= 30) g++;
                    else if ($NF > 30 && $NF <= 60) h++;
                } END {
                    print fileName, fileDate, msRange, a+0, b+0, c+0, d+0, e+0, f+0, g+0, h+0, minRange, totalSizeMB
                }' ${secRange} 1>>${ocsdFile}-Performance-Download_Duration.csv
            done
            sed 's/,//g' ${ocsdFile}-Performance-Download_Duration.csv | column -t 1>>${ocsdFile}-Performance-Download_Duration.txt
            cat ${ocsdFile}-Performance-Download_Duration.txt 1>>${ocsdFile}-Summary.txt
            echo -e "" | tee -a ${ocsdFile}-Summary.txt
            # OCSD - Report - File Operations
            echo -e "${p2}\nMSDP Cloud - Report - File Operations\n${p2}" | tee ${ocsdFile}-File_Operations-Summary.txt
            echo -e "File, Date, Upload, Download, Delete, Warn, Error" 1>>${ocsdFile}-File_Operations-Detail.csv
            # Process
            for logFile in ${ocsdLogs}; do
                fileName=$(echo ${logFile} | awk -F'/' '{print $NF}')
                fileDate=$(stat -c "%y" ${logFile} | awk '{print $1}')
                echo -e "Processing: OCSD - File Operations - ${fileName}"
                warnCount=$(grep -c 'warn' ${logFile})
                errorCount=$(grep -c 'error' ${logFile})
                uploadCount=$(grep -c 'Upload is done' ${logFile})
                downloadCount=$(grep -c 'Download is done' ${logFile})
                deleteCount=$(grep -c 'Delete is done' ${logFile})
                warnTotal=$((warnTotal + warnCount))
                errorTotal=$((errorTotal + errorCount))
                uploadTotal=$((uploadTotal + uploadCount))
                downloadTotal=$((downloadTotal + downloadCount))
                deleteTotal=$((deleteTotal + deleteCount))
                echo -e "${fileName}, ${fileDate}, ${uploadCount}, ${downloadCount}, ${deleteCount}, ${warnCount}, ${errorCount}" 1>>${ocsdFile}-File_Operations-Detail.csv
            done
            echo -e "Upload, Download, Delete, Warning, Error" 1>${ocsdFile}-File_Operations-Total.csv
            echo -e "${uploadTotal}, ${downloadTotal}, ${deleteTotal}, ${warnTotal}, ${errorTotal}" 1>>${ocsdFile}-File_Operations-Total.csv
            # Report
            echo -e "${p3}\nTotal\n${p3}" 1>${ocsdFile}-File_Operations-Total.txt
            echo -e "Upload: ${uploadTotal}\nDownload: ${downloadTotal}\nDelete: ${deleteTotal}\nWarning: ${warnTotal}\nError: ${errorTotal}" | column -t 1>>${ocsdFile}-File_Operations-Total.txt
            cat ${ocsdFile}-File_Operations-Total.txt 1>>${ocsdFile}-File_Operations-Summary.txt
            echo -e "" 1>>${ocsdFile}-File_Operations-Summary.txt
            echo -e "${p3}\nDetail\n${p3}" 1>${ocsdFile}-File_Operations-Detail.txt
            sed 's/,//g' ${ocsdFile}-File_Operations-Detail.csv | column -t 1>>${ocsdFile}-File_Operations-Detail.txt
            cat ${ocsdFile}-File_Operations-Detail.txt 1>>${ocsdFile}-File_Operations-Summary.txt
            cat ${ocsdFile}-File_Operations-Summary.txt 1>>${ocsdFile}-Summary.txt
            echo -e "" | tee -a ${ocsdFile}-Summary.txt
            # OCSD - Report - Error Messages - Summary
            echo -e "${p2}\nMSDP Cloud - Report - Error Messages - Summary\n${p2}" | tee ${ocsdFile}-Error_Messages-Summary.txt
            if [[ ${errorTotal} -eq 0 && ${warnTotal} -eq 0 ]]; then
                echo -e "Info: No errors present in 'ocsd_storage' log files." | tee -a ${ocsdFile}-Error_Messages-Summary.txt
            elif [[ ${errorTotal} -gt 0 || ${warnTotal} -gt 0 ]]; then
                for logFile in ${ocsdLogs}; do
                    echo -e "Processing: OCSD - Error Messages - ${fileName}"
                    grep -hi "warn\|error" ${logFile} 1>>${logdataSample}
                done
                if [ -f ${logdataSample} ]; then
                    echo -e "Processing: OCSD - Error Messages - Parsing"
                    sed -i 's/,/,\n/g' ${logdataSample}
                    sed -i '/EXTRA\|Extra/d' ${logdataSample}
                    echo -e "Processing: OCSD - Error Messages - Summary"
                    grep "\"message" ${logdataSample} | sort | uniq -c | sort -nr | sed 's/}//g' 1>${ocsdFile}-Error_Messages-List.txt
                    echo -e "Processing: OCSD - Error Messages - Details"
                    sed -i 's/\\n/\n/g' ${logdataSample}
                    grep "RESPONSE Status" ${logdataSample} | sort | uniq -c | sort -nr 1>${ocsdFile}-Error_Messages-Status_Codes.txt
                    if [ -f ${logdataSample} ]; then
                        echo -e "${p3}\nSummary\n${p3}\n${p5}\nErrors\n${p5}"
                        cat ${ocsdFile}-Error_Messages-List.txt
                        echo -e "\n${p5}\nStatus Codes\n${p5}"
                        countCodes=$(awk '/./{c++} END {print c+0}' ${ocsdFile}-Error_Messages-Status_Codes.txt)
                        if [ ${countCodes} -gt 0 ]; then
                            cat ${ocsdFile}-Error_Messages-Status_Codes.txt
                        else
                            echo -e "No HTTP response errors present in 'ocsd_storage' logs."
                        fi
                        echo -e ""
                    fi 1>>${ocsdFile}-Error_Messages-Summary.txt
                fi
            fi
            cat ${ocsdFile}-Error_Messages-Summary.txt 1>>${ocsdFile}-Error_Messages-Report.txt
            cat ${ocsdFile}-Error_Messages-Summary.txt 1>>${ocsdFile}-Summary.txt
            echo -e "\n"
            # OCSD - Report - Error Messages - Detail
            if [ ! -f ${ocsdFile}-Error_Messages-List.txt ]; then
                echo -e "Info: No error messages present in 'Error Messages' report.\n\n"
                errorCount=0
            else
                errorCount=$(awk '/./{c++} END {print c+0}' ${ocsdFile}-Error_Messages-List.txt)
                if [ ${errorCount} -eq 0 ]; then
                    echo -e "No error messages present in 'Error Messages' report.\n\n"
                fi
            fi
            if [ ${errorCount} -gt 0 ]; then
                awk -F"\"" '{print $4}' ${ocsdFile}-Error_Messages-List.txt | awk 'NF' 1>${ocsdFile}-Error_Messages-List-Strings.txt
                errorCount=$(awk '/./{c++} END {print c+0}' ${ocsdFile}-Error_Messages-List-Strings.txt)
            fi
            if [ ${errorCount} -gt 0 ]; then
                echo -e "${p2}\nMSDP Cloud - Report - Error Messages - Detail\n${p2}" 1>${ocsdFile}-Error_Messages-Detail.txt
                while read errorText; do
                    searchString="$(echo ${errorText} | sed 's/\[.*\] //g')"
                    echo -e "${p3}\n${searchString}\n${p3}"
                    for logFile in ${ocsdLogs}; do
                        grep -q "${searchString}" ${logFile}
                        if [ ${?} -eq 0 ]; then
                            echo -e "${logFile}" >> ${ocsdFile}-Errors-Detail-temp.lst
                        fi
                    done
                    oldestError=$(head -n1 ${ocsdFile}-Errors-Detail-temp.lst)
                    newestError=$(tail -n1 ${ocsdFile}-Errors-Detail-temp.lst)
                    echo -e "${p5}\nOldest Message\n${p5}\nFile: ${oldestError}\n${p5}"
                    grep -hi "${searchString}" ${oldestError} 2>/dev/null | head -n1 | sed 's/,/,\n/g;s/\\n/\n/g'
                    echo -e "\n${p5}\nNewest Message\n${p5}\nFile: ${newestError}\n${p5}"
                    grep -hi "${searchString}" ${newestError} 2>/dev/null | tail -n1 | sed 's/,/,\n/g;s/\\n/\n/g'
                    echo -e "\n"
                    if [ -f ${ocsdFile}-Errors-Detail-temp.lst ]; then
                        rm ${ocsdFile}-Errors-Detail-temp.lst
                    fi
                done <${ocsdFile}-Error_Messages-List-Strings.txt 1>>${ocsdFile}-Error_Messages-Detail.txt
                cat ${ocsdFile}-Error_Messages-Detail.txt 1>>${ocsdFile}-Error_Messages-Report.txt
                cat ${ocsdFile}-Error_Messages-Detail.txt 1>>${ocsdFile}-Summary.txt
            fi
            # Report
            cat ${ocsdFile}-Summary.txt
            cp ${ocsdFile}-Summary.txt ${reportDir}
            # Cleanup
            if [ -f ${secRange} ]; then
                rm ${secRange}
            fi
            if [ -f ${logdataSample} ]; then
                rm ${logdataSample}
            fi
        fi
        msdpCloudReportComplete=1
    fi
	logTime
}
# Operation: Report - Performance - Historical
performanceHistoricalReport() {
    if [[ -n ${performanceHistoricalReportComplete} || ${performanceHistoricalReportComplete} -eq 1 ]]; then
        echo -e "\033[0;31m${p2}\nError - Duplicate Report\n${p2}\n"
        echo -e "Error: Performance - Historical Report has already been executed.\033[0m\n"
    elif [[ -z ${performanceHistoricalReportComplete} || ${performanceHistoricalReportComplete} -eq 0 ]]; then
        echo -e "\n\n\n${p1}\nLHC - Processing - Report: Performance - Historical - 30 Days\n${p1}"
        # Error Handling - Check Binary - 'sar'
        sarPath=/bin/sar 
        ${sarPath} 1>/dev/null 2>&1
        sarStatus=${?}
        saPath=/var/log/sa
        if [[ ! -d ${saPath} || ${sarStatus} -gt 0 ]]; then
            if [ ${sarStatus} -ne 0 ]; then
                echo -e "Error: The 'sar' binary returned non-zero exit status. Exit Status ${sarStatus}" | tee -a ${outputDir}/LHC-Error.txt
                echo -e "Error: The 'sar' binary returned non-zero exit status. Check files in data directory: ${saPath}" | tee -a ${outputDir}/LHC-Error.txt
            fi
            if [ ! -d ${saPath} ]; then
                echo -e "\n\nError: The 'sa' directory is missing. Path: ${saPath}" | tee -a ${outputDir}/LHC-Error.txt
            fi
            echo -e "\n\nSkipping System Activity Report (SA Report)...\n"
            saReport=0
        else
            saReport=1
        fi
        # Error Handling - Check Path - '/var/log/sa'
        if [[ ${saReport} -eq 1 && ! -d ${saPath} ]]; then
            echo -e "\n\nError: The 'sysstat' data path '/var/log/sa' does not exist."
            saPath=$(grep "DDIR=" /etc/sysconfig/sysstat | awk -F'=' '{print $2}')
            if [ -z ${saPath} ]; then
                echo -e "\nError: The 'sysstat' data path in '/etc/sysconfig/sysstat' cannot be found ('DDIR=').\n"
                saReport=0
            else
                echo -e "\nInfo: The 'sysstat' data path in '/etc/sysconfig/sysstat' is set ('DDIR=${saPath}').\n"
                saReport=1
            fi
        fi
        # Error Handling - Check Files
        saDataFiles=$(ls -1tr ${saPath}/* 2>/dev/null | grep "sa[0-9]")
        if [ -z "${saDataFiles}" ]; then
            echo -e "\nError: The 'sysstat' data files cannot be found in the '${saPath}' directory.\n"
            saReport=0
        fi
        # Performance - Historical - Processing
        if [ ${saReport} -eq 1 ]; then
            # Make Working Directory
            saDir=${outputDir}/Performance-Historical-30_Days
            saFile=${saDir}/Performance
            mkdir ${saDir}
            if [ ${?} -ne 0 ]; then escape; fi
            # Report Variables
            LANG=en_US
            cpuCores=$(awk '/core id/{c++} END {print c+0}' /proc/cpuinfo)
            memoryTotal=$(awk '/MemTotal/{print $2}' /proc/meminfo)
            kernelRelease=$(timeout -s 9 10 uname -r)
            # Process SA Data
            echo -e "${p2}\nProcessing SA Data\n${p2}"
            for saDataFile in ${saDataFiles}; do
                echo "Processing: ${saDataFile}"
                ${sarPath} -u -f ${saDataFile} 1>>${saFile}-CPU 2>/dev/null
                ${sarPath} -S -f ${saDataFile} 1>>${saFile}-Swap 2>/dev/null
                ${sarPath} -W -f ${saDataFile} 1>>${saFile}-Swap_Stats 2>/dev/null
                ${sarPath} -B -f ${saDataFile} 1>>${saFile}-Paging_Stats 2>/dev/null
                ${sarPath} -r -f ${saDataFile} 1>>${saFile}-Memory 2>/dev/null
                ${sarPath} -dp -f ${saDataFile} 1>>${saFile}-Disk_IO 2>/dev/null
                ${sarPath} -b -f ${saDataFile} 1>>${saFile}-Disk_IO_Stats 2>/dev/null
                ${sarPath} -v -f ${saDataFile} 1>>${saFile}-Kernel-inodes 2>/dev/null
                ${sarPath} -n DEV -f ${saDataFile} 1>>${saFile}-Network 2>/dev/null
                ${sarPath} -n EDEV -f ${saDataFile} 1>>${saFile}-Network-Errors 2>/dev/null
                ${sarPath} -n SOCK -f ${saDataFile} 1>>${saFile}-Network-Sockets 2>/dev/null
                fileDate=$(stat -c "%y" ${saDataFile} | awk '{split($1, a, "-"); print a[2]"/"a[3]"/"a[1]}')
                echo -e "Linux ${kernelRelease} (${hostnameFull})\t${fileDate}\t_x86_64_\t(${cpuCores} CPU)\n12:00:01\tCommitted AS\n" 1>>${saFile}-Memory-Committed_AS
                ${sarPath} -r -f ${saDataFile} 2>/dev/null | grep -v "RESTART\|Average\|mem\|^$\|CPU" | awk -v memoryTotal="${memoryTotal}" '{printf("%s \t%.2f %\n", $1, ($(NF-4))/memoryTotal*100)}' 1>>${saFile}-Memory-Committed_AS
            done
            echo -e "\n${p2}\nProcessing SA Report\n${p2}"
            echo -e "${p3}\nDisk IO - Overview\n${p3}"
            # Disk IO - Overview
            grep -v "x86\|DEV\|Average\|RESTART" ${saFile}-Disk_IO | awk 'NF' 1>${saFile}-Disk_IO-Data
            echo -e "\nDevice Summary: All Devices - Utilization\n" 1>${saFile}-Disk_IO-Historical
            for range in {0..95..5}; do
                echo "Processing: Disk IO - Utilization - Summary: ${range}% Complete..."
                rangeMax=$(echo -e "${range} + 5" | bc -l)
                count=$(awk '$NF >= '${range}' && $NF <= '${rangeMax}' {c++} END {print c+0}' ${saFile}-Disk_IO-Data)
                echo -e "Threshold: ${range}% - ${rangeMax}%      \t Count: ${count}" 1>>${saFile}-Disk_IO-Historical
            done
            # Disk IO - Await Summary
            echo -e "\n${p3}\nDisk IO - Await\n${p3}"
            echo -e "\nDevice Summary: All Devices - Await\n" 1>${saFile}-Disk_IO-Historical-Await
            echo -e "Processing: Disk IO - Await - Low"
            for range in {0..95..5}; do
                minValue=${range}
                maxValue=$(expr ${range} + 5)
                rangeCount=$(awk '$(NF-2) >= '${minValue}' && $(NF-2) <= '${maxValue}' {c++} END {print c+0}' ${saFile}-Disk_IO-Data)
                echo -e "Threshold: ${minValue} - ${maxValue} ms       \t Count: ${rangeCount}"
            done 1>>${saFile}-Disk_IO-Historical-Await
            echo -e "Processing: Disk IO - Await - Medium"
            for range in {100..900..100}; do
                minValue=${range}
                maxValue=$(expr ${range} + 100)
                rangeCount=$(awk '$(NF-2) >= '${minValue}' && $(NF-2) <= '${maxValue}' {c++} END {print c+0}' ${saFile}-Disk_IO-Data)
                echo -e "Threshold: ${minValue} - ${maxValue} ms       \t Count: ${rangeCount}"
            done 1>>${saFile}-Disk_IO-Historical-Await
            echo -e "Processing: Disk IO - Await - High"
            for range in {1000..19000..1000}; do
                minValue=${range}
                maxValue=$(expr ${range} + 1000)
                rangeCount=$(awk '$(NF-2) >= '${minValue}' && $(NF-2) <= '${maxValue}' {c++} END {print c+0}' ${saFile}-Disk_IO-Data)
                echo -e "Threshold: ${minValue} - ${maxValue} ms       \t Count: ${rangeCount}" | awk '!/Count: 0/'
            done 1>>${saFile}-Disk_IO-Historical-Await
            cat ${saFile}-Disk_IO-Historical-Await
            # Disk IO - Device Reports
            echo -e "\n${p3}\nDisk IO - Device Reports\n${p3}"
            diskInventory=$(awk '{print $2}' ${saFile}-Disk_IO | sort -u | grep -v "LINUX\|DEV\|x86_64\|\bAM\b\|\bPM\b\|loop" | awk 'NF' | tr '\n' ' ')
            sdDisks=$(echo ${diskInventory} | tr ' ' '\n' | grep "\bsd[a-z]" | tr '\n' ' ')
            devDisks=$(echo ${diskInventory} | tr ' ' '\n' | grep "\bdev[0-9]" | tr '\n' ' ')
            devDisksAdd=$(echo ${diskInventory} | tr ' ' '\n' | grep "\bdev-[0-9]" | tr '\n' ' ')
            diskList=$(echo ${diskInventory} | tr ' ' '\n' | grep -v "\bsd[a-z]\|dev[0-9]\|dev-[0-9]" | tr '\n' ' ')
            echo -e "Disk_Inventory: ${diskInventory}\nSD_Disks: ${sdDisks}\nDev_Disks: ${devDisks}\nDev_Disks_Ext: ${devDisksAdd}\nDisk List: ${diskList}" 1>${saFile}-Disk_IO-Device_List
            if [ -z "${diskList}" ]; then
                diskList=$(echo ${sdDisks} | tr ' ' '\n' | head -n8)
            fi
            if [ -n "${diskList}" ]; then
                for diskName in ${diskList}; do
                    # Disk IO - Utilization
                    echo "Processing: Disk IO - ${diskName}"
                    grep "x86\|\sDEV\s\|\s${diskName}\s" ${saFile}-Disk_IO 1>${saFile}-Disk_IO-${diskName}
                    grep -v "x86\|DEV\|Average\|RESTART" ${saFile}-Disk_IO-${diskName} | awk 'NF' 1>${saFile}-Disk_IO-${diskName}-data
                    echo -e "\nDevice Summary: ${diskName}\n" 1>>${saFile}-Disk_IO-${diskName}-Summary
                    for range in {0..95..5}; do
                        count=$(awk '$NF >= '${range}' && $NF <= '${range}+4.99' {c++} END {print c+0}' ${saFile}-Disk_IO-${diskName}-data)
                        echo -e "Threshold: ${range}%    \t Count: ${count}"
                    done 1>>${saFile}-Disk_IO-${diskName}-Summary
                    # Disk IO - Await
                    echo -e "\nDevice Summary: ${diskName}\n" 1>${saFile}-Disk_IO-${diskName}-Await
                    for range in {0..95..5}; do
                        minValue=${range}
                        maxValue=$(expr ${range} + 5)
                        rangeCount=$(awk '$(NF-2) >= '${minValue}' && $(NF-2) <= '${maxValue}' {c++} END {print c+0}' ${saFile}-Disk_IO-${diskName}-data)
                        echo -e "Threshold: ${minValue} - ${maxValue} ms       \t Count: ${rangeCount}"
                    done 1>>${saFile}-Disk_IO-${diskName}-Await
                    midPass=$(awk '$(NF-2) >= '100' {c++} END {print c+0}' ${saFile}-Disk_IO-${diskName}-data)
                    if [ ${midPass} -gt 1 ]; then
                        awaitWarn="${awaitWarn} ${diskName}"
                        for range in {100..475..25}; do
                            minValue=${range}
                            maxValue=$(expr ${range} + 25)
                            rangeCount=$(awk '$(NF-2) >= '${minValue}' && $(NF-2) <= '${maxValue}' {c++} END {print c+0}' ${saFile}-Disk_IO-${diskName}-data)
                            echo -e "Threshold: ${minValue} - ${maxValue} ms       \t Count: ${rangeCount}"
                        done | awk '!/Count: 0/' 1>>${saFile}-Disk_IO-${diskName}-Await
                    fi
                    highPass=$(awk '$(NF-2) >= '500' {c++} END {print c+0}' ${saFile}-Disk_IO-${diskName}-data)
                    if [ ${highPass} -gt 1 ]; then
                        echo -e "Disk IO Await Summary: ${diskName} - WARN: HIGH DISK AWAIT TIME" | tee -a ${saFile}-Disk_IO-${diskName}-Await-Alert
                        awaitCrit="${awaitCrit} ${diskName}"
                        for range in {500..20000..500}; do
                            minValue=${range}
                            maxValue=$(expr ${range} + 500)
                            rangeCount=$(awk '$(NF-2) >= '${minValue}' && $(NF-2) <= '${maxValue}' {c++} END {print c+0}' ${saFile}-Disk_IO-${diskName}-data)
                            echo -e "Threshold: ${minValue} - ${maxValue} ms       \t Count: ${rangeCount}"
                        done | awk '!/Count: 0/' 1>>${saFile}-Disk_IO-${diskName}-Await
                    fi
                    if [ -f ${saFile}-Disk_IO-${diskName}-data ]; then
                        rm ${saFile}-Disk_IO-${diskName}-data
                    fi
                done
            fi
            echo -e "\n${p3}\nNetwork\n${p3}"
            # Network - Device Report
            if [ -f ${saFile}-Network ]; then
                nicList=$(grep Average ${saFile}-Network | awk '{print $2}' | sort -uV)
            fi
            # Network - Device Summary
            if [ -n "${nicList}" ]; then
                for nicName in ${nicList}; do
                    echo "Processing: Network - ${nicName}";
                    grep "x86\|\sIFACE\s\|\s${nicName}\s" ${saFile}-Network 1>${saFile}-Network-${nicName}
                    grep -v "x86\|CPU\|Average\|RESTART\|IFACE" ${saFile}-Network-${nicName} | grep [0-9] | awk 'NF' 1>${saFile}-Network-${nicName}-data
                    echo -e "\nDevice Summary: ${nicName}\n" 1>${saFile}-Network-${nicName}-Summary
                    for range in {0..90000..10000}; do
                        minValue=${range}
                        maxValue=$(expr ${range} + 10000)
                        recvCount=$(awk '$(NF-4) >= '${minValue}' && $(NF-4) <= '${maxValue}' {c++} END {print c+0}' ${saFile}-Network-${nicName}-data)
                        txCount=$(awk '$(NF-3) >= '${minValue}' && $(NF-3) <= '${maxValue}' {c++} END {print c+0}' ${saFile}-Network-${nicName}-data)
                        echo -e "Threshold: ${minValue} - ${maxValue} KB/s       \t Receive: ${recvCount}       \t Transmit: ${txCount}"
                    done | sed '/Receive: 0.*.Transmit: 0/d' 1>>${saFile}-Network-${nicName}-Summary
                    for range in {100000..4900000..100000}; do
                        minValue=${range}
                        maxValue=$(expr ${range} + 100000)
                        recvCount=$(awk '$(NF-4) >= '${minValue}' && $(NF-4) <= '${maxValue}' {c++} END {print c+0}' ${saFile}-Network-${nicName}-data)
                        txCount=$(awk '$(NF-3) >= '${minValue}' && $(NF-3) <= '${maxValue}' {c++} END {print c+0}' ${saFile}-Network-${nicName}-data)
                        echo -e "Threshold: ${minValue} - ${maxValue} KB/s       \t Receive: ${recvCount}       \t Transmit: ${txCount}"
                    done | sed '/Receive: 0.*.Transmit: 0/d' 1>>${saFile}-Network-${nicName}-Summary
                    if [ -f ${saFile}-Network-${nicName}-data ]; then
                        rm ${saFile}-Network-${nicName}-data
                    fi
                    # Error Reports
                    grep "x86\|\sIFACE\s\|\s${nicName}\s" ${saFile}-Network-Errors 1>${saFile}-Network-${nicName}-Errors
                done
            fi
            echo -e "\n${p3}\nSummary\n${p3}"
            # Host Performance Metrics
            echo "Processing: SA Report - Host Performance Metrics";
            echo -e "Vx - Host Performance Summary - ${hostnameFull}\n" 1>${saFile}-Host_Performance_Metrics.txt
            echo -e "The 'Mem_Commit' value shows memory allocated by active processes as a percentage of RAM + Swap.\n\nThe 'Mem_Util' value includes memory used by 'File System Cache' for optimization of Disk IO (released on request).\n" 1>>${saFile}-Host_Performance_Metrics.txt
            grep -v "x86\|CPU\|Average\|RESTART" ${saFile}-CPU | awk 'NF' 1>${saFile}-CPU-Data
            grep -v "x86\|CPU\|Average\|RESTART" ${saFile}-Swap | awk 'NF' 1>${saFile}-Swap-Data
            grep -v "x86\|CPU\|Average\|RESTART" ${saFile}-Memory | awk 'NF' 1>${saFile}-Memory-Data
            for range in {0..100..5}; do
                rangeMax=$(echo -e "${range} + 4.99" | bc -l)
                cpuUse=$(awk '100-$NF <= '${range}' && 100-$NF >= '${range}-4.99' {count++} END {if (count == 0) print 0; else print count}' ${saFile}-CPU-Data)
                swapUse=$(awk '$(NF-2) >= '${range}' && $(NF-2) <= '${rangeMax}' {count++} END {if (count == 0) print 0; else print count}' ${saFile}-Swap-Data)
                memUse=$(awk '$(NF-7) >= '${range}' && $(NF-7) <= '${rangeMax}' {count++} END {if (count == 0) print 0; else print count}' ${saFile}-Memory-Data)
                commitUse=$(awk '$(NF-3) >= '${range}' && $(NF-3) <= '${rangeMax}' {count++} END {if (count == 0) print 0; else print count}' ${saFile}-Memory-Data)
                ioWait=$(awk '$(NF-2) >= '${range}' && $(NF-2) <= '${rangeMax}' {count++} END {if (count == 0) print 0; else print count}' ${saFile}-CPU-Data)
                echo -e "Threshold: ${range}%   \t CPU_Util: ${cpuUse}    \t Swap_Util: ${swapUse}     \t Mem_Util: ${memUse}    \t Mem_Commit: ${commitUse}    \t IO_Wait: ${ioWait}";
            done 1>>${saFile}-Host_Performance_Metrics.txt;
            # Host Performance Metrics - Memory - Committed AS
            echo "Processing: SA Report - Memory - Committed AS"
            echo -e "The 'Committed AS' value represents the memory required to prevent 'Out of Memory' ('OOM') events.\n\nThis report shows 'Commited AS' as a percentage of the Physical Memory." 1>${saFile}-Memory-Committed_AS-Summary.txt
            grep "%" ${saFile}-Memory-Committed_AS 1>${saFile}-Memory-Committed_AS-data
            for range in {0..250..5}; do
                count=$(awk -v var="${range}" '$(NF-1) >= var && $(NF-1) <= var+4.99 {count++} END {print (count ? count : 0)}' ${saFile}-Memory-Committed_AS-data);
                echo -e "Threshold: ${range}%   \t Count: ${count}" 1>>${saFile}-Memory-Committed_AS-Summary-Full.txt
            done
            awk '!/Count: 0/' ${saFile}-Memory-Committed_AS-Summary-Full.txt 1>${saFile}-Memory-Committed_AS-Summary.txt
            cp ${saFile}-Memory-Committed_AS-Summary.txt ${reportDir}
            # SA Report - Summary
            if [ -f ${saFile}-Host_Performance_Metrics.txt ]; then
                echo -e "Processing: SA Report - Report Summary"
                saReportSummary=${saFile}-Summary.txt
                # SA Report - Host Performance Metrics
                echo -e "\n${p1}\nSA Report - Host Performance Metrics\n${p1}" 1>>${saReportSummary}
                cat ${saFile}-Host_Performance_Metrics.txt 1>>${saReportSummary}
                # SA Report - Host Performance Metrics - Committed AS
                echo -e "\n\n${p1}\nSA Report - Memory - Committed AS\n${p1}\n" 1>>${saReportSummary}
                cat ${saFile}-Memory-Committed_AS-Summary.txt 1>>${saReportSummary}
                # SA Report - Disk IO - Utilization
                echo -e "\n\n${p1}\nSA Report - Disk IO - Utilization\n${p1}" 1>>${saReportSummary}
                echo -e "The % Utilization values may be higher than expected for Multi-Path Devices.\n\nReview storage 'await' time to evaluate performance." 1>>${saReportSummary}
                cat ${saFile}-Disk_IO-Historical 1>>${saReportSummary}
                # SA Report - Disk IO - Await
                echo -e "\n\n${p1}\nSA Report - Disk IO - Await\n${p1}" 1>>${saReportSummary}
                cat ${saFile}-Disk_IO-Historical-Await 1>>${saReportSummary}
                # SA Report - Network Performance
                echo -e "\n\n${p1}\nSA Report - Network Performance\n${p1}" 1>>${saReportSummary}
                nicSummaries=$(find ${saFile}-Network-*-Summary -type f -size +111c 2>/dev/null)
                nicCounter=$(echo ${nicSummaries} | awk '{print $1}')
                if [ -n "${nicCounter}" ]; then
                    for nicSummary in ${nicSummaries}; do
                        nicName=$(grep "Device Summary:" ${nicSummary} | awk '{print $NF}')
                        echo -e "\n${p2}\nNetwork Interface - Summary - ${nicName}\n${p2}"
                        cat ${nicSummary}
                        echo -e ""
                    done 1>>${saReportSummary}
                else
                    echo -e "\nNetwork Interfaces do not have activity above 25 MB/s.\n\nPlease review the reports for further details:\n" 1>>${saReportSummary}
                    find ${saFile}-Network-* ! -name '*Errors' ! -name '*-Summary' ! -name '*-Sockets' 1>>${saReportSummary} 2>/dev/null
                fi
                # SA Report - Disk Performance - Utilization
                echo -e "\n\n${p1}\nSA Report - Disk IO Utilization\n${p1}" 1>>${saReportSummary}
                diskSummaries=$(find ${saFile}-Disk_IO-*-Summary -type f -size +642c 2>/dev/null)
                checkSummary=$(echo ${diskSummaries} | awk '{print $1}')
                if [ -n ${checkSummary} ]; then
                    for diskSummary in ${diskSummaries}; do
                        deviceName=$(grep "Device Summary:" ${diskSummary} | awk '{print $NF}')
                        echo -e "\n${p2}\nDisk IO - Summary - ${deviceName}\n${p2}"
                        cat ${diskSummary}
                        echo -e "\n"
                    done 1>>${saReportSummary}
                else
                    echo -e "\nNo devices with significant 'Disk IO' levels. View individual reports for more details.\n" 1>>${saReportSummary}
                    ls -1tr ${saFile}-Disk_IO-*-Summary 2>/dev/null | awk -F'/' '{print $NF}' 1>>${saReportSummary}
                fi
                # SA Report - Disk Performance - Await
                echo -e "\n\n${p1}\nSA Report - Disk IO Await\n${p1}" 1>>${saReportSummary}
                awaitSummaries=$(echo ${awaitWarn} ${awaitCrit} | tr ' ' '\n' | sort -u)
                checkSummary=$(echo ${awaitSummaries} | awk '{print $1}')
                if [ -n ${checkSummary} ]; then
                    for awaitSummary in ${awaitSummaries}; do
                        deviceName=$(grep "Device Summary:" ${saFile}-Disk_IO-${awaitSummary}-Await | awk '{print $NF}')
                        echo -e "${p2}\nDisk IO - Await - ${deviceName}\n${p2}"
                        cat ${saFile}-Disk_IO-${awaitSummary}-Await
                        echo -e "\n"
                    done 1>>${saReportSummary}
                else
                    echo -e "\nNo devices with significant 'Disk Await' times. View individual reports for more details.\n" 1>>${saReportSummary}
                    ls -1tr ${saFile}-Disk_IO-*-Await 2>/dev/null | awk -F'/' '{print $NF}' 1>>${saReportSummary}
                fi
            fi
            # SA Report - Cleanup
            echo "Processing: SA Report - Cleanup"
            cp ${saReportSummary} ${reportDir}
            cleanupFiles="${saFile}-CPU-Data ${saFile}-Swap-Data ${saFile}-Memory-Data ${saFile}-Memory-Committed_AS-data"
            for fileName in ${cleanupFiles}; do
                if [ -f ${fileName} ]; then
                    rm ${fileName}
                fi
            done
            # SA Report - Collect Data Files
            if [ -d /var/log/sa ]; then
                cd /var/log/sa
                echo -e "Processing: SA Report - Compressing '/var/log/sa'"
                saReportFiles=$(ls -1tr /var/log/sa/ | grep "sa[0-9]")
                tar czf ${saDir}/Sysstat-SA_Files.tar.gz ${saReportFiles}
                cd ${outputPath}
            fi
        fi
        performanceHistoricalReportComplete=1
        logTime
        performanceHistoricalDisplayReport
    fi
}
# Operation: Report - Performance - Historical Summary - Display
performanceHistoricalDisplayReport() {
    saDir=${outputDir}/Performance-Historical-30_Days
    if [[ -d ${saDir} ]]; then
        echo -e "\n\n${p1}\nSA Report - Host Performance Metrics\n${p1}\n"
        cat ${saFile}-Host_Performance_Metrics.txt
        # Memory - Commited AS
        echo -e "\n\n${p1}\nSA Report - Memory - Committed AS\n${p1}\n"
        cat ${saFile}-Memory-Committed_AS-Summary.txt
        # Network Performance
        echo -e "\n\n${p1}\nSA Report - Network - Performance Summary\n${p1}"
        if [ -n "${nicSummaries}" ]; then
            for nicSummary in ${nicSummaries}; do 
                nicName=$(echo ${nicSummary} | awk -F"/" '{print $NF}')
                echo -e "${p2}\n${nicName}\n${p2}"
                cat ${nicSummary}
                echo -e ""
            done
        else
            echo -e "\nNetwork Interfaces do not show any historical activity.\n\nPlease review the reports for further detail.\n"
            find ${saFile}-Network-* ! -name '*Errors' ! -name '*-Summary' ! -name '*-Sockets' 2>/dev/null
        fi
        # Disk IO - Utilization
        echo -e "\n\n${p1}\nSA Report - Disk IO - Utilization\n${p1}" 1>>${saReportSummary}
        cat ${saFile}-Disk_IO-Historical 1>>${saReportSummary}
    fi
	logTime
}
# Operation: Report - Performance - Snapshot
performanceSnapshotReport() {
    if [[ -n ${performanceSnapshotReportComplete} || ${performanceSnapshotReportComplete} -eq 1 ]]; then
        echo -e "\033[0;31m${p2}\nError - Duplicate Report\n${p2}\n"
        echo -e "Error: Performnace - Snapshot Report has already been executed.\033[0m\n"
    elif [[ -z ${performanceSnapshotReportComplete} || ${performanceSnapshotReportComplete} -eq 0 ]]; then
        echo -e "\n\n\n${p1}\nLHC - Processing - Report: Performance - Snapshot - 60 Seconds\n${p1}"
        echo -e "${p2}\nData Capture\n${p2}"
        # Output Directory - Snapshot
        snapPath=${outputDir}/Performance-Snapshot-60_Seconds
        snapFile=${snapPath}/Snapshot
        mkdir ${snapPath}
        timeout -s 9 10 iostat -d 1>${snapFile}-devices
        runIOstat=iostat_-x_1_60
        runIFstat=ifstat_-t_1_60
        runVMstat=vmstat_-t_-w_1_60
        runDstat=dstat_-t_-c_-p_-n_-d_-r_-m_-s_-g_--vm_--socket_--tcp
        echo -e "Start: Capture Disk IO"
        echo -e "Start: Capture Network IO"
        echo -e "Start: Capture Network Queue"
        echo -e "Start: Capture Memory Statistics"
        # Start Snapshot - Telemetry
        nohup timeout -s 9 65 nice iostat -x 1 60 1>${snapFile}-${runIOstat} 2>/dev/null &
        nohup timeout -s 9 65 nice ifstat -t 1 60 1>${snapFile}-${runIFstat} 2>/dev/null &
        nohup timeout -s 9 65 nice vmstat -t -w 1 60 1>${snapFile}-${runVMstat} 2>/dev/null &
        nohup timeout -s 9 65 dstat -t -c -p -n -d -r -m -s -g --vm --socket --tcp --nocolor 1 60 1>${snapFile}-${runDstat} 2>/dev/null &
        echo -e "\nWaiting for data collection... (60 seconds)\n"
        # Start Snapshot - Netstat
        netstatFile=${snapFile}-netstat-full
        mkdir ${netstatFile}
        if [ -f /bin/netstat ]; then
            for i in {0..60}; do
                epochTime=$(date +%s)
                timeout -s 9 2 /bin/netstat -anopt 1>${netstatFile}/netstat-full-${epochTime} 2>/dev/null
                sleep 0.9
            done
        else
            sleep 60
        fi
        # Status 
        echo -e "Complete: Capture Memory Statistics"
        echo -e "Complete: Capture Network Queue"
        echo -e "Complete: Capture Network IO"
        echo -e "Complete: Capture Disk IO"
        # Post Processing
        echo -e "\n${p2}\nData Processing\n${p2}"
        # Post Process - Disk IO - Device
        ioCount=$(awk '/./{c++} END {print c+0}' ${snapFile}-${runIOstat})
        if [ ${ioCount} -gt 1 ]; then
            echo -e "${p3}\nDisk IO\n${p3}"
            deviceReport=${snapFile}-iostat-device_reports
            mkdir ${deviceReport}
            timeout -s 9 10 iostat -d 1>${snapFile}-devices
            deviceNames=$(awk '!/Device:/ && !/Linux/ && NF{print $1}' ${snapFile}-devices)
            if [ -n "${deviceNames}" ]; then
                for deviceName in ${deviceNames}; do 
                    echo -e "Processing: Disk IO - ${deviceName}"
                    grep Linux ${snapFile}-${runIOstat} -A4 1>>${deviceReport}/${deviceName}
                    echo -e "Device:         rrqm/s   wrqm/s     r/s     w/s    rkB/s    wkB/s avgrq-sz avgqu-sz   await r_await w_await  svctm  %util" 1>>${deviceReport}/${deviceName}
                    grep "^${deviceName}\s" ${snapFile}-${runIOstat} 1>>${deviceReport}/${deviceName}
                done
            fi
            echo -e ""
        fi
        # Post Process - Netstat
        if [ -f /bin/netstat ]; then
            # Timeseries Report
            echo -e "${p3}\nNetwork\n${p3}"
            echo -e "Processing: Netstat - Timeseries Report"
            epochFiles=$(ls -1tr ${netstatFile}/netstat-full-* 2>/dev/null)
            epochFirst=$(echo ${epochFiles} | awk '{print $1}') 
            epochStart=$(stat -c "%z %n" ${epochFirst} | cut -d' ' -f1)
            cpuCores=$(awk '/core id/{c++} END {print c+0}' /proc/cpuinfo)
            kernelRelease=$(timeout -s 9 10 uname -r)
            echo -e "Linux ${kernelRelease} (${hostnameFull})\t${epochStart}\t_x86_64_\t(${cpuCores} CPU)\n\nTime \t\t Recv-Q \t Send-Q" 1>>${snapFile}-netstat-queue-timeseries_report.txt
            for epochFile in ${epochFiles}; do
                epochTime=$(echo ${epochFile} | awk -F'-' '{print $NF}')
                epochDate=$(date +%H:%M:%S -d @${epochTime})
                queueSize=$(grep ^tcp ${epochFile} | awk '{recvSum+=$2; sendSum+=$3} END {print recvSum / 1024,"    \t ", sendSum / 1024 }' OFMT="%.2f")
                echo -e "${epochDate} \t ${queueSize}" 1>>${snapFile}-netstat-queue-timeseries_report.txt
            done
            cp ${snapFile}-netstat-queue-timeseries_report.txt ${reportDir}
            # Snapshot Reports
            echo -e "Processing: Netstat - Snapshot Reports"
            queueReport=${snapFile}-netstat-queue_reports
            mkdir -p ${queueReport}/send ${queueReport}/recv
            for epochFile in ${epochFiles}; do
                epochTime=$(echo ${epochFile} | awk -F'-' '{print $NF}')
                grep ^tcp ${epochFile} | sort -nrk3 1>${queueReport}/send/${epochTime}-tcp-send-q
                grep ^tcp ${epochFile} | sort -nrk2 1>${queueReport}/recv/${epochTime}-tcp-recv-q
            done
            # Process Reports
            if [ ${msdpHost} -eq 1 ]; then
                echo -e "Processing: Netstat - Snapshot Reports - MSDP Services"
                msdpSnap=${snapFile}-netstat-msdp_processes
                mkdir -p ${msdpSnap}/spad ${msdpSnap}/spoold ${msdpSnap}/ocsd ${msdpSnap}/vpfsd
                psCheck_spoold=$(pidof spoold | wc -l)
                psCheck_spad=$(pidof spad | wc -l)
                psCheck_ocsd=$(pidof ocsd | wc -l)
                psCheck_vpfsd=$(pidof vpfsd | wc -l)
                for epochFile in ${epochFiles}; do
                    epochTime=$(echo ${epochFile} | awk -F'-' '{print $NF}')
                    if [ ${psCheck_spoold} -eq 1 ]; then grep "^tcp.*spoold" ${epochFile} | sort -nrk2 1>${msdpSnap}/spoold/netstat-spoold-${epochTime}; fi
                    if [ ${psCheck_spad} -eq 1 ]; then grep "^tcp.*spad" ${epochFile} | sort -nrk2 1>${msdpSnap}/spad/netstat-spad-${epochTime}; fi
                    if [ ${psCheck_ocsd} -eq 1 ]; then grep "^tcp.*ocsd" ${epochFile} | sort -nrk2 1>${msdpSnap}/ocsd/netstat-ocsd-${epochTime}; fi
                    if [ ${psCheck_vpfsd} -eq 1 ]; then grep "^tcp.*vpfsd" ${epochFile} | sort -nrk2 1>${msdpSnap}/vpfsd/netstat-vpfsd-${epochTime}; fi
                done
            fi
        fi
        performanceSnapshotReportComplete=1
    fi
	logTime
}
# Operation: Report - Notifications
notificationReport() {
    if [ ${genericHost} -eq 1 ]; then
        echo -e "\n\n\n${p1}\nLHC - Processing - Report: Notifications\n${p1}"
        # Notification: NetBackup - License and Registration Keys - Expired
        if [[ ${nbuHost} -eq 1 && -f ${nbuFile}/bpminlicense-verbose-list_keys-expired ]]; then
            echo -e "${p2}\nNetBackup - License and Registration Keys - Expired\n${p2}\n"
            cat ${nbuFile}/bpminlicense-verbose-list_keys-expired
            echo -e "\n"
        fi
        # Notification: NetBackup - Log Level - bp.conf - HIGH
        if [ -f ${nbuFile}/configuration-bp.conf-verbose ]; then
            verboseCount=$(timeout -s 9 10 awk '/VERBOSE/{c++} END {print c+0}' ${nbuFile}/configuration-bp.conf-verbose)
            if [ ${verboseCount} -gt 0 ]; then
                echo -e "${p2}\nNetBackup - Log Level - bp.conf\n${p2}"
                cat ${nbuFile}/configuration-bp.conf-verbose
                timeout -s 9 30 awk '/VERBOSE/' ${nbuFile}/configuration-bp.conf-verbose | while read setting eq value; do
                    if [ ${value} -gt 2 ]; then
                        echo -e "\nWARNING: Found increased NetBackup Log Level: ${setting} ${eq} ${value}" | tee -a ${nbuFile}/configuration-bp.conf-verbose-ALERT.txt
                    fi
                done
                echo -e ""
            fi
        fi
        # Notification: Memory Allocation - Host/OS
        if [[ -d ${saDir} && -f ${saFile}-Memory-Committed_AS ]]; then
            echo -e "${p2}\nMemory Utilization - Historical\n${p2}"
            memoryMax=$(awk '/%/{a[$0]=$(NF-1)} END {n=asort(a); for (i=n; i>n-1; i--) print a[i]}' ${saFile}-Memory-Committed_AS)
            memoryExhaustion=$(awk '/%/ && $(NF-1) >= 100 {count++} END {print count+0}' ${saFile}-Memory-Committed_AS)
            memoryExhaustionTime=$(echo -e "${memoryExhaustion} * 10" | bc -l)
            echo -e "Host/OS Report - Memory Maximum: ${memoryMax} %\nHost/OS Report - Memory 100%+: ${memoryExhaustion} events\nHost/OS Report - Memory 100%+: ${memoryExhaustionTime} minutes"
        fi
        # Notification: Memory Allocation - NetBackup
        nbuMemSummary=${memoryReport}/Summary-netbackup-process-memory-total
        if [[ ${nbuHost} -eq 1 && -f ${nbuMemSummary} ]]; then
            echo -e "\n${p2}\nMemory Allocation - Current\n${p2}"
            cat ${nbuMemSummary}
        fi
        # Notification: Memory Allocation - AutoSupport
        asMemSummary=${memoryReport}/Summary-autosupport-memory-total
        if [[ ${nbApp} -eq 1 && -f ${asMemSummary} ]]; then
            cat ${asMemSummary}
        fi
        # Notification: Kernel - Messages Log
        if [[ -n ${msgCombined} && -f ${msgCombined} ]]; then
            calltraceCount=$(awk '/Call Trace:/{c++} END {print c+0}' ${msgFile}-Call_Trace-List)
            if [ ${calltraceCount} -gt 0 ]; then
                # Notification: Kernel - Call Trace
                echo -e "\n${p2}\nLinux - Error - Call Trace messages\n${p2}";
                calltraceReport=$(echo -e "${msgFile}-Call_Trace-List" | awk -F'/' '{print $NF}')
                echo -e "Count: ${calltraceCount} \t File: ${calltraceReport}\n"
                awk '/Call Trace/{a[++n]=$0} END {for(i=n-4;i<=n;i++) print a[i]}' ${msgFile}-Call_Trace-List
            fi
            # Notification: Corruption - File System messages
            fsckCount=$(awk '/./{c++} END {print c+0}' ${msgFile}-File_System-Events-run_fsck)
            if [ ${fsckCount} -gt 0 ]; then
                echo -e "\n${p2}\nStorage - Corruption - File System messages\n${p2}";
                fsckReport=$(echo -e "${msgFile}-File_System-Events-run_fsck" | awk -F'/' '{print $NF}')
                echo -e "Count: ${fsckCount} \t File: ${fsckReport}\n"
                tail -n 15 ${msgFile}-File_System-Events-run_fsck
            fi
        fi
        # Notification: MSDP - Corruption - Affected Backup List
        if [[ -d ${msdpFile} ]]; then
            if [ -f ${msdpFile}/catdbutil-corrupt-parsed ]; then
                corruptCount=$(awk '/./{c++} END {print c+0}' ${msdpFile}/catdbutil-corrupt-parsed)
                if [ ${corruptCount} -gt 0 ]; then
                    echo -e "\n${p2}\nAlert - MSDP - Corruption - Catalog Report\n${p2}";
                    catalogReport=$(echo -e "${msdpFile}/catdbutil-corrupt-parsed" | awk -F'/' '{print $NF}')
                    echo -e "Count: ${corruptCount} \t File: ${catalogReport}\n"
                    tail -n 15 ${msdpFile}/catdbutil-corrupt-parsed
                fi
            fi
            if [ -f ${msdpFile}/datacheck-affectedbackup.lst-count ]; then
                affectedCount=$(awk '/./{c++} END {print c+0}' ${msdpFile}/datacheck-affectedbackup.lst-count)
                if [ ${affectedCount} -gt 0 ]; then
                    echo -e "\n${p2}\nAlert - MSDP - Corruption - Affected Backup List\n${p2}";
                    backupReport=$(echo -e "${msdpFile}/datacheck-affectedbackup.lst-count" | awk -F'/' '{print $NF}')
                    echo -e "Count: ${affectedCount} \t File: ${backupReport}\n"
                    tail -n 15 ${msdpFile}/datacheck-affectedbackup.lst-count
                fi
            fi
            if [ -f ${msdpFile}/checkcrcd-errors-full ]; then
                errorCount=$(awk '/./{c++} END {print c+0}' ${msdpFile}/checkcrcd-errors-full)
                if [ ${errorCount} -gt 0 ]; then
                    echo -e "\n${p2}\nAlert - MSDP - Corruption - CheckCRCd Report\n${p2}";
                    checkcrcdReport=$(echo -e "${msdpFile}/checkcrcd-errors-full" | awk -F'/' '{print $NF}')
                    echo -e "Count: ${errorCount} \t File: ${checkcrcdReport}\n"
                    tail -n 15 ${msdpFile}/checkcrcd-errors-full
                fi
            fi
            if [ -f ${msdpFile}/pddecfg-listcloudlsu.err-cloud.json ]; then
                echo -e "\n${p2}\nAlert - MSDP - Cloud - LSU Errors\n${p2}";
                echo -e "Error may indicate improper decommissioning of Cloud LSU."
                cat ${msdpFile}/pddecfg-listcloudlsu.err-cloud.json
            fi
        fi
    fi | tee ${outputDir}/Notifications.txt
    echo -e "\n\n"
	logTime
}
# Operation: Archive
createArchive() {
    echo -e "\n\n\n${p1}\nLHC - Processing - Creating Archive\n${p1}"
    echo -e "${p3}\nProcessing\n${p3}"
    echo -e "Processing: Collate report files"
    cd ${reportDir}
    fileList=$(timeout -s 9 10 ls -1)
    for fileName in ${fileList}; do
        fileNameNew=$(echo ${fileName} | sed 's/\.txt//g')
        timeout -s 9 5 mv ${fileName} ${filePrefix}-${fileNameNew}-${fileSuffix}.txt
    done
    echo -e "Processing: Collect process log"
    timeout -s 9 5 mv ${psLog} ${reportDir} 2>/dev/null
    echo -e "$(echo -e "CTime,,, Date,,, Time,,, Elapsed,,, Runtime,,, Function,,," | awk '{print; gsub(/[^ ]/,"="); print}')\n$(cat ${outputDir}/LHC-Log.csv)" | sed 's/,//g' | column -t 1>${outputDir}/LHC-Log.txt
    echo -e "Processing: Set file permissions"
    timeout -s 9 120 chmod -R +666 ${outputDir}
    echo -e "Processing: Compress report files"
    cd ${outputPath}
    lhcDir=$(echo ${outputDir} | awk -F'/' '{print $NF}')
    tar czf ${outputDir}.tgz ${lhcDir}
    echo -e "\nDone.\n"
    echo -e "\n${p3}\nUpload Instructions\n${p3}"
    echo -e "\nPlease upload the report archive to the Veritas Support Portal.\n\nReport Files: ${outputDir}\n\nReport Archive: ${outputDir}.tgz\n\n\n"
    createArchiveComplete=1
}
# End: Operations
# Begin: Processes
# Process: MSDP - Compaction
msdpCompactionProcess() {
    if [ ${msdpHost} -eq 0 ]; then
        echo -e "Error: Local host is not a MSDP Storage Server."
    elif [ ${msdpHost} -eq 1 ]; then
        if [ -z ${msdpInitComplete} ]; then msdpInit; fi
        echo -e "\n${p1}\nLHC - Process - MSDP: Compaction\n${p1}"
        echo -e "${p3}\nInitialization\n${p3}"
        if [[ -z "${dataPaths}" ]]; then
            echo -e "\nError: Cannot find Data Path(s), invalid '/etc/pdregistry.cfg'.\n"
        else
            echo -e "Found MSDP Configuration and Data Path(s).\n\nMSDP Configuration: ${etcPath}\nMSDP Logs: ${logPath}\n"
            echo -e "${p4}\nData Paths\n${p4}"
            echo -e "${dataPaths}"
        fi
        echo -e "\n\n${p2}\nCompaction Setting\n${p2}"
        echo -e "\nThere are two types of compaction which can be run against MSDP Storage.\n\nOptions:"
        echo -e "\t all - used to reclaim space within MSDP Data Containers.\n\t check - used to look for segment loss within MSDP Data Containers"
        echo -e "\n\nEnter an option...\n"; read compactType; echo -e "\n"
        if [[ -z "${compactType}" || "${compactType}" != @(check|all) ]]; then
            echo -e "Error: Invalid option has been entered. Please enter 'check' or 'all' at the prompt."
        elif [[ -n ${compactType} && "${compactType}" == @(check|all) ]]; then
            echo -e "${p2}\nFingerprint Cache Load\n${p2}"
            echo -e "\nThe MSDP Fingerprint Cache Load must be complete before starting compaction.\n\nIf the MSDP Services were recently restarted, ensure Fingerprint Cache Load has completed.\n"
            echo -e "\n${p3}\nService Startup\n${p3}"
            timeout -s 9 20 grep "Startup.*occurred" $(echo -e ${spooldLogs} | tail -n 5) | grep -v "\[" | tail
            echo -e "\n${p3}\nFP Cache Load\n${p3}"
            timeout -s 9 20 grep "cacheLoadMain" $(echo -e ${spooldLogs} | tail -n 5) | tail
            echo -e "\n${p3}\nFP Cache Complete\n${p3}"
            timeout -s 9 20 grep "cache transition" $(echo -e ${spooldLogs} | tail -n 10) | tail
            echo -e "\n\nDo you want to start the MSDP Compaction process? (y/n)\n"; read compactStart; echo -e "\n"
            if [[ -n ${compactStart} && ${compactStart} != "y" ]]; then
                echo -e "\nExiting.\n"
            elif [[ -n ${compactStart} && ${compactStart} == "y" ]]; then
                echo -e "${p2}\nProcessing\n${p2}"
                echo -e "${p3}\nCreate Touch Files\n${p3}"
                if [[ -n ${compactType} && ${compactType} == "check" ]]; then
                    for dataPath in ${dataPaths}; do
                        touchFiles+="${dataPath}/compaction.check "
                    done
                    touchFilesCount=$(ls -l ${touchFiles} 2>/dev/null | wc -l)
                    if [ ${touchFilesCount} -gt 0 ]; then
                        echo -e "Touch files already exist for the following volumes:\n"
                        ls -l ${touchFiles} | tee ${msdpFile}/compaction-touch_files
                        echo -e "\n\nExiting.\n"
                        escape
                    else
                        touch ${touchFiles}
                        ls -l ${touchFiles}
                    fi
                fi
                if [[ -n ${compactType} && ${compactType} == "all" ]]; then
                    for dataPath in ${dataPaths}; do
                        touchFiles+="${dataPath}/compaction.all "
                    done
                    touchFilesCount=$(ls -l ${touchFiles} 2>/dev/null | wc -l)
                    if [ ${touchFilesCount} -gt 0 ]; then
                        echo -e "Touch files already exist for the following volumes:\n"
                        ls -l ${touchFiles} | tee ${msdpFile}/compaction-touch_files
                        echo -e "\n\nExiting.\n"
                        escape
                    elif [ ${touchFilesCount} -eq 0 ]; then
                        touch ${touchFiles}
                        ls -l ${touchFiles}
                    fi
                fi
                echo -e "\n${p3}\nStart Compaction\n${p3}"
                echo -e "Starting compaction process..."
                /usr/openv/pdde/pdcr/bin/crcontrol --compactstart 0 0
                compactExit=${?}
                if [ ${compactExit} -eq 0 ]; then
                    echo -e "Starting compaction process... Done."
                elif [ ${compactExit} -ne 0 ]; then
                    echo -e "\nMSDP Compaction failed to start.\n\nPlease run the command manually:\n\n\t/usr/openv/pdde/pdcr/bin/crcontrol --compactstart 0 0"
                fi
                if [[ -n ${compactType} && ${compactType} == "check" ]]; then
                    echo -e "\n${p3}\nAffected Backup List\n${p3}"
                    echo -e "Creating backup of current Affected Backup List:"
                    timeout -s 9 10 cp ${dbPath}/datacheck/AffectedBackup.lst ${dbPath}/datacheck/AffectedBackup.lst-${sourceDate}-${sourceTime}
                    timeout -s 9 10 ls -l ${dbPath}/datacheck/AffectedBackup.lst ${dbPath}/datacheck/AffectedBackup.lst-${sourceDate}-${sourceTime}
                    echo -e "\n\nWhen complete check the 'AffectedBackup.lst' file for results."
                fi
                echo -e "\n${p3}\nMonitor Compaction\n${p3}"
                echo -e "Use the commands shown below to monitor the compaction process:\n"
                echo -e "/usr/openv/pdde/pdcr/bin/crcontrol --compactstate | grep \"Compaction busy\"\n\n"
                echo "for fileName in \$(find ${logPath}/spoold/ -type f -name 'compactd_node_*' -mmin -15); do echo -e \"\n\n\${fileName}\n\"; grep -i \"compaction\" \${fileName} | tail; done\n\n"
                escape
            fi
        fi
    fi
	logTime
}
# Process: Log Collection - nbcplogs
nbcplogsProcess() {
    echo -e "\n${p1}\nLHC - Process - Log Collection: nbcplogs\n${p1}"
    echo -e "${p3}\nLog Duration Option\n${p3}"
    echo -e "\nThis option defines the duration for which logs should be collected.\n\n\nEntering the value '1h' will collect logs from the past hour.\n\nEntering '1d' will collect logs from the past day.\n"
    echo -e "\nExample:\n\t 1h - 1 Hour\n\t 3h - 3 Hours\n\t 9h - 9 Hours\n\t 1d - 1 Day\n\t 2d - 2 Days\n"; read logDuration
    echo -e "\n\n${p3}\nRunning 'nbcplogs'\n${p3}"
    /usr/openv/netbackup/bin/support/nbcplogs --duration ${logDuration} --no-nbsu ${outputPath}/${sourceDate}-${hostnameShortForce}-nbcplogs-${logDuration}-${sourceTime} --tmpdir=${outputPath} --bundle
    if [ ${?} -ne 0 ]; then
        echo -e "\nError: Failed execution of the 'nbcplogs' utility."
    else
        echo -e "\nLog collection complete.."
        echo -e "\n\n${p3}\nCompressing Logs\n${p3}"
        echo -e "\nCompressing file..."
        gzip ${outputPath}/${sourceDate}-${hostnameShortForce}-nbcplogs-${logDuration}-${sourceTime}.tar
        echo -e "\nFile compression complete.\n\nPlease upload the file to Veritas Support:"
        ls -lh ${outputPath}/${sourceDate}-${hostnameShortForce}-nbcplogs-${logDuration}-${sourceTime}.tar.gz
    fi
	logTime
}
# Process: Log Collection - NBSU
nbsuProcess() {
    echo -e "\n${p1}\nLHC - Process - Log Collection: NBSU\n${p1}"
    if [ ${nbuHost} -eq 0 ]; then
        echo -e "Error: Local host is not a NetBackup Server."
    elif [ ${nbuHost} -eq 1 ]; then
        echo -e "${p3}\nRunning 'nbsu'\n${p3}"
        cd ${outputPath}
        /usr/openv/netbackup/bin/support/nbsu
    fi
	logTime
}
# Process: Log Collection - MSDP
msdpLogsProcess () {
    if [ ${msdpHost} -eq 0 ]; then
        echo -e "Error: Local host is not a MSDP Storage Server."
    elif [ ${msdpHost} -eq 1 ]; then
        if [ -z ${msdpInitComplete} ]; then msdpInit; fi
        echo -e "\n${p1}\nLHC - Process - Log Collection: MSDP\n${p1}"
        echo -e "${p3}\nInitialization\n${p3}"  
        if [[ -z ${logPath} || ! -d ${logPath} ]]; then
            echo -e "\nError: Cannot find Log Path, invalid '/etc/pdregistry.cfg'.\n"
        else
            echo -e "Found MSDP Configuration and Log Path.\n\nMSDP Configuration: ${etcPath}\nMSDP Logs: ${logPath}\n\n"
            echo -e "${p3}\nLog Duration Option\n${p3}"
            echo -e "\nCollect logs from the past using number of \"minutes\" or \"days?\"\n"
            echo -e "Options:\n\t minutes\n\t days\n"; read logDuration
            if [ ${logDuration} == "minutes" ]; then
                echo -e "\n\nEnter number of minutes to collect logs...\n"; read logDuration; 
                tar czvf ${outputPath}/${sourceDate}-Veritas-${hostnameShortForce}-MSDP-Logs-${logDuration}_minute-${sourceTime}.tgz $(find {${logPath},/var/log/puredisk,/var/log/vpfs} -type f -mmin -${logDuration}) /var/log/puredisk/*install* ${dbPath}/datacheck ${etcPath} /usr/openv/lib/ost-plugins/*.c* /usr/openv/pdde/pdag/*.conf /usr/openv/pdde/pdcr/etc/
                echo -e "\n\nLog collection complete.\n\n\nPlease upload the logs to Veritas Support:\n"
                ls -lh ${outputPath}/${sourceDate}-Veritas-${hostnameShortForce}-MSDP-Logs-${logDuration}_minute-${sourceTime}.tgz
            elif [ ${logDuration} == "days" ]; then
                echo -e "\n\nEnter number of days to collect logs...\n"; read logDuration; 
                tar czvf ${outputPath}/${sourceDate}-Veritas-${hostnameShortForce}-MSDP-Logs-${logDuration}_day-${sourceTime}.tgz $(find {${logPath},/var/log/puredisk,/var/log/vpfs} -type f -mtime -${logDuration}) /var/log/puredisk/*install* ${dbPath}/datacheck ${etcPath} /usr/openv/lib/ost-plugins/*.c* /usr/openv/pdde/pdag/*.conf /usr/openv/pdde/pdcr/etc/
                echo -e "\n\nLog collection complete.\n\n\nPlease upload the logs to Veritas Support:\n"
                ls -lh ${outputPath}/${sourceDate}-Veritas-${hostnameShortForce}-MSDP-Logs-${logDuration}_day-${sourceTime}.tgz
            fi
            echo -e ""
        fi
    fi
	logTime
}
# Process: MSDP - Process Trace - Generic
hostStackTraceProcess() {
    echo -e "\n${p1}\nLHC - Process - Stack Trace: MSDP\n${p1}"
    # Exit if container
    if [[ ${appInst} -eq 1 ]]; then
        echo -e "${p3}\nError: Container\n${p3}"
        echo -e "Error: Cannot run strack trace within container. Run at node level."
        return 9
    fi
    # Process IDs
    echo -e "${p3}\nProcess IDs\n${p3}"
    echo -e "Processing: spad"
    spadPID=$(pidof spad)
    if [[ ${?} -ne 0 || -z "${spadPID}" ]]; then
        echo -e "Error: Unable to get Process ID for 'spad'."
        return 9
    fi
    echo -e "Processing: spad"
    spooldPID=$(pidof spoold)
    if [[ ${?} -ne 0 || -z "${spooldPID}" ]]; then
        echo -e "Error: Unable to get Process ID for 'spad'."
        return 9
    fi
    echo -e "Process ID - 'spad': ${spadPID}\nProcess ID - 'spoold': ${spooldPID}\n"
    # Settings
    echo -e "${p3}\nSettings\n${p3}"
    msdpTraceDir=${outputDir}/${sourceDate}-MSDP-Process_Trace-${sourceTime}
    delaySeconds=10
    mkdir ${msdpTraceDir}
    echo -e "Output: ${msdpTraceDir}\nDelay: 10s\nRounds: 20\n"
    # Collect Trace
    echo -e "${p3}\nCollect Trace\n${p3}"
    if [[ -n "${spadPID}" && -n "${spooldPID}" ]]; then
        for pass in {1..20}; do
            echo -e "Processing: Round: ${pass}..."
            currentEpoch=$(date +%s); currentEpochLong=$(date +%Hh_%Mm_%Ss)
            lsof -p ${spadPID} &> ${msdpTraceDir}/lsof_output-spad-Round_${pass}-${currentEpoch}-${currentEpochLong}
            lsof -p ${spooldPID} &> ${msdpTraceDir}/lsof_output-spoold-Round_${pass}-${currentEpoch}-${currentEpochLong}
            gstack ${spadPID} &> ${msdpTraceDir}/gstack_output-spad-Round_${pass}-${currentEpoch}-${currentEpochLong}
            gstack ${spooldPID} &> ${msdpTraceDir}/gstack_output-spoold-Round_${pass}-${currentEpoch}-${currentEpochLong}
            timeout -s 9 10 /usr/openv/pdde/pdcr/bin/crcontrol --taskstat 0 1 &> ${msdpTraceDir}/taskstat-Round_${pass}-${currentEpoch}-${currentEpochLong}
            timeout -s 9 10 /usr/openv/pdde/pdcr/bin/cacontrol --rep query &> ${msdpTraceDir}/rep_query-Round_${pass}-${currentEpoch}-${currentEpochLong}
            echo -e "Processing: Round: ${pass}... Done.  Waiting ${delaySeconds} seconds."
            sleep ${delaySeconds}
        done
    fi
	logTime
}
# Process: MSDP - Process Trace - Containers
containerStackTraceProcess() {
    echo -e "\n"
	logTime
}
# End: Processes
# Start: Reports
# Report: complete
complete() {
    echo -e "${p1}\nLHC - Processing - Report: Complete\n${p1}"
    echo -e "${p3}\nOption: ${mainOpt}\n${p3}"
    echo -e "Command: ${bin} ${mainOpt}\n"
    runComplete
}
partial() {
    echo -e "${p1}\nLHC - Processing - Report: Partial\n${p1}"
    echo -e "${p3}\nOption: ${mainOpt}\n${p3}"
    echo -e "Command: ${bin} ${mainOpt}\n"
    setOptions
    runOptions
}
# Report: memory
memory() {
    if [[ -n "${memoryReportComplete}" && "${memoryReportComplete}" -eq 1 ]]; then
        echo -e "\033[0;31m${p2}\nError - Duplicate Report\n${p2}\n"
        echo -e "Error: Memory Report has already been executed.\033[0m\n"
    elif [[ -z "${memoryReportComplete}" ]]; then
        memoryReport
        memoryReportComplete=1
    fi
}
# Report: network
network() {
    if [[ -n "${networkReportComplete}" && "${networkReportComplete}" -eq 1 ]]; then
        echo -e "\033[0;31m${p2}\nError - Duplicate Report\n${p2}\n"
        echo -e "Error: Network Report has already been executed.\033[0m\n"
    elif [ -z "${networkReportComplete}" ]; then
        networkReport
        networkReportComplete=1
    fi
}
# Report: storage
storage() {
    if [[ -n "${storageReportComplete}" && "${storageReportComplete}" -eq 1 ]]; then
        echo -e "\033[0;31m${p2}\nError - Duplicate Report\n${p2}\n"
        echo -e "Error: Storage Report has already been executed.\033[0m\n"
    elif [ -z "${storageReportComplete}" ]; then
        storageReport
        storageReportComplete=1       
    fi
}
# Report: appliance
appliance() {
    if [[ -n "${applianceReportComplete}" && "${applianceReportComplete}" -eq 1 ]]; then
        echo -e "\033[0;31m${p2}\nError - Duplicate Report\n${p2}\n"
        echo -e "Error: Appliance Report has already been executed.\033[0m\n"
    elif [ -z "${applianceReportComplete}" ]; then
        echo -e "\n\n\n${p1}\nLHC - Processing - Report: Appliance\n${p1}"
        echo -e "${p3}\nOption: ${mainOpt}\n${p3}"
        echo -e "Command: ${bin} ${mainOpt}\n"
        if [[ ${nbApp} -eq 1 ]]; then
            nbuApplianceReport
        elif [[ ${flexApp} -eq 1 && ${appInst} -eq 0 ]]; then
            containerReport
            flexApplianceReport
        elif [[ ${nbfsApp} -eq 1 && ${appInst} -eq 0 ]]; then
            containerReport
            nbfsApplianceReport
        elif [[ ${accessApp} -eq 1 && ${appInst} -eq 0 ]]; then
            containerReport
            # accessApplianceReport
        fi
        vcsApplianceReport
        ipmiApplianceReport
        applianceReportComplete=1
    fi
}
# Report: trace
trace() {
    echo -e "\n${p1}\nLHC - Process - Stack Trace\n${p1}"
    echo -e "${p3}\nOption: ${mainOpt}\n${p3}"
    echo -e "Command: ${bin} ${mainOpt}\n"
    hostStackTraceProcess
}
# Report: compress
compress() {
    notificationReport
    createArchive
}
# Report: escape
escape() {
    exit
}
# Report: quit
quit() {
    # Check Archive
    if [ -z "${createArchiveComplete}" ]; then compress; fi
    exit
}
# End: Reports
# Start: Menu
# Menu: redirect
redirect() {
    if [ "${menuPersist}" -eq 1 ]; then
        unset mainOpt
    else
        quit
    fi
}
# Menu: os
osMenu() {
    until [ "${subOpt}" = "back" ]; do
        echo -e "\n\n\n${p1}\nLHC - Processing - Report: OS\n${p1}"
        echo -e "${p3}\nOption: ${mainOpt}\n${p3}"
        echo -e "Command: ${bin} ${mainOpt}\n"
        echo -e "\n${p3}\nReport Options: ${mainOpt}\n${p3}"
        optsOS="complete overview configuration messages back quit"
        echo -e "\nEnter 'complete' to run all available reports.\n\nEnter a report option to run a specific report.\n"
        echo -e "\nOptions:"; for opt in ${optsOS}; do echo -e "\t ${opt}"; done
        echo -e "\n\nEnter an option...\n"; read subOpt; echo -e "\n${subOpt}\n"
        case ${subOpt} in
            complete ) osOverviewReport; osConfigurationReport; osMessagesReport;;
            overview ) osOverviewReport;;
            configuration ) osConfigurationReport;;
            messages ) osMessagesReport;; 
            back ) redirect;;
            quit ) quit;;
            * ) echo -e "\033[0;31m${p2}\nError - Invalid Option\n${p2}\nPlease enter a valid option.\033[0m\n";
        esac
    done
}
# Menu: performance
performanceMenu() {
    until [ "${subOpt}" = "back" ]; do
        echo -e "\n\n\n${p1}\nLHC - Processing - Report: Performance\n${p1}"
        echo -e "${p3}\nOption: ${mainOpt}\n${p3}"
        echo -e "Command: ${bin} ${mainOpt}\n"
        echo -e "\n${p3}\nReport Options: ${mainOpt}\n${p3}"
        optsPerf="complete historical snapshot back quit"
        echo -e "\nEnter 'complete' to run all available reports.\n\nEnter the name of the option to run a specific report.\n"
        echo -e "\nOptions:"; for opt in ${optsPerf}; do echo -e "\t ${opt}"; done
        echo -e "\n\nEnter an option...\n"; read subOpt; echo -e "\n${subOpt}\n"
        case ${subOpt} in
            complete ) performanceHistoricalReport; performanceSnapshotReport; redirect;;
            historical ) performanceHistoricalReport; redirect;;
            snapshot ) performanceSnapshotReport; redirect;;
            back ) redirect;;
            quit ) quit;;
            * ) echo -e "\033[0;31m${p2}\nError - Invalid Option\n${p2}\nPlease enter a valid option.\033[0m\n"; redirect;;
        esac
    done
}
# Menu: netbackup
netbackupMenu() {
    until [ "${subOpt}" = "back" ]; do
        echo -e "\n\n\n${p1}\nLHC - Processing - Report: NetBackup\n${p1}"
        echo -e "${p3}\nOption: ${mainOpt}\n${p3}"
        echo -e "Command: ${bin} ${mainOpt}\n"
        echo -e "\n${p3}\nReport Options: ${mainOpt}\n${p3}"
        optsNBU="complete environment configuration slp back quit"
        echo -e "\nEnter 'complete' to run all available reports.\n\nEnter the name of the option to run a specific report.\n"
        echo -e "\nOptions:"; for opt in ${optsNBU}; do echo -e "\t ${opt}"; done
        echo -e "\n\nEnter an option...\n"; read subOpt; echo -e "\n${subOpt}\n"
        case ${subOpt} in
            complete ) nbuEnvironmentReport; nbuConfigurationReport;;
            environment ) nbuEnvironmentReport;;
            configuration ) nbuConfigurationReport;;
            slp ) nbuSLPReport;;
            back ) redirect;;
            quit ) quit;;
            * ) echo -e "\033[0;31m${p2}\nError - Invalid Option\n${p2}\nPlease enter a valid option.\033[0m\n"; redirect;;
        esac
    done
}
# Menu: msdp
msdpMenu() {
    until [ "${subOpt}" = "back" ]; do
        echo -e "\n\n\n${p1}\nLHC - Processing - Report: MSDP\n${p1}"
        echo -e "${p3}\nOption: ${mainOpt}\n${p3}"
        echo -e "Command: ${bin} ${mainOpt}\n"
        echo -e "\n${p3}\nReport Options: ${mainOpt}\n${p3}"
        optsMSDP="complete overview dedupe cloud performance compaction back quit"
        echo -e "\nEnter 'complete' to run all available reports.\n\nEnter the name of the option to run a specific report.\n"
        echo -e "\nOptions:"; for opt in ${optsMSDP}; do echo -e "\t ${opt}"; done
        echo -e "\n\nEnter an option...\n"; read subOpt; echo -e "\n${subOpt}\n"
        case ${subOpt} in
            complete ) msdpOverviewReport; msdpDedupeReport; msdpCloudReport; redirect;;
            overview ) msdpOverviewReport; redirect;;
            dedupe ) msdpDedupeReport; redirect;;
            cloud ) msdpCloudReport; redirect;;
            performance ) msdpSessionReport; redirect;;
            compaction ) msdpCompactionProcess; redirect;;
            back ) redirect;;
            quit ) quit;;
            * ) echo -e "\033[0;31m${p2}\nError - Invalid Option\n${p2}\nPlease enter a valid option.\033[0m\n"; redirect;;
        esac
    done
}
# Menu: logs
logsMenu() {
    until [ "${subOpt}" = "back" ]; do
        echo -e "\n\n\n${p1}\nLHC - Processing - Operation: Log Collection\n${p1}"
        echo -e "${p3}\nOption: ${mainOpt}\n${p3}"
        echo -e "Command: ${bin} ${mainOpt}\n"
        echo -e "\n${p3}\nReport Options: ${mainOpt}\n${p3}"
        optsOS="nbcplogs nbsu msdp back quit"
        echo -e "\nEnter 'complete' to run all available reports.\n\nEnter a report option to run a specific report.\n"
        echo -e "\nOptions:"; for opt in ${optsOS}; do echo -e "\t ${opt}"; done
        echo -e "\n\nEnter an option...\n"; read subOpt; echo -e "\n${subOpt}\n"
        case ${subOpt} in
            nbcplogs ) nbcplogsProcess; redirect;;
            nbsu ) nbsuProcess;;
            msdp ) msdpLogsProcess; redirect;;
            back ) redirect;;
            quit ) quit;;
            * ) echo -e "\033[0;31m${p2}\nError - Invalid Option\n${p2}\nPlease enter a valid option.\033[0m\n"; redirect;;
        esac
    done
}
# Menu: main
mainMenu() {
    if [[ -z "${outputDir}" && -n "${mainOpt}" ]]; then
        echo -e "\n\n${p0}\nVeritas - NetBackup - LHC - Linux Health Check - v${lhcVersion}\n${p0}"
        setOutput
    fi
    until [ "${mainOpt}" = "quit" ]; do
        echo -e "\n\n${p0}\nVeritas - NetBackup - LHC - Linux Health Check - v${lhcVersion}\n${p0}"
        if [ -n ${subOpt} ]; then unset subOpt; fi
        if [ -z "${mainOpt}" ]; then 
            echo -e "${p2}\nMain Menu\n${p2}"
            echo -e "\nThe Linux Health Check utility reports Host/OS, Application, and Performance Data.\n\nAn archive will be created with the results upon completion.\n"
            if [ -z "${outputDir}" ]; then setOutput; fi
            # echo "\nAn option can be specified when running the './Vx-LHC' command.\n"
            # echo -e "Examples:"; for opt in ${optsMain}; do echo -e "\t ./Vx-LHC ${opt}"; done
            echo -e "${p3}\nOptions\n${p3}"
            echo -e "\nEnter the 'complete' option to run all available reports.\n\nEnter the 'partial' option or the 'name' of a report to select reports.\n"
            echo -e "\nType:\n\t complete - execute all available reports\n\t partial - prompt to select reports"
            echo -e "\nOption:"; for opt in ${optsMain}; do echo -e "\t ${opt}"; done
            echo -e "\n\nEnter an option...\n"; read mainOpt; echo -e "\n${mainOpt}\n"
        fi
        case ${mainOpt} in
            complete ) complete;;
            partial ) partial;;
            os ) osMenu;;
            netbackup ) netbackupMenu;;
            msdp ) msdpMenu;;
            performance ) performanceMenu;;
            memory ) memory; redirect;;
            storage ) storage; redirect;;
            network ) network; redirect;;
            appliance ) appliance; redirect;;
            logs ) logsMenu;;
            trace ) trace; redirect;;
            compress ) compress; redirect;;
            quit ) quit;;
            * ) echo -e "\033[0;31m${p2}\nError - Invalid Option\n${p2}\nPlease enter a valid option.\033[0m\n"; redirect;;
        esac
    done
}
mainMenu
