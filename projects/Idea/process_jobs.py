#!/usr/bin/env python
#
# $Log: process_jobs.py,v $
# Revision 1.64  2017/01/30 22:59:38  pweaver # added status 196 limit has been reached output file # added waiting for resources msgs output file
# Revision 1.63  2017/01/30 16:34:55  pweaver # corrected how the job start time was being captured; had incorrectly assumed the primary job start time field was the beginning, but discovered this can actually be later than the 1st job try start time.
# Revision 1.62  2017/01/28 02:51:33  pweaver # still working on the job start times in the heatmaps when the last line of the job dump is not the oldest timestamp, though it is the oldest jobid.
# Revision 1.61  2017/01/27 20:56:50  pweaver # removed an extra control character that got into the file on line 444
# Revision 1.60  2017/01/27 20:53:27  pweaver # updated bptm delay calculation to allow for 2 digit years if a 4 digit year is not found in the date field.
# Revision 1.59  2017/01/27 19:58:32  pweaver # needed to int type the elapsed time in the slowest 20 backups greater than 5 minutes.
# Revision 1.58  2017/01/27 19:10:32  pweaver # corrected how the oldest start timestamp was being defined.  Had assumed that the oldest job would have the oldest start time but several job dumps from clients have proven that assumption false.
# Revision 1.57  2017/01/26 14:38:29  pweaver # changed the first line to be more Linux/Unix friendly since it doesn't matter on Windows
# Revision 1.56  2017/01/26 14:10:34  pweaver # corrected an assumption that in replication jobs a pid # only appeared for 1 replicating backup images; discovered a pid could be appear for more than 1 backup image on very busy media servers or in a job that has 100s of images
# Revision 1.55  2017/01/25 21:36:46  pweaver # modified the filename used if creating a new file is needed.
# Revision 1.54  2017/01/25 21:07:28  pweaver # added replication image start time, end time, and difference/elapsed to the report on replications
# Revision 1.53  2017/01/25 15:42:31  pweaver # modified the csv.writer to remove the extra line feeds in the jobsummary csv file, when run on a Windows server.  Updated the spinner some more as well.
# Revision 1.52  2017/01/25 03:14:53  pweaver # added in a workaround for a bug in the job database when a job is created but has no data.  Also expanded the use of the spinner.
# Revision 1.51  2017/01/24 04:19:53  pweaver # bug fix in the printing of the headers in the policy_heatmap
# Revision 1.50  2017/01/24 04:02:22  pweaver # added spinner to give visual of progress when dealing with job data containing multiple 10,000s of jobs.  Also condensed the comments/rcs update lines to trim it's number of lines.
# Revision 1.49  2017/01/24 02:59:54  pweaver # bug fix: had been using the overall job status for the status of each try; this has been corrected now.
# Revision 1.48  2017/01/24 01:50:07  pweaver # add again in the policy_heatmap
# Revision 1.47  2017/01/24 01:48:33  pweaver # forgot a trailing | in the stu_heatmap
# Revision 1.46  2017/01/24 01:46:14  pweaver # fixed a bug in the STU heatmap and also change the total count to be like the policy_heatmap of failure/total counts
# Revision 1.45  2017/01/23 21:11:05  pweaver # corrected the stu and policy heatmaps to account for jobs failing without a job try, like for a status 237. also added a sort for the heatmap columns
# Revision 1.44  2017/01/23 18:53:41  pweaver # removed debugging line forgotten with the previous update
# Revision 1.43  2017/01/23 16:51:39  pweaver # added count for air import images
# Revision 1.42  2017/01/22 22:28:53  pweaver # added the policy failure/total heatmap
# Revision 1.41  2017/01/21 23:27:21  pweaver # modified the job try end time variable to account for a zero value, meaning the job had not terminated when the collection was made.
# Revision 1.40  2017/01/21 22:37:25  pweaver # removed the extra _total_ column from the STU heatmap and also corrected the storage unit parsing when a STU name contained a hyphen (-)
# Revision 1.39  2017/01/21 18:52:34  pweaver # added a STU usage heatmap by checking every job that has a storage unit defined then mapping, per job try, each try's start and end time.  This should calculate as a range, not just end points if a job try spans more than 1 heatmap_interval.  This is 99% complete.  Remaining is to eliminate one of the 2 totals columns per row - maybe.
# Revision 1.38  2017/01/18 21:11:05  pweaver # made script better timezone aware and started the frameware for a STU heatmap, of jobs running every 15 minutes per stu
# Revision 1.37  2017/01/16 22:01:30  pweaver # added DSSU Staging policy number, modified the output directory of patool on Windows, added secondary sort keys to some of the reports
# Revision 1.36  2017/01/16 16:49:30  pweaver # updated the reged_combine_runonlines regex expression to account for  W:\\DIR00[01]\\
# Revision 1.35  2017/01/14 01:15:35  pweaver # added --input_nbsu to take a compressed nbsu from the master server, extract the files, parse out the CSV portion of the NBU_jobs.txt file, and use this output as the input to the program.  requires the patool library
# Revision 1.34  2017/01/11 21:37:52  pweaver # corrected MSDP replication regex expressions to account for FQDNs instead of just short names
# Revision 1.33  2017/01/05 20:48:20  pweaver # added throughput summary by policy name added a job count column to the media server and stu throughput summaries
# Revision 1.32  2017/01/03 22:06:38  pweaver # bug fix in min replication dedup calc fixed to allow for 0.00 deduplication rates
# Revision 1.31  2016/12/21 22:37:15  pweaver # corrected recipients processing for email routine
# Revision 1.30  2016/12/21 21:10:31  pweaver # updated the tarfile name to be more reflective of the input file for easier distinction, corrected a missing column heading in the alljobsummary csv file, and added error correction to the email routine.
# Revision 1.29  2016/12/21 16:53:36  pweaver # added encryption and decryption routines and updated the email section accordingly, plus adjusted the replication report formatting a touch
# Revision 1.28  2016/12/20 21:04:15  pweaver # minor corrections - changed the email subject to be more descriptive of what it really is
# Revision 1.27  2016/12/20 18:16:04  pweaver # added command line options for better processing, including emailing output files, compressing output files, generating bpdbjobs output when on the master server.  also corrected misspelling of Throughput on a couple of reports
# Revision 1.26  2016/12/15 21:04:42  pweaver # corrected vmware datastore collection, added initial hyper-v counting, updated vmware transport type to account for windows backup host, added inital hyper-v count
# Revision 1.25  2016/12/15 16:50:16  pweaver # corrected Status codes > 1 report; had Qyt and it was misspelled plus should have been the Error code (now Code)
# Revision 1.24  2016/12/15 16:30:22  pweaver # added Job policy type breakdown overall, by media server, and by storage unit
# Revision 1.23  2016/12/07 22:30:48  pweaver # changed slowest completed backup reports to only report on jobs that had KB written - so we won't see all or mostly parent jobs since they always report 0KB written
# Revision 1.22  2016/12/05 22:34:23  pweaver # updated vmware reporting code to v2, added exit status column to top 20 reports, changed check for accelerator stats existence
# Revision 1.21  2016/12/02 22:50:11  pweaver # added ver 1 of VMware reporting - added vCenter server list and ESX hosts list
# Revision 1.20  2016/12/02 20:19:20  pweaver # added accelerator stats and output file, renamed some of the other output files to include the unixtimestamp, and reformatted a few columns
# Revision 1.19  2016/12/01 23:12:22  pweaver # adjusted for jobs with more than 1 attempt and adjusted the reports on performance for media servers and storage units.
# Revision 1.18  2016/11/30 19:13:29  pweaver # updated Report on Replication deduplication percentages to make sure report is only run when MSDP replication jobs exist
# Revision 1.17  2016/11/30 19:02:57  pweaver # added reports for media server throughput and stu throughput - works for 7.7.x jobs here but is off for 7.6.x.x jobs right now
# Revision 1.16  2016/11/30 16:22:45  pweaver # correct the max, min values in the replication deduplication percentages report
# Revision 1.15  2016/11/30 16:18:12  pweaver # updated the msdprepdb to correctly assoicate the PDDO Stats line with the backup id while excluding PDDO stats for the catalog record.  Added a reference to the PID for each transfer/replication job.
# Revision 1.14  2016/11/29 23:08:31  pweaver # added poorest rep dedupe rate output to file
# Revision 1.13  2016/11/29 17:05:04  pweaver # added Replication deduplication percentages section to the report
# Revision 1.12  2016/11/23 22:47:10  pweaver # added the backup deduplication range max, min, and avg and top 20 poorest dedupe rate jobs
# Revision 1.11  2016/11/23 17:05:46  pweaver # added Top 20 largest bptm exiting delays between \"waited for full buffer\" and \"EXITING\"
# Revision 1.10  2016/11/23 00:05:01  pweaver # reformatted output and added top 20 waited for full buffer report code
# Revision 1.9  2016/11/22 20:23:19  pweaver # add Top 20 longest running replications or duplications changed MB/sec to KB/sec with the use of commas
# Revision 1.8  2016/11/22 18:32:24  pweaver # added Calculate average backup rate per client
# Revision 1.7  2016/11/18 22:52:41  pweaver # added top 20 slowest backup jobs longer than 5 minutes
# Revision 1.6  2016/11/18 21:29:26  pweaver # added Top 20 longest backup jobs report
# Revision 1.5  2016/11/16 14:27:23  pweaver # finished the top 20 longest jobs
# Revision 1.4  2016/11/16 14:02:41  pweaver # added comments for RCS versioning (hopefully)
#
# $ID: $
#
import os
import platform
import time
import re
import datetime
import subprocess
import sys
import csv
import collections
import locale
import tarfile
import argparse
import pytz

from sys import argv
from tzlocal import get_localzone
from operator import itemgetter, attrgetter, methodcaller
from hashlib import md5
from Crypto.Cipher import AES
from Crypto import Random

csv.field_size_limit(sys.maxint)

runtime_start = time.time()
mediaserversused = set()
restoremediaservers = set()
stusused = set()
policynames = set()
targetstorageservers = set()
vmtransporttypes = set()
vmwarebackuphosts = set()
status1b = set()
status1blist = []
status1d = set()
status1dlist = []
status1i = set()
status1ilist = []
status1r = set()
status1rlist = []
limitresource = []
waitingresources = []
jobdb = []
msdprepdb = []
vmware_client_info = []
vmware_datastores = set()
accelstatsdb = []
waited_for_full = []
stu_start_end_times = []
policy_start_end_times = []
status0 = 0
status0list = set()
status1 = 0
import_air_images = []
jobsnotcomplete = 0
otherstatus = 0
otherstatuslist = []
#policy_type_defs = {"Standard": 0, "Oracle": 4, "Informix-On-BAR": 6, "Sybase": 7, "MS-SharePoint": 8, "DataTools-SQL-BackTrack": 11, "MS-Windows": 13, "MS-SQL-Server": 15, "MS-Exchange-Server": 16, "SAP": 17, "DB2": 18, "NDMP": 19, "FlashBackup": 20, "Lotus-Notes": 25, "FlashBackup-Windows": 29, "NBU-Catalog": 35, "Enterprise_Vault": 39, "VMware": 40, "Hyper-V": 41}
policy_type_defs = { 0: "Standard", 4: "Oracle", 6: "Informix-On-BAR", 7: "Sybase", 8: "MS-SharePoint", 11: "DataTools-SQL-BackTrack", 13: "MS-Windows", 15: "MS-SQL-Server", 16: "MS-Exchange-Server", 17: "SAP", 18: "DB2", 19: "NDMP", 20: "FlashBackup", 24: "Netezza", 25: "Lotus-Notes", 29: "FlashBackup-Windows", 30: "Vault", 34: "DSSU Staging", 35: "NBU-Catalog", 39: "Enterprise_Vault", 40: "VMware", 41: "Hyper-V"}
policy_types = set()
policy_frequency = {}
policyname_type_pair = {}
policy_col_length = 0
target_storage_server_col_length = 0
schedule_col_length = 0
client_col_length = 0
mediaserver_col_length = 0
stu_col_length = 0
is_vmwarebackup = 0
is_hypervbackup = 0
ms_timezone = ""
password = "aAgGlL123#$%"
most_recent_job_end = 0
base_timestamp = 1483250400     # January 1, 2017 00:00:00 CST but the timezone shouldn't matter as this just gives us a base to compare what is in the job detail times; will convert to the correct timezone later.:w!
start_timestamp = 1483250400    # psudeo arbitrary number
oldestjob_start_timestamp = 0
newestjob_start_timestamp = 0
oldestjob_id = 0


backup_err = '(starting backup job .*)|(Warning .*)|(Error .*)|(Cannot .*)'
dup_err = '(Error .*)|(Warning .*)'
import_err = '(Error .*)|(import failed.*)'
rep_err = '(Error .*)|(Critical .*)|(Warning .*)'
regex_backup = re.compile('%s'%backup_err,re.VERBOSE|re.IGNORECASE)
regex_duplication = re.compile('%s'%dup_err,re.VERBOSE|re.IGNORECASE)
regex_import = re.compile('%s'%import_err,re.VERBOSE|re.IGNORECASE)
regex_replication = re.compile('%s'%rep_err,re.VERBOSE|re.IGNORECASE)
regex_wff = re.compile(r"waited for full",re.IGNORECASE)
regex_pddostats = re.compile("PDDO stats",re.IGNORECASE)
regex_bptm_delay = re.compile(r"(\d\d/\d\d/\d\d\d\d \d\d:\d\d:\d\d)( - Info bptm\(pid=\d+\) waited for full)|(\d\d/\d\d/\d\d\d\d \d\d:\d\d:\d\d)( - Info bptm\(pid=\d+\) EXITING with status)",re.IGNORECASE)
regex_bptm_delay_shortyear = re.compile(r"(\d\d/\d\d/\d\d \d\d:\d\d:\d\d)( - Info bptm\(pid=\d+\) waited for full)|(\d\d/\d\d/\d\d \d\d:\d\d:\d\d)( - Info bptm\(pid=\d+\) EXITING with status)",re.IGNORECASE)
regex_convert_runonlines = re.compile(r"\\\\', ' ")
regex_pddo_stats_capture = re.compile(r"(\d\d/\d\d/\d\d\d\d \d\d:\d\d:\d\d) - Info \S+\(pid=(\d+)\) StorageServer=PureDisk:\S+; Report=PDDO Stats for \(\S+\): scanned: (\d+) KB -  CR sent: (\d+) KB -  CR sent over FC: (\d+) KB -  dedup: (\d+.\d+)%",re.IGNORECASE)
regex_rep_target_storage = re.compile(r"Replicating images to target storage server (\S+)",re.IGNORECASE)
regex_rep_backupids = re.compile(r"(\d\d/\d\d/\d\d\d\d \d\d:\d\d:\d\d) - Info \S+\(pid=(\d+)\) Using OpenStorage to replicate backup id (\S+)",re.IGNORECASE)
regex_combine_runonlines = re.compile(r"(?<![\w\d\s,%-_][:\s\w\d$%\)\]]\\)\\,")    # This means find "\," but not "\\," which was in the filelist of a real world example at a customer site as the policy includes :\
regex_backupid_line = re.compile(r",([\w\d\%.-]+_\d\d\d\d\d\d\d\d\d\d),",re.IGNORECASE)
regex_accel_stats = re.compile(r"accelerator sent (\d+) bytes out of (\d+) bytes to server \W+ optimization (\d+.\d+)%",re.IGNORECASE)
regex_vmware_client_info = re.compile(r"Backing up vCenter server (\S+) -  ESX host (\S+) -  BIOS UUID \S+ -  Instance UUID \S+ -  Display Name (\S+) -  Hostname (\S+)",re.IGNORECASE)
regex_vmware_esxhost_info = re.compile(r"granted resource \S+.VMware.ESXserver.(\S+)', ",re.IGNORECASE)
regex_vmware_datastore_info = re.compile(r"granted resource \S+.VMware.Datastore.(\S+)', ",re.IGNORECASE)
regex_vmware_vcenter_info = re.compile(r"granted resource \S+.VMware.snapshot.vCenter.(\S+)', ",re.IGNORECASE)
regex_vmware_transport_types = re.compile(r"Info bpbkar\(pid=\d+\) INF - Transport Type =  (\S+)', ",re.IGNORECASE)
regex_vmware_transport_types_windows = re.compile(r"Info bpbkar32\(pid=\d+\) INF - Transport Type =  (\S+)', ",re.IGNORECASE)
regex_vmware_backup_host = re.compile(r"started backup .* using backup host (\S+)',",re.IGNORECASE)
regex_start_end_times = re.compile(r",(\d\d\d\d\d\d\d\d\d\d),(\d\d\d\d\d\d\d\d\d\d),(\d\d\d\d\d\d\d\d\d\d),([,\d]+),")
regex_limit_reached = re.compile(r",(\d\d/\d\d/\d\d[\d][\d] \d\d:\d\d:\d\d) - Info nbrb\(pid=\d+\) (Limit has been reached for.*?,)",re.IGNORECASE)
regex_waiting_resource = re.compile(r",(\d\d/\d\d/\d\d[\d][\d] \d\d:\d\d:\d\d) - (waiting for resources.*?,)",re.IGNORECASE)
#01/28/2017 23:18:27 - Info nbrb(pid=2857) Limit has been reached for the logical resource rwl-netbk-p01.dc.fmcna.com.VMware.ESXserver.rwesxc11b04.dc.fmcna.com

def convert_elapsed(seconds):
    hours = seconds // (60*60)
    seconds %= (60*60)
    minutes = seconds // 60
    seconds %= 60
    return "%02i:%02i:%02i" % (hours, minutes, seconds)

def spinning_cursor():
    while True:
        for cursor in '|/-\\':
            yield cursor

def derive_key_and_iv(password, salt, key_length, iv_length):
    d = d_i = ''
    while len(d) < key_length + iv_length:
        d_i = md5(d_i + password + salt).digest()
        d += d_i
    return d[:key_length], d[key_length:key_length+iv_length]

def encrypt(in_file, out_file, password, key_length=32):
    bs = AES.block_size
    salt = Random.new().read(bs - len('Salted__'))
    key, iv = derive_key_and_iv(password, salt, key_length, bs)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    out_file.write('Salted__' + salt)
    finished = False
    while not finished:
        chunk = in_file.read(1024 * bs)
        if len(chunk) == 0 or len(chunk) % bs != 0:
            padding_length = bs - (len(chunk) % bs)
            chunk += padding_length * chr(padding_length)
            finished = True
        out_file.write(cipher.encrypt(chunk))

def decrypt(in_file, out_file, password, key_length=32):
    bs = AES.block_size
    salt = in_file.read(bs)[len('Salted__'):]
    key, iv = derive_key_and_iv(password, salt, key_length, bs)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    next_chunk = ''
    finished = False
    while not finished:
        chunk, next_chunk = next_chunk, cipher.decrypt(in_file.read(1024 * bs))
        if len(next_chunk) == 0:
            padding_length = ord(chunk[-1])
            if padding_length < 1 or padding_length > bs:
               raise ValueError("bad decrypt pad (%d)" % padding_length)
            # all the pad-bytes must be the same
            if chunk[-padding_length:] != (padding_length * chr(padding_length)):
               # this is similar to the bad decrypt:evp_enc.c from openssl program
               raise ValueError("bad decrypt")
            chunk = chunk[:-padding_length]
            finished = True
        out_file.write(chunk)

def create_tarball():
    print "\nCreating tar file..."
    tarfilename = str(int(runtime_start))+"_process_jobs_"+filename+"_collection.tar.gz"
    out = tarfile.open(tarfilename, mode="w:gz")
    try:
        for filetoadd in os.listdir("."):
            if str(int(runtime_start)) in filetoadd and str("collection") not in filetoadd:
                out.add(filetoadd)
                if str("process_jobs_")+str(int(runtime_start)) not in filetoadd:
                    print "Moving",filetoadd,"to",tarfilename
                    os.remove(filetoadd)
                else:
                    print "Copying",filetoadd,"to",tarfilename
    finally:
        out.close()
        print "Created tar file",tarfilename
        tarfilename_enc = "enc_"+tarfilename
        if args['encrypt']:
            print "Creating encrypted file",tarfilename_enc
            with open(tarfilename, 'rb') as in_file, open(tarfilename_enc, 'wb') as out_file:
                encrypt(in_file, out_file, password)
            return tarfilename_enc
    return tarfilename

parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description='This program will parse the output of the bpdbjobs comma separated output from NetBackup and produce a report. Either the --input_file {filename} must be included in the options or the --generate option.')
parser.add_argument('-i','--input_file',nargs=1, metavar=('file_to_parse'), help='The bpdbjobs -report -all_columns output file to parse and report on')
parser.add_argument('-in','--input_nbsu',nargs=1, metavar=('file_to_parse'), help='The compressed nbsu file from the NetBackup master server')
parser.add_argument('-c','--compress', action='store_true', help='compress the output files into a tarball with .gz compression')
parser.add_argument('-e','--email', nargs=3, metavar=('smtp_server','sender_address','recipient_address'), help='where to send it, who is sending it, and who is receiving it.  If there are multiple recipients, use a comma to separate the email addresses.')
parser.add_argument('-g','--generate', action='store_true', help='generate the input file when this is run on the NetBackup master server.  **NOTE** bpdbjobs must be in the env PATH variable to work properly.')
parser.add_argument('-l','--last24hours', action='store_true', help='used with the --generate option to report on only the last 24 hours of jobs.')
parser.add_argument('-enc','--encrypt', action='store_true', help='used with the --compress option to encrypt the created tarball.')
parser.add_argument('-dec','--decrypt', nargs=1, metavar=('file_to_decrypt'), help='decrypt a file created by this program.')
parser.add_argument('-hmi','--heatmap_interval', nargs=1, metavar=('value_in_minutes'), help="time interval in minutes for the heatmap. Min value = 5 minutes.  Max value = 60 minutes.  Default is 15 minutes.")
parser.add_argument('-tz','--timezone', nargs=1, metavar=('timezone_for_master_server'), help="the timezone name for the master server's timezone.")
args = vars(parser.parse_args())
#print "Arguments given = ",args

if args['decrypt']:
    enc_file = args['decrypt'][0]
    print "The file to decrypt is",enc_file
    orig_file = re.search(r"enc_(\S+)", str(enc_file),re.IGNORECASE).group(1)
    print "The original filename is",orig_file
    with open(args['decrypt'][0], 'rb') as in_file, open (orig_file, 'wb') as out_file:
        decrypt(in_file, out_file, password)
    exit(0)

if args['timezone']:
    if not args['timezone'][0] in pytz.all_timezones_set:
        print "Timezone %s is not recognized.  Please enter a valide timezone name." % (args['timezone'][0])
        print ("\n".join(pytz.country_timezones('US')))
        exit (1)
    else:
        ms_timezone = args['timezone'][0]

if args['input_nbsu']:
    import patoolib
    from patoolib.util import log_error, log_internal_error, PatoolError
    from patoolib.configuration import App
    archive=str(args['input_nbsu'][0])
    if platform.system() == "Windows":
#        outputdir=".\\"+"_".join(archive.split('_')[:3])+"_"+archive.split('_')[3].split('.')[0]
        outputdir="_".join(archive.split('_')[:3])+"_"+archive.split('_')[3].split('.')[0]

    else:
        outputdir="./"+"_".join(archive.split('_')[:3])+"_"+archive.split('_')[3].split('.')[0]
    if not os.path.exists(outputdir):   os.makedirs(outputdir)
    try:
        patoolib.extract_archive(archive, verbosity=1, outdir=outputdir)
    except PatoolError as msg:
        log_error("error extracting %s: %s" % (archive, msg))
        exit(1)
    all_columns = 0
    command_used = 0
    try:
        if platform.system() == "Windows":
            infile=outputdir+"\\NBU_jobs.txt"
#            outfile=outputdir.split('\\')[1]+"_NBU_jobs.txt"
            outfile=outputdir+"_NBU_jobs.txt"
        else:
            infile=outputdir+"/NBU_jobs.txt"
            outfile=outputdir.split('/')[1]+"_NBU_jobs.txt"
        sys.stderr.write("Creating jobs file "+str(outfile)+"\n")
        spinner = spinning_cursor()
        with open(infile,"r") as jobsinfile:
            with open(outfile,"w") as jobsoutfile:
                for line in jobsinfile:
                    sys.stderr.write(spinner.next())
                    sys.stderr.flush()
                    if re.search(r"-report -all_columns",line):    all_columns = 1
                    if all_columns and re.search(r" command used ",line,re.IGNORECASE):    command_used = 1
                    if (all_columns == 2) and not command_used:    jobsoutfile.write(line)
                    if (all_columns == 1):    all_columns = 2
                    sys.stderr.write('\b')
        jobsinfile.close()
        jobsoutfile.close()
    except IOError as msg:
        print "\nThe file could not be processed: %s" % msg
        exit(2)

if args['input_file']:
    needs_parsing = 0
    input_filename = str(args['input_file'][0])
    sys.stderr.write("Checking input file "+(str(input_filename))+"\n")
    spinner = spinning_cursor()
    with open (input_filename, "r") as jobsinfile:
        for line in jobsinfile:
            sys.stderr.write(spinner.next())
            sys.stderr.flush()
            if re.search(r"Command Used",line,re.IGNORECASE):
                needs_parsing = 1
                sys.stderr.write('\b')
                break
            sys.stderr.write('\b')
    jobsinfile.close()
    if needs_parsing:
        all_columns = 0
        command_used = 0
        if re.search(".",input_filename):
            output_filename = str(".".join(input_filename.split(".")[:-1]))+"_"+str(int(runtime_start))+".txt"
        else:
            output_filename = str(input_filename)+"_"+str(int(runtime_start))+".txt"
        sys.stderr.write("Creating a new CSV formatted file for processing: "+str(output_filename)+"\n")
        with open(input_filename,"r") as jobsinfile:
            with open(output_filename,"w") as jobsoutfile:
                for line in jobsinfile:
                    sys.stderr.write(spinner.next())
                    sys.stderr.flush()
                    if re.search(r"-report -all_columns",line):    all_columns = 1
                    if all_columns and re.search(r" command used ",line,re.IGNORECASE):    command_used = 1
                    if (all_columns == 2) and not command_used:    jobsoutfile.write(line)
                    if (all_columns == 1):    all_columns = 2
                    sys.stderr.write('\b')
        jobsinfile.close()
        jobsoutfile.close()
        filename = output_filename


if not args['generate']:
    if not args['input_file'] and not args['input_nbsu']:
        parser.print_help()
        exit(1)
    else:
        if args['input_file'] and not needs_parsing:  filename = str(args['input_file'][0])
        if args['input_nbsu']:  
            if platform.system() == "Windows":
#                filename = outputdir.split('\\')[1]+"_NBU_jobs.txt"
                filename = outputdir+"_NBU_jobs.txt"
            else:
                filename = outputdir.split('/')[1]+"_NBU_jobs.txt"
        print "Processing file: %r" % filename
    if not ms_timezone:
        ms_timezone = str(get_localzone())
        print "Processing timestamps using the local timezone, %s, which may not be the same timezone as the master server." % (ms_timezone)
else:
    filename = str(platform.uname()[1]) + "_" + str(int(runtime_start)) + "_bpdbjobs_dump.out"
    ms_timezone = str(get_localzone())
    print "Generating file ",filename
    if args['last24hours']:
        p24h = datetime.datetime.strftime(datetime.datetime.now() -datetime.timedelta(days=1),"%m/%d/%Y %H:%M:%S")
        print "24 hours ago = ",p24h
        cmd = "bpdbjobs -report -all_columns -file {} -t {}".format(str(filename),str(p24h))
    else:
        cmd = "bpdbjobs -report -all_columns -file {}".format(str(filename))
    try:
        output = subprocess.check_output(cmd,stderr=subprocess.STDOUT,shell=True)
    except OSError:
        print "Could not generate the bpdbjobs output required."
        exit(1)

if args['heatmap_interval']:
    heatmap_interval = int(args['heatmap_interval'][0])*60
    if heatmap_interval < 300:
        heatmap_interval = 300
    elif heatmap_interval > 3600:
        heatmap_interval = 3600
if not args['heatmap_interval']:
    heatmap_interval = 900          # 15 minute interval.

read_filename = filename
if platform.system() == "Windows":
    import ntpath
    filename = ntpath.basename(filename)
    print "The basename is ", filename
else:
    filename = os.path.basename(filename)
    print "The basename is ", filename

print "Running on ",platform.system(),platform.release()
spinner = spinning_cursor()

orig_stdout = sys.stdout
new_stdout = file("process_jobs_" + str(int(runtime_start)) + "_" + filename, 'w')
sys.stdout = new_stdout

try:
        with open(read_filename,"r") as myfile:
                with open(str(int(runtime_start)) + "_job_summary_" + filename + ".csv","w") as alljobssummarycsv:
                        jobs=csv.reader(myfile, delimiter=',')
                        if platform.system() == "Windows":
                            alljobssummary=csv.writer(alljobssummarycsv, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
                        else:
                            alljobssummary=csv.writer(alljobssummarycsv, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                        alljobssummary.writerow(("job id","job type","job state","exit status","policy","schedule","client","media server","storage unit","start time","start time converted","elapsed time","end time","end time converted","backup id","number of attempts","total KB","KB/sec","number of files","dedup rate","number of files in file list","file list"))
                        for i, job in enumerate(jobs):
                                sys.stderr.write(spinner.next())
                                sys.stderr.flush()
                                #print "then = ",str(",".join(job))
                                job = regex_combine_runonlines.sub(" - ",str(",".join(job))).split(",") # This takes the comma separated [] in python, shoves it back together as 1 string, changes "\\," to " - ", then splits it again
                                maxrecords = len(job)
                                jobid = int(job[0])
                                if not job[1]:
                                    # this could happen if a job is restarted and has details similar to this:
                                    # 601184,,,,,,,,0000000000,0000000000,0000000000,,,,,,,0,,,,,,,,master01,,,,0,0,0,1,0,,,0000000000,0000000000,0000000000,,,1,07/16/16 17:53:38 - Job 601184 restarted as job 601216,0,0,,,,,
                                    sys.stderr.write("\b")
                                    continue
                                jobtype = int(job[1]) 
                                jobstate = int(job[2])
                                jobstatus = job[3]
                                jobpolicy = job[4]
                                if len(jobpolicy) > 1:  policynames.add(jobpolicy)
                                if policy_col_length < len(jobpolicy): policy_col_length = len(jobpolicy)
                                jobpolicytype = int(job[21]) if job[21] else int(-1)
                                jobschedule = job[5]
                                if schedule_col_length < len(jobschedule): schedule_col_length = len(jobschedule)
                                jobclient = job[6]
                                if client_col_length < len(jobclient): client_col_length = len(jobclient)
                                jobmediaserver = job[7]
                                if mediaserver_col_length < len(jobmediaserver):    mediaserver_col_length = len(jobmediaserver)
                                jobstart = int(job[8])
                                if int(oldestjob_start_timestamp) == 0 or int(oldestjob_start_timestamp) >= int(jobstart):
                                    oldestjob_start_timestamp = int(jobstart)
                                    oldestjob_id = int(jobid)
                                if newestjob_start_timestamp == 0 or newestjob_start_timestamp < jobstart:
                                    newestjob_start_timestamp = jobstart
                                #jobstartconverted = datetime.datetime.fromtimestamp(int(jobstart)).strftime("%m/%d/%Y %H:%M:%S")
                                jobstartconverted = pytz.timezone(str(get_localzone())).localize(datetime.datetime.fromtimestamp(int(jobstart))).astimezone(pytz.timezone(ms_timezone)).strftime("%m/%d/%Y %H:%M:%S")
                                jobelapsed = job[9]
                                jobend = int(job[10])
                                if jobend > most_recent_job_end:
                                    most_recent_job_end = jobend
                                jobstu = job[11]
                                if stu_col_length < len(jobstu):    stu_col_length = len(jobstu)
                                if jobpolicytype >= 0:
                                    if jobpolicytype not in policy_type_defs.keys():
                                        sys.stderr.write("I don't know what policy type value "+str(jobpolicytype)+" is in job "+str(jobid)+".\n")
                                    else:
                                        policy_types.add(jobpolicytype)
                                        policy_frequency[jobpolicytype] = policy_frequency.get(jobpolicytype, 0) + 1
                                        policyname_type_pair.update(dict([(jobpolicy,jobpolicytype)]))
                                if jobstatus and int(jobstatus) == 0:
                                        status0 += 1
                                        status0list.add(jobclient)
                                if jobstatus and int(jobstatus) > 1:
                                        otherstatus += 1
                                        otherstatuslist.append(str(jobstatus) + "," + str(jobpolicy) + "," + str(jobschedule) + "," + str(jobclient))
                                if jobend > 0:
                                        #jobendconverted = datetime.datetime.fromtimestamp(int(jobend)).strftime("%m/%d/%Y %H:%M:%S")
                                        jobendconverted = pytz.timezone(str(get_localzone())).localize(datetime.datetime.fromtimestamp(int(jobend))).astimezone(pytz.timezone(ms_timezone)).strftime("%m/%d/%Y %H:%M:%S")
                                else:
                                        jobendconverted = "NA"
                                if jobstate in [1,3] and jobtype in [0,1,4,6,7,22,23,28]:
                                        #if jobmediaserver == ' ' or jobmediaserver == '':
                                        if not re.search(r"[\w-]+",jobmediaserver):
                                                for element in job:
                                                        stu = re.match(r".*on storage unit ([\w-]+)",element)
                                                        if stu:
                                                                stusused.add(str(stu.group(1)))
                                        else:
                                                mediaserversused.add(jobmediaserver)
                                                if not re.search(r"[\w-]+",jobstu):
                                                        for element in job:
                                                                stu = re.match(r".*on storage unit ([\w-]+)",element)
                                                                if stu:
                                                                        stusused.add(str(stu.group(1)))
                                                else:
                                                        stusused.add(jobstu)
                                if jobtype == 20:       #replications
                                        for element in job:
                                                target = re.match(r".*target storage server (\w+)",element)
                                                if target:
                                                        targetstorageservers.add(target.group(1))
                                if jobtype == 2:        #restores
                                        restoremediaservers.add(str(jobmediaserver))
                                if jobstatus in ["1"] and int(jobstate) == 3 and not jobschedule in ['-']:   #jobstatus is a string because it can be undefined and integers cannot be undefined
                                        status1 += 1
                                        for element in job:
                                                if jobtype == 0 and ("starting backup job" in element or "Warning" in element or "Error" in element or "Cannot" in element):
                                                        status1b.add(str(jobclient))
                                                        status1blist.append(str(jobclient) + "," + str(jobid) + ",backup," + " ".join(str(e) for e in regex_backup.findall(element)))
                                                if jobtype == 4 and ( "Error" in element or "Warning" in element ):
                                                        status1d.add(str(jobclient))
                                                        status1dlist.append(str(jobclient) + "," + str(jobid) + ",duplication," + " ".join(str(e) for e in regex_duplication.findall(element)))
                                                if jobtype == 20 and ( "Error" in element or "Critical" in element or "Warning" in element ):
                                                        status1i.add(str(jobclient))
                                                        status1ilist.append(str(jobclient) + "," + str(jobid) + ",import," + " ".join(str(e) for e in regex_import.findall(element)))
                                                if jobtype == 21 and ( "Error" in element or "import failed" in element ):
                                                        status1r.add(str(jobclient))
                                                        status1rlist.append(str(jobclient) + "," + str(jobid) + ",replication," + " ".join(str(e) for e in regex_replication.findall(element)))
                                if jobstatus in ["196"]:
                                    limit = regex_limit_reached.findall(",".join(job))
                                    if limit:
                                        limitresource.append(str(jobid)+","+str(jobclient)+","+str(limit))
                                        #sys.stderr.write("limitresource = "+str(limitresource)+"\n")
                                waiting_for_resource = regex_waiting_resource.findall(",".join(job))
                                if waiting_for_resource:
                                    waitingresources.append(str(jobid)+","+str(jobstu)+","+str(jobclient)+","+str(waiting_for_resource))
                                jobtries = job[12]
                                joboperation = job[13]
                                jobfileswritten = job[15]
                                jobfilelistcount = int(job[31])
                                jobfilelist = ""
                                x = 32
                                while x < (32 + int(jobfilelistcount)):
                                    jobfilelist = jobfilelist + job[x] + ","
                                    if jobtype == 21:               # AIR Import jobs
                                        import_air_images.append(job[x])
                                    x = x + 1
                                backupid = regex_backupid_line.search(str(",".join(job)))
                                if backupid:
                                    jobbackupid=backupid.group(1)
                                else:
                                    jobbackupid = backupid
                                #jobkbwritten = job[maxrecords - 27]
                                jobkbwritten = int(job[14]) if job[14] else int(0)
                                #kbfield = maxrecords - 28
                                if jobstate and (int(jobstate) == 3):
                                    if jobstatus and (int(jobstatus) in [0,1,40,41,83,84,150]) and (int(jobtype) in [0,1,2,4,6,7,20,22]):
                                        if jobtries and (int(jobtries) == 1):
                                            #sys.stderr.write( "jobid = "+str(jobid)+" field 32 ="+str(job[31])+" plus 41 gives "+str((int(job[31]) + 41))+" or "+str(job[(int(job[31]) + 41)])+" then "+str(int(job[(int(job[31])+41)])+(int(job[31])+41)+4)+" and that field = "+str(job[(int(job[(int(job[31])+41)])+(int(job[31])+41)+4)])+"\n")
                                            #print "maxrecords =",maxrecords
                                            kbfield = (int(job[(int(job[31])+41)])+(int(job[31])+41)+4)     # take the contents of job[field 32(starting at 1) + 41] then add the value of field 32 + 41 + 4
                                            jobfinalkbpersec = int(job[kbfield]) if job[kbfield] else int(0)    # 0 should mean that it is a parent job
                                            #print "jobid =",jobid,"KB field = ",kbfield,"and job[",kbfield,"] =",jobfinalkbpersec
                                        else:
                                            #print "oops, I haven't calcuated for multiple tries yet. please check job id",jobid,"which has",jobtries,"attempts and finished with a status code",jobstatus
                                            if jobbackupid:
                                                #print "jobid =",jobid,"jobstatus =",jobstatus,"jobtype =",jobtype,"jobtries =",jobtries,"jobbackupid =",jobbackupid," and job.index(jobbackupid) =",job.index(jobbackupid)
                                                if job[(job.index(jobbackupid)-17)]:
                                                    kbfield = int(job.index(jobbackupid)-17)
                                                    jobfinalkbpersec = int(job[(kbfield)])
                                                else:
                                                    jobfinalkbpersec = 0    # if the kbpersec field is empty then this is probably a parent job whose children did the backup
                                            else:
                                                jobfinalkbpersec = 0   # the backupid does not exist and so we shouldn't expect to have a throughput rate
                                    else:
                                        jobfinalkbpersec = 0           # the job failed or is not a backup, restore, duplication or replication so do we really care about calculating it's throughput?
                                else:
                                    jobfinalkbpersec = 0       # because the job isn't finished yet
                                    jobsnotcomplete = jobsnotcomplete + 1
                                if ((jobtype == 0) or (jobtype == 1) or (jobtype == 4) or (jobtype == 6) or (jobtype == 22)) and (jobstatus) and (int(jobstatus) <= 1) and regex_pddostats.search(str(job)):
                                    if job[(maxrecords - 2)]:
                                        jobdeduperate = float(job[(maxrecords - 2)])   # since arrays start at zero, the dedup rate for 7.6.x.x and below jobs will actually be the next to last field which is addressed by maxrecords-2
                                    elif job[(maxrecords - 5)]:
                                        jobdeduperate = float(job[(maxrecords - 5)])   # for 7.7.x the dedup rate is now the 5th value from the end instead of the 2nd like above
                                    else:
                                        jobdeduperate = float(-1.0)     # found an SLP dup in a client's job data from MSDP to tape that reported PDDO stats received when the dup was from disk to tape so this should not have a dedupe rate.
                                else:
                                    jobdeduperate = float(-1.0)       # this is really a Not Appliable (NA) but I'm working with numbers so thus using -1 instead
                                if ((jobtype == 20) and (jobstatus) and (int(jobstatus) <= 1) and regex_pddostats.search(str(job))):        # for replication jobs
                                    n = regex_pddo_stats_capture.findall(str(job))        # capture the PDDO stats from the image transfer
                                    o = regex_rep_target_storage.search(str(job))         # find the target storage server, which may not be evident in the stu depending on the version of NBU
                                    p = regex_rep_backupids.findall(str(job))             # This finds all the backup ids in a job that are being replicated.
                                    bidmatrix = []
                                    for z in p:
                                       bidmatrix.append([z,0])
                                       #if int(jobid) == 445740:
                                       #     sys.stderr.write("bidmatrix[-1] = "+str(bidmatrix[-1])+"\n")
                                    if (target_storage_server_col_length < len(o.group(1))):   target_storage_server_col_length = len(o.group(1))
                                    #if int(jobid) == 445740:    sys.stderr.write("n = "+str(n)+"\n")
                                    #if int(jobid) == 445740:    sys.stderr.write("o = "+str(o.group())+"\n")
                                    #if int(jobid) == 445740:    sys.stderr.write("p = "+str(p)+"\n")
                                    FMT = '%m/%d/%Y %H:%M:%S'
                                    for i, dedupestat in enumerate(n):
                                        if (int(dedupestat[2]) > 50):                      # exclude all jobs smaller than 50 KB which should only be the sizes for the catalog record sent as part of the AIR transfer
                                            #s = [q for q, r in enumerate(p) if dedupestat[1] in r]      # this find the index location within p given the pid value in dedupestat[1] to make sure we have the backupid that belongs to the same PID as the PDDO Stats line while accounting for the removal of the catalog record being transferred.
                                            s = [q for q, r in enumerate(bidmatrix) if dedupestat[1] in r[0]]      # this find the index location within p given the pid value in dedupestat[1] to make sure we have the backupid that belongs to the same PID as the PDDO Stats line while accounting for the removal of the catalog record being transferred.
                                            #if len(s) > 1:  sys.stderr.write("s ="+str(s)+"\n")
                                            pos = 0
                                            while pos < len(s):
                                                #if int(jobid) == 445740:    sys.stderr.write("bidmatrix["+str(s[pos])+"] = "+str(bidmatrix[s[pos]])+"\n")
                                                while pos < len(s) and bidmatrix[s[pos]][1] == 1:
                                                    #sys.stderr.write("bidmatrix["+str(s[pos])+"][0][2] = "+str(bidmatrix[s[pos]][0][2])+" and is already in mspdrepdb.\n")
                                                    pos = pos + 1
                                                start = datetime.datetime.strptime(bidmatrix[s[pos]][0][0],FMT)
                                                end = datetime.datetime.strptime(dedupestat[0],FMT)
                                                elapsedtime = end - start
                                                if start <= end:
                                                    if not ([jobid,jobpolicy,jobschedule,jobstu,o.group(1),list(dedupestat[1:]),bidmatrix[s[pos]][0][2],bidmatrix[s[pos]][0][0],dedupestat[0],elapsedtime.seconds]) in msdprepdb:
                                                        msdprepdb.append([jobid,jobpolicy,jobschedule,jobstu,o.group(1),list(dedupestat[1:]),bidmatrix[s[pos]][0][2],bidmatrix[s[pos]][0][0],dedupestat[0],elapsedtime.seconds])
                                                        #if len(s) > 1:  sys.stderr.write("msdprepdb[-1] = "+str(msdprepdb[-1])+"\n")
                                                        bidmatrix[s[pos]][1] = 1
                                                        break
                                                else:
                                                    sys.stderr.write("else dedupestat = "+str(dedupestat)+" and start = "+str(start)+" and end = "+str(end)+"\n")
                                                #if len(s) > 1:  sys.stderr.write("msdprepdb[-1] = "+str(msdprepdb[-1])+"\n")
                                                pos = pos + 1
                                            # example: msdprepdb[-1] = [95970, 'SLP_VMWare', 'Default_24x7_Window', 'cs5220:From_mspd5200-1', 'cs5220', ['24023', '41716341', '13074080', '0', '68.7'], 'vCenter6_1484713042', '01/17/2017 23:05:35', '01/17/2017 23:14:06', 511]
                                if len(jobstu) > 1 and (jobtype != 20) and regex_start_end_times.search(str(",".join(job))):
                                    start_end = regex_start_end_times.findall(str(",".join(job)))
                                    #sys.stderr.write("start_end = "+str(start_end)+"\n")   # for debugging, print the last line in the array which is the line we just added/appended
                                    zero_times = re.search(r"0000000000,0000000000,0000000000",(str(",".join(start_end[0]))))
                                    if zero_times:
                                        start_end = [(jobstart,jobelapsed,jobend,jobstatus)]
                                    #sys.stderr.write("start_end = "+str(start_end)+"\n")   # for debugging, print the last line in the array which is the line we just added/appended
                                    stu_start_end_times.append([jobid,jobtries,jobstatus,jobstu,start_end])
                                    if int(start_end[0][0]) > 0 and int(oldestjob_start_timestamp) > int(start_end[0][0]):
                                        oldestjob_start_timestamp = int(start_end[0][0])
                                        oldestjob_id = int(jobid)
                                    #sys.stderr.write("stu_start_end_times = "+str(stu_start_end_times[-1])+"\n")   # for debugging, print the last line in the array which is the line we just added/appended
                                if jobpolicy:
                                    start_end = regex_start_end_times.findall(str(",".join(job)))
                                    zero_times = re.search(r"0000000000,0000000000,0000000000",(str(",".join(start_end[0]))))
                                    if zero_times:
                                        start_end = [(jobstart,jobelapsed,jobend,jobstatus)]
                                        #sys.stderr.write("start_end = "+str(start_end)+"\n")   # for debugging, print the last line in the array which is the line we just added/appended
                                    policy_start_end_times.append([jobid,jobtries,jobstatus,jobpolicy,jobschedule,jobclient,start_end])
                                    #sys.stderr.write("policy_start_end_times = "+str(policy_start_end_times[-1])+"\n")   # for debugging, print the last line in the array which is the line we just added/appended
                                jobdb.append([jobid,jobtype,jobstate,jobstatus,jobpolicy,jobschedule,jobclient,jobmediaserver,jobstu,jobstart,jobstartconverted,jobelapsed,jobend,jobendconverted,jobbackupid,jobtries,jobkbwritten,jobfinalkbpersec,jobfileswritten,jobdeduperate,jobfilelistcount,jobfilelist])
                                alljobssummary.writerow((jobid,jobtype,jobstate,jobstatus,jobpolicy,jobschedule,jobclient,jobmediaserver,jobstu,jobstart,jobstartconverted,jobelapsed,jobend,jobendconverted,jobbackupid,jobtries,jobkbwritten,jobfinalkbpersec,jobfileswritten,jobdeduperate,jobfilelistcount,jobfilelist));
                                if ((jobtype == 0) or (jobtype == 1) or (jobtype == 6) or (jobtype == 22)) and (jobstatus) and (int(jobstatus) <= 1) and regex_wff.search(str(job)):
                                    #print "job = ",job
                                    m = re.search(r"waited for full buffer \d+ times -  delayed \d+ times"," ".join(str(f) for f in job))
                                    times = re.split("\D+",m.group(0))
                                    # the below returns a list like this but if there are more than 1 job attempts we will only report on the successful attempt
                                    # n =  [('05/16/2016 13:26:27', ' - Info bptm(pid=349647) waited for full', '', ''), ('', '', '05/16/2016 13:26:27', ' - Info bptm(pid=349647) EXITING')]
                                    n = regex_bptm_delay.findall(" ".join(str(f) for f in job))
                                    FMT = '%m/%d/%Y %H:%M:%S'
                                    if not n:       # account for timestamps that are in mm/dd/yy where yy is the last 2 digits of the year.  I think this may depend on LOCALE setting for the user but was encountered in real data.
                                        n = regex_bptm_delay_shortyear.findall(" ".join(str(f) for f in job))
                                        FMT = '%m/%d/%y %H:%M:%S'
                                        if not n:
                                            sys.stderr.write("\n*** enountered an issue trying to calculate the bptm delays.  job = "+str("\n".join(str(f) for f in job))+"\nExiting.\n")
                                            exit(1)
                                    start = datetime.datetime.strptime(n[(len(n)-2)][0],FMT)
                                    end = datetime.datetime.strptime(n[(len(n)-1)][2],FMT)
                                    elapsedwait = end - start
                                    waited_for_full.append([jobid,jobclient,jobpolicy,jobschedule,times[1],times[2],str(m.group(0)),jobstu,n[(len(n)-2)][0],n[(len(n)-1)][2],elapsedwait,elapsedwait.seconds])
                                if ((int(jobstate) == 3) and (int(jobtype) in [0,1,22]) and (jobstatus) and (int(jobstatus) <= 1) and regex_accel_stats.search(str(job))):
                                    #sys.stderr.write("job = "+str(job)+"\n")
                                    astats = regex_accel_stats.search(str(job))
                                    #sys.stderr.write("astats ="+str(astats.group(1,2,3))+"\n")
                                    accelstatsdb.append([jobid,jobclient,jobpolicy,jobschedule,jobstu,list(astats.group(1,2,3))])
                                    #sys.stderr.write("accelstatsdb ="+str(accelstatsdb)+"\n")
                                if ((jobpolicytype == 40) and (int(jobstate) == 3) and (jobstatus) and (int(jobstatus) <= 1)):
                                    if (int(jobtype) == 0): is_vmwarebackup = is_vmwarebackup + 1
                                    #sys.stderr.write("job = "+str(job)+"\n")
                                    vminfo = regex_vmware_client_info.search(str(job))
                                    #sys.stderr.write("vminfo ="+str(vminfo)+"\n")
                                    if vminfo :
                                        vmware_client_info.append([jobid,jobclient,jobpolicy,jobschedule,jobstu,list(vminfo.groups())])
                                    else:
                                        vmesx = regex_vmware_esxhost_info.search(str(job))
                                        vmdatastore = regex_vmware_datastore_info.search(str(job))
                                        if vmdatastore: vmware_datastores.add(vmdatastore.group(1))
                                        vmvcenter = regex_vmware_vcenter_info.search(str(job))
                                        if vmesx and vmdatastore and vmvcenter:
                                            vmware_client_info.append([jobid,jobclient,jobpolicy,jobschedule,jobstu,(vmvcenter.group(vmvcenter.lastindex),vmesx.group(vmesx.lastindex),"","")])
                                        elif vmesx:
                                            vmware_client_info.append([jobid,jobclient,jobpolicy,jobschedule,jobstu,("",vmesx.group(vmesx.lastindex),"","")])
                                    ttype = regex_vmware_transport_types.search(str(job))
                                    if ttype:
                                        vmtransporttypes.add(ttype.group(ttype.lastindex))
                                        #sys.stderr.write("VMware Transport Type for job "+str(jobid)+" is "+str(ttype.group(ttype.lastindex))+"\n")
                                        #sys.stderr.write("VMware Transport Type for job "+str(jobid)+" is "+str(ttype.groups())+"\n")
                                    else:   # we are dealing with a windows machine that is reporting bpbkar32 instead of bpbkar
                                        ttype = regex_vmware_transport_types_windows.search(str(job))
                                        if ttype:
                                            vmtransporttypes.add(ttype.group(ttype.lastindex))
                                    bhost = regex_vmware_backup_host.search(str(job))
                                    if bhost:
                                        vmwarebackuphosts.add(bhost.group((bhost.lastindex)))
                                if ((jobpolicytype == 41) and (int(jobstate) == 3) and (jobstatus) and (int(jobtype) == 0) and (int(jobstatus) <= 1)):
                                    is_hypervbackup = is_hypervbackup + 1
                                sys.stderr.write('\b')
except IOError as msg:
        print "The file %s could not be read: %s" % (filename, msg)
myfile.close()
alljobssummarycsv.close()
sys.stderr.write("Generating report.\n")
status0clients = sorted(list(str(e) for e in status0list))
status1clients = sorted(list(status1b | status1d | status1i | status1r))
otherstatusclients = sorted(list(str(e.split(",")[3]) for e in set(otherstatuslist)))
jobid_length = len(str(jobdb[0][0]))
sys.stderr.write(spinner.next())
sys.stderr.flush()
oldestjobstartconverted = pytz.timezone(str(get_localzone())).localize(datetime.datetime.fromtimestamp(int(oldestjob_start_timestamp))).astimezone(pytz.timezone(ms_timezone)).strftime("%m/%d/%Y %H:%M:%S")
print "Processing run on ",time.strftime("%m/%d/%Y %H:%M:%S",time.localtime(runtime_start))
print
print "This job dump contains ",int(len(jobdb))," jobs"
#print "     The oldest job, %d, was started:\t%s %s" %  (jobdb[-1][0],jobdb[-1][10],pytz.timezone(ms_timezone))
#print "     The newest job, %d, was started:\t%s %s" % (jobdb[0][0],jobdb[0][10],pytz.timezone(ms_timezone))
print "     The oldest job, %s, was started:\t%s %s" %  (str(oldestjob_id).rjust(jobid_length),oldestjobstartconverted,pytz.timezone(ms_timezone))
print "     The newest job, %s, was started:\t%s %s" % (str(jobdb[0][0]).rjust(jobid_length),jobdb[0][10],pytz.timezone(ms_timezone))
print
print "The media servers used in these jobs are: %s " % str.join(',',set(mediaserversused))
print
print "The STUs used in these jobs are: ",str.join(',',set(stusused))
print
print "The target storage servers for AIR replications are: ",str.join(',',set(targetstorageservers))
print
print "Media servers used during restores: ",str.join(',',set(restoremediaservers))
print
print "Number of images imported from A.I.R. jobs: ",len(import_air_images)
print
print "Status Code Summary:\t%s status code 0, %d status code 1, %d status codes > 1, %d jobs not complete" % (status0, status1, otherstatus, jobsnotcomplete)
print
print "Status 0 jobs:"
print "     client names    : "," ".join(str(e) for e in status0clients)
print
print "Status 1 jobs:"
print "     for backups     : ",len(set(status1b))," jobs"
print "     for duplications: ",len(set(status1d))," jobs"
print "     for imports     : ",len(set(status1d))," jobs"
print "     for replications: ",len(set(status1d))," jobs"
print "     client names    : "," ".join(str(e) for e in status1clients)
print
print "Status >1 jobs:"
print "     all job types   : ",otherstatus," jobs"
print "     client names    : "," ".join(sorted(str(e) for e in set(otherstatusclients)))
sys.stderr.write('\b')
sys.stderr.write(spinner.next())
sys.stderr.flush()
status1b_file = open(str(int(runtime_start)) + "_status1_backup_msgs_" + filename, 'w')
status1b_file.write( "\n".join(str(e) for e in status1blist));
status1b_file.close()
sys.stderr.write('\b')
sys.stderr.write(spinner.next())
sys.stderr.flush()

status1d_file = open(str(int(runtime_start)) + "_status1_duplication_msgs_" + filename, 'w')
status1d_file.write( "\n".join(str(e) for e in status1dlist));
status1d_file.close()
sys.stderr.write('\b')
sys.stderr.write(spinner.next())
sys.stderr.flush()

status1i_file = open(str(int(runtime_start)) + "_status1_import_msgs_" + filename, 'w')
status1i_file.write( "\n".join(str(e) for e in status1ilist));
status1i_file.close()
sys.stderr.write('\b')
sys.stderr.write(spinner.next())
sys.stderr.flush()

status1r_file = open(str(int(runtime_start)) + "_status1_replication_msgs_" + filename, 'w')
status1r_file.write( "\n".join(str(e) for e in status1rlist));
status1r_file.close()
sys.stderr.write('\b')
sys.stderr.write(spinner.next())
sys.stderr.flush()

# find out how many unique non-status code 0 error were recorded in the job dump
otherstatuscodes = sorted(list(int(n.split(",")[0]) for n in set(otherstatuslist)))
counter=collections.Counter(otherstatuslist)
print
print "Status Codes >1 by Policy,Schedule,Client"
print "\tCode\tCount\tPolicy,Schedule,Client"
for t in list(sorted(counter.most_common(1000),key=itemgetter(0))):
    if len(t) == 2:
        s=t[0]
        print "\t",t[0].split(",")[0],"\t",t[1],"\t",s.split(",")[1],",",s.split(",")[2],",",s.split(",")[3]
    else:
        print "t = ",t," and length = ",len(t)
sys.stderr.write('\b')
sys.stderr.write(spinner.next())
sys.stderr.flush()

sys.stderr.write('\b')
sys.stderr.write("Generated file "+str(str(int(runtime_start)) + "_196_limit_resource_msgs_" + filename)+"\n")
limitresource_file = open(str(int(runtime_start)) + "_196_limit_resource_msgs_" + filename, 'w')
limitresource_file.write("job id, job client, limit resource message(s)\n");
limitresource_file.write("\n".join(str(l) for l in limitresource));
limitresource_file.close()
sys.stderr.write(spinner.next())
sys.stderr.flush()
 
sys.stderr.write('\b')
sys.stderr.write("Generated file "+str(str(int(runtime_start)) + "_waiting_for_resource_msgs_" + filename)+"\n")
waitingresource_file = open(str(int(runtime_start)) + "_waiting_for_resource_msgs_" + filename, 'w')
waitingresource_file.write("job id, job stu, job client, waiting for resource message(s)\n");
waitingresource_file.write("\n".join(str(l) for l in waitingresources));
waitingresource_file.close()
sys.stderr.write(spinner.next())
sys.stderr.flush()

#Report on the breakdown of policy types
print "\nJob count by Policy Type:"
for type in policy_frequency.items():
    print str(policy_type_defs.get(int(type[0]))).rjust(30),": ","{:10,}".format(int(type[1]))
sys.stderr.write('\b')
sys.stderr.write(spinner.next())
sys.stderr.flush()

#Report on the breakdown of policy types by media server
print "\nJob count by Policy Type per Media Server:"
#sys.stderr.write ("policyname_type_pair = " + str(policyname_type_pair) + "\n")
#sys.stderr.write ("policy_frequency.items() = " + str(policy_frequency.items()) + "\n")
for mediaserver in sorted(mediaserversused):
    print "\t",str(mediaserver).rjust(mediaserver_col_length),":"
    for ptype in policy_frequency.items():
        count = 0
        for job in jobdb:
            if job[7] == mediaserver and job[4] in policyname_type_pair.keys() and policyname_type_pair[job[4]] == ptype[0]:    # this is because I didn't add the policytype field to the jobdb entry before I started
                #sys.stderr.write("policyname_type_pair["+str(job[4])+"] = " + str(policyname_type_pair[job[4]]) + " and ptype[0] = " + str(ptype[0]) + "\n")
                count = count + 1
        if count > 0:
            print "\t",str(policy_type_defs.get(int(ptype[0]))).rjust(mediaserver_col_length+5),": ","{:10,}".format(count)

sys.stderr.write('\b')
sys.stderr.write(spinner.next())
sys.stderr.flush()
#Report on the breakdown of policy types by storage unit
print "\nJob count by Policy Type per Storage Unit:"
for stu in sorted(stusused):
    print "\t",str(stu).rjust(stu_col_length),":"
    for ptype in policy_frequency.items():
        count = 0
        for job in jobdb:
            if job[8] == stu and job[4] in policyname_type_pair.keys() and policyname_type_pair[job[4]] == ptype[0]:    # this is because I didn't add the policytype field to the jobdb entry before I started
                #sys.stderr.write("policyname_type_pair["+str(job[4])+"] = " + str(policyname_type_pair[job[4]]) + " and ptype[0] = " + str(ptype[0]) + "\n")
                count = count + 1
        if count > 0:
            print "\t",str(policy_type_defs.get(int(ptype[0]))).rjust(stu_col_length+5),": ","{:10,}".format(count)
sys.stderr.write('\b')
sys.stderr.write(spinner.next())
sys.stderr.flush()

#Report on successful VMware "Backup" jobs (based on the job type column)
if (is_vmwarebackup >= 1):
    print "\nNumber of VMware Backup data jobs: ","{:9,}".format(is_vmwarebackup)
    vcenter_servers = set()
    esx_hosts = set()
    for job in vmware_client_info:
        if job[5][0] not in vcenter_servers:
            vcenter_servers.add(job[5][0])
        if job[5][1] not in esx_hosts:
            esx_hosts.add(job[5][1])
    print "The reported vCenters involved in backup jobs were  : "," ".join(str(vs) for vs in vcenter_servers)
    print "The reported ESX hosts involved in backup jobs were : "," ".join(str(eh) for eh in esx_hosts)
    print "The reported Datastores involved in backup jobs were: "," ".join(str(ds) for ds in vmware_datastores)
    print "Transport Type(s) used for backups: "," ".join(str(tt) for tt in vmtransporttypes)
    print "Backup Hosts for VMware backups: "," ".join(str(bh) for bh in vmwarebackuphosts)
#else:
    #sys.stderr.write("vmware_client_info routine did not find any vmware server details.  vmware_client_info = "+str(vmware_client_info)+" and vmtransporttypes = "+str(vmtransporttypes)+"\n")
sys.stderr.write('\b')
sys.stderr.write(spinner.next())
sys.stderr.flush()

#Report on successful Hyper-V "Backup" jobs
if (is_hypervbackup >= 1):
    print "\nNumber of Hyper-V Backup data jobs: ","{:9,}".format(is_hypervbackup)
sys.stderr.write('\b')
sys.stderr.write(spinner.next())
sys.stderr.flush()

#Top 20 longest running jobs
jobdb.sort(key = lambda x: int(x[11]), reverse = True)
print "\nTop 20 longest running jobs of any kind are:"
print "\t","Job ID".rjust(10),"Elapsed Time".rjust(12),"Client Name".rjust(client_col_length+2),"Policy Name".rjust(policy_col_length+2),"Schedule Name".rjust(schedule_col_length+2),"Storage Unit".rjust(stu_col_length+2),"   Job Size GB       Throughput Rate  Exit Status"
for job in jobdb[:20]:
    jobsum=[job[0],convert_elapsed(int(job[11])),job[6],job[4],job[5],job[8],job[16],job[17],job[3]]
    jobGB = (float(jobsum[6])/1024/1024) if jobsum[6] else 0
    jobKBrate = int(jobsum[7]) if jobsum[7] else 0
    print "\t",str(jobsum[0]).rjust(10),jobsum[1].rjust(12),jobsum[2].rjust(client_col_length+2),jobsum[3].rjust(policy_col_length+2),jobsum[4].rjust(schedule_col_length+2),jobsum[5].rjust(stu_col_length+2),"%14s %14s KB/sec  %s" % ("{:14,.2f}".format(jobGB),"{:14,}".format(jobKBrate),str(jobsum[8]))
sys.stderr.write('\b')
sys.stderr.write(spinner.next())
sys.stderr.flush()

#Top 20 longest running completed backups
count=0
print "\nTop 20 longest running completed backup jobs are:"
print "\t","Job ID".rjust(10),"Elapsed Time".rjust(12),"Client Name".rjust(client_col_length+2),"Policy Name".rjust(policy_col_length+2),"Schedule Name".rjust(schedule_col_length+2),"Storage Unit".rjust(stu_col_length+2),"   Job Size GB       Throughput Rate  Exit Status"
for job in jobdb:
    if ((job[1] == 0 or job[1] == 1 or job[1] == 22) and (job[2] == 3) and (len(job[8]) > 0)):
        count = count + 1
        jobsum=[job[0],convert_elapsed(int(job[11])),job[6],job[4],job[5],job[8],job[16],job[17],job[3]]
        jobGB = (float(jobsum[6])/1024/1024) if jobsum[6] else 0
        jobKBrate = int(jobsum[7]) if jobsum[7] else 0
        print "\t",str(jobsum[0]).rjust(10),jobsum[1].rjust(12),jobsum[2].rjust(client_col_length+2),jobsum[3].rjust(policy_col_length+2),jobsum[4].rjust(schedule_col_length+2),jobsum[5].rjust(stu_col_length+2),"%14s %14s KB/sec  %s" % ("{:14,.2f}".format(jobGB),"{:14,}".format(jobKBrate),str(jobsum[8]))
    if count == 20:
            break
sys.stderr.write('\b')
sys.stderr.write(spinner.next())
sys.stderr.flush()

#Top 20 slowest completed backups
jobdb.sort(key = lambda x: int(x[16]), reverse=True)    #secondary sort key of jobkbwritten, largest to smallest
jobdb.sort(key = lambda x: int(x[17]))          #primary sort key of jobfinalkbpersec
slowest_clients = open(str(int(runtime_start)) + "_sorted_slowest_clients_" + filename, "w")
print "\nTop 20 slowest completed backups that ran more than 5 minutes are:"
print "\t","Job ID".rjust(10),"Elapsed Time".rjust(12),"Client Name".rjust(client_col_length+2),"Policy Name".rjust(policy_col_length+2),"Schedule Name".rjust(schedule_col_length+2),"Storage Unit".rjust(stu_col_length+2),"   Job Size MB       Throughput Rate  Exit Status"
slowest_clients.write("\nSlowest completed backups that ran more than 5 minutes are:\n")
slowest_clients.write("".join(["\t","Job ID ".rjust(10),"Elapsed Time".rjust(12),"Client Name".rjust(client_col_length+2),"Policy Name".rjust(policy_col_length+2),"Schedule Name".rjust(schedule_col_length+2),"Storage Unit".rjust(stu_col_length+2),"   Job Size MB       Throughput Rate  Exit Status\n"]))
count = 0
for job in jobdb:
    if ((job[1] == 0 or job[1] == 1 or job[1] == 22) and (job[2] == 3) and (int(job[3]) <= 1) and (len(job[5]) > 1) and (int(job[11]) >= 300) and (job[16] > 0)):
        count = count + 1
        jobsum=[job[0],convert_elapsed(int(job[11])),job[6],job[4],job[5],job[8],job[16],job[17],job[3]]
        jobMB = (float(jobsum[6])/1024) if jobsum[6] else int(0)
        jobKBrate = int(jobsum[7]) if jobsum[7] else int(0)
        slowest_clients.write("".join(["\t",str(jobsum[0]).rjust(10),jobsum[1].rjust(12),jobsum[2].rjust(client_col_length+2),jobsum[3].rjust(policy_col_length+2),jobsum[4].rjust(schedule_col_length+2),jobsum[5].rjust(stu_col_length+2),"%14s %14s KB/sec  %s\n" % ("{:14,.2f}".format(jobMB),"{:,}".format(jobKBrate),str(jobsum[8]))]))
        if count <= 20:
            print "\t",str(jobsum[0]).rjust(10),jobsum[1].rjust(12),jobsum[2].rjust(client_col_length+2),jobsum[3].rjust(policy_col_length+2),jobsum[4].rjust(schedule_col_length+2),jobsum[5].rjust(stu_col_length+2),"%14s %14s KB/sec  %s" % ("{:14,.2f}".format(jobMB),"{:,}".format(jobKBrate),str(jobsum[8]))
slowest_clients.close()
print "** A job size of 0 indicates this is a parent job and the data is found in the child jobs.  Please see ",str(int(runtime_start)) + "_sorted_slowest_clients_" + filename," for the complete list. **"
sys.stderr.write('\b')
sys.stderr.write(spinner.next())
sys.stderr.flush()

#Calculate average backup rate per client
jobdb.sort(key = lambda x: x[6])
client_avg_backup = collections.defaultdict(list)
client_avg_backup_file = open(str(int(runtime_start)) + "_avg_backup_per_client_" + filename, "w")
for job in jobdb:
    if ((job[1] == 0 or job[1] == 1 or job[1] == 22) and (job[2] == 3) and (int(job[3]) <= 1) and (len(job[5]) > 1)):
        clientname = str(job[6])
        client_avg_backup[clientname].append(job[17])
cab = collections.OrderedDict(sorted(client_avg_backup.items()))
for client in cab.items():
    client_total_rate = 0
    jobs = 0
    for i, jobkb in enumerate(client[1]):
        if jobkb:
            client_total_rate = client_total_rate + int(jobkb)
            jobs = jobs + 1
        if ((i+1) == len(client[1])):
            client_avg_backup_file.write(" ".join([client[0],"has an averaged backup rate of","{:,}".format(client_total_rate/(jobs+1)),"KB/sec over %d jobs\n" % (jobs)]))
client_avg_backup_file.close()
print "\nThe averaged backup rate of each client has been written to ",str(int(runtime_start)) + "_avg_backup_per_client_" + filename,"\n"
sys.stderr.write('\b')
sys.stderr.write(spinner.next())
sys.stderr.flush()

#Top 20 largest backup jobs by size
jobdb.sort(key = lambda x: int(x[16]),reverse = True)
print "\nTop 20 largest completed backups:"
print "\t","Job ID".rjust(10),"Elapsed Time".rjust(12),"Client Name".rjust(client_col_length+2),"Policy Name".rjust(policy_col_length+2),"Schedule Name".rjust(schedule_col_length+2),"Storage Unit".rjust(stu_col_length+2),"   Job Size MB       Throughput Rate  Exit Status"
count = 0
for job in jobdb:
    if ((job[1] == 0 or job[1] == 1 or job[1] == 22) and (job[2] == 3) and (int(job[3]) <= 1) and (len(job[5]) > 1) and (job[11] >= 300)):
        count = count + 1
        jobsum=[job[0],convert_elapsed(int(job[11])),job[6],job[4],job[5],job[8],job[16],job[17],job[3]]
        jobMB = (float(jobsum[6])/1024) if jobsum[6] else 0
        jobKBrate = int(jobsum[7]) if jobsum[7] else int(0)
        if count <= 20:
            print "\t",str(jobsum[0]).rjust(10),jobsum[1].rjust(12),jobsum[2].rjust(client_col_length+2),jobsum[3].rjust(policy_col_length+2),jobsum[4].rjust(schedule_col_length+2),jobsum[5].rjust(stu_col_length+2),"%14s %14s KB/sec  %s" % ("{:14,.2f}".format(jobMB),"{:,}".format(jobKBrate),str(jobsum[8]))
sys.stderr.write('\b')
sys.stderr.write(spinner.next())
sys.stderr.flush()

#Top 20 poorest accelerator optimization jobs
poorest_accel = open(str(int(runtime_start)) + "_sorted_poorest_accelerator_optimization_rates_" + filename, "w")
#if accelstatsdb[0]:
if len(accelstatsdb) > 0:
    accelstatsdb.sort(key = lambda x: (float(x[5][0])), reverse=True)       # secondary sort key of how much accelerator sent
    accelstatsdb.sort(key = lambda x: (float(x[5][2])))             # primary sort key of % sent
    count = 0
    print "\nThe 20 poorest optimized accelerator enabled jobs are:"
    print "\t","Job ID".rjust(10),"Client Name".rjust(client_col_length+2),"Policy Name".rjust(policy_col_length+2),"Schedule Name".rjust(schedule_col_length+2),"Total Bytes".rjust(17),"Optimization".rjust(13),"Sent Bytes".rjust(17)
    poorest_accel.write("".join(["\t","Job ID".rjust(10),"Client Name".rjust(client_col_length+2),"Policy Name".rjust(policy_col_length+2),"Schedule Name".rjust(schedule_col_length+2),"Total Bytes".rjust(17),"Optimization".rjust(13),"Sent Bytes".rjust(17),"\n"]))
    for job in accelstatsdb:
        count = count + 1
        poorest_accel.write("".join(["\t",str(job[0]).rjust(10),str(job[1]).rjust(client_col_length+2),str(job[2]).rjust(policy_col_length+2),str(job[3]).rjust(schedule_col_length+2),"{:17,}".format(int(job[5][1])),"{:11,.1f}".format(float(job[5][2]))," %","{:17,}".format(int(job[5][0])),"\n"]))
        if (count < 20):
            print "\t",str(job[0]).rjust(10),str(job[1]).rjust(client_col_length+2),str(job[2]).rjust(policy_col_length+2),str(job[3]).rjust(schedule_col_length+2),"{:17,}".format(int(job[5][1])),"{:11,.1f}".format(float(job[5][2])),"%","{:17,}".format(int(job[5][0]))
else:
    print "\nThere were no accelerator enabled backups reported which completed with a status 0 or status 1.\n"
poorest_accel.close()
sys.stderr.write('\b')
sys.stderr.write(spinner.next())
sys.stderr.flush()

#Top 20 longest replications or duplications
jobdb.sort(key = lambda x: int(x[11]),reverse = True)
print "\nTop 20 longest running replications or duplications:"
print "\t","Job ID".rjust(10),"Elapsed Time".rjust(12),"Policy Name".rjust(policy_col_length+2),"Schedule Name".rjust(schedule_col_length+2),"Storage Unit".rjust(stu_col_length+2),"   Job Size MB  Number of Images"
count = 0
for job in jobdb:
    if ((job[1] == 4 or job[1] == 7 or job[1] == 20 or job[1] == 23) and (job[2] == 3)):
        count = count + 1
        jobsum=[job[0],convert_elapsed(int(job[11])),job[6],job[4],job[5],job[8],job[16],job[17]]
        jobMB = (float(jobsum[6])/1024) if jobsum[6] else 0
        if count <= 20:
            print "\t",str(jobsum[0]).rjust(10),jobsum[1].rjust(12),jobsum[3].rjust(policy_col_length+2),jobsum[4].rjust(schedule_col_length+2),jobsum[5].rjust(stu_col_length+2),"%14s %17s" % ("{:14,.2f}".format(jobMB),"{:,}".format(int(job[20])))
sys.stderr.write('\b')
sys.stderr.write(spinner.next())
sys.stderr.flush()

#Top 20 biggest full buffer delays
count = 0
waited_for_full.sort(key = lambda x: int(x[5]),reverse = True)
print "\nThe top 20 largest full buffer (parent bptm waiting for data) delays."
print "\t","Job ID".rjust(10),"Client name".rjust(client_col_length+2),"Policy".rjust(policy_col_length+2),"Schedule".rjust(schedule_col_length+2),"Waited Times Delayed Times  Delayed Minutes "
for line in waited_for_full:
    print "\t",str(line[0]).rjust(10),str(line[1]).rjust(client_col_length+2),str(line[2]).rjust(policy_col_length+2),str(line[3]).rjust(schedule_col_length+2),str(line[4]).rjust(12),str(line[5]).rjust(13),str(convert_elapsed(int(int(line[5])*0.015))).rjust(16)
    count = count + 1
    if count == 20:
        break
sys.stderr.write('\b')
sys.stderr.write(spinner.next())
sys.stderr.flush()

#Determine bptm delays between waited for full buffers and exiting for jobs
count = 0
print "\nTop 20 largest bptm exiting delays between \"waited for full buffer\" and \"EXITING\":"
print "* Times have been extracted from the job details and no timezone conversion is needed *"
print "\t","Job ID".rjust(10),"Storage Unit".rjust(stu_col_length+2),"bptm buffer timestamp".rjust(23),"bptm EXITING timestamp".rjust(24),"Diff Seconds".rjust(14),"Diff Converted".rjust(16),"Policy".ljust(policy_col_length+2)
waited_for_full.sort(key = lambda x: int(x[11]),reverse = True)
for line in waited_for_full:
    print "\t",str(line[0]).rjust(10),str(line[7]).rjust(stu_col_length+2),str(line[8]).rjust(23),str(line[9]).rjust(24),str(line[11]).rjust(14),str(line[10]).rjust(16),str(line[2]).ljust(policy_col_length+2)
    count = count + 1
    if count == 20:
        break
sys.stderr.write('\b')
sys.stderr.write(spinner.next())
sys.stderr.flush()

#Report on Backup deduplication percentages
print "\nBackup Deduplication range for MSDP storage pools:"
jobdb.sort(key = lambda x: float(x[16]))            #secondary sort key job kb written
jobdb.sort(key = lambda x: float(x[19]),reverse = True)     #primary sort key dedup rate
max = 0.0
min = 100.0
count = 0
sum = 0.0
if float(jobdb[0][19]) < 0:
        print "\tThere are no jobs with an MSDP deduplication rate to be reported"
else:
        for line in jobdb:
            if (float(line[19]) > max): max = float(line[19])
            if (float(line[19]) >= 0) and (float(line[19]) < min): min = float(line[19])
            if (float(line[19]) >= 0):
                count = count + 1
                sum = sum + float(line[19])
        print "\tThere are {:,}".format(count),"jobs that report a deduplication rate."
        print "\tThe max dedupe rate is {:.2f}".format(max),"and the min dedupe rate is {:.2f}".format(min)
        print "\tThe averaged deduplication rate across these jobs is {:.2f}".format(sum/count)
        print "\n\tThe 20 jobs with the poorest deduplication rates, that backed up at least 100MB, are:"
        print "\t\t","Job ID".rjust(10),"Client name".rjust(client_col_length+2),"Policy".rjust(policy_col_length+2),"Schedule".rjust(schedule_col_length+2),"Storage Unit".rjust(stu_col_length+2),"Job Size".rjust(17),"  Deduplication Rate"
        count=0
        for line in reversed(jobdb):
            if (line[19] > -1) and (line[16] >= 102400):
                print "\t\t",str(line[0]).rjust(10),line[6].rjust(client_col_length+2),line[4].rjust(policy_col_length+2),line[5].rjust(schedule_col_length+2),line[8].rjust(stu_col_length+2),"{:14,.2f}".format(int(line[16])/1024),"MB {:8,.2f}".format(line[19])
                count = count + 1
            if count == 20: break
sys.stderr.write('\b')
sys.stderr.write(spinner.next())
sys.stderr.flush()

#Report on Replication deduplication percentages
poorest_reps = open(str(int(runtime_start)) + "_sorted_poorest_replication_rates_" + filename, "w")
msdprepdb.sort(key = lambda x: float(x[5][2]))              # secondary key sort by the job kb sent field, largest to smallest
msdprepdb.sort(key = lambda x: float(x[5][4]),reverse = True)   # primary key sort by the deduplication percentage field, largest to smallest
if len(msdprepdb) == 0:
    poorest_reps.write("There are no MSDP replications.\n")
    print "\nThere are no MSDP replications to calculate."
else:
    max = float(msdprepdb[0][5][4])
    min = float(msdprepdb[len(msdprepdb)-1][5][4])
    if (target_storage_server_col_length < 21):   target_storage_server_col_length = 21    # make sure the field is at least as long as the column heading
    print "\nReplication deduplication percentages:\n"
    print "\tBest dedupe rate for replications:  ","{:5,.1f}".format(max)
    print "\tWorst dedupe rate for replications: ","{:5,.1f}".format(min),"\n"
    print "\tThe 20 poorest image replication deduplication rates (could be more than 1 per job):"
    print "\t\t","Job ID".rjust(10),"Policy Name".rjust(policy_col_length+2),"Schedule".rjust(schedule_col_length+2),"Destination".rjust(stu_col_length+2),"Target Storage Server".rjust(target_storage_server_col_length+2),"Image Size".rjust(16),"Dedupe Rate".rjust(13),"  Qty Transferred",str("Start Time").rjust(23),str("End Time").rjust(22),str("Elapsed Time").rjust(14),"  Backup ID"
    poorest_reps.write("".join(["\t",str("Job ID").rjust(10),str("Policy Name").rjust(policy_col_length+2),str("Schedule").rjust(schedule_col_length+2),str("Destination").rjust(stu_col_length+2),str("Target Storage Server").rjust(target_storage_server_col_length+2),str("Images Size").rjust(16),str("Dedupe Rate").rjust(13),"  Qty Transferred",str("Start Time").rjust(23),str("End Time").rjust(22),str("Elapsed Time").rjust(14),"  Backup ID\n"]))
    count = 0
    transferred_images = len(msdprepdb)
    for line in reversed(msdprepdb):
        poorest_reps.write("".join(["\t",str(line[0]).rjust(10),str(line[1]).rjust(policy_col_length+2),str(line[2]).rjust(schedule_col_length+2),str(line[3]).rjust(stu_col_length+2),str(line[4]).rjust(target_storage_server_col_length+2),"{:13,}".format(int(line[5][1]))," KB @ ","{:8,.2f}".format(float(line[5][4])),"% ","{:14,}".format(int(line[5][2]))," KB ",str(line[7]).rjust(22),str(line[8]).rjust(22),str(convert_elapsed(line[9])).rjust(14),"  ",str(line[6]),"\n"]))
        if (count < 20):
            print "\t\t",str(line[0]).rjust(10),str(line[1]).rjust(policy_col_length+2),str(line[2]).rjust(schedule_col_length+2),str(line[3]).rjust(stu_col_length+2),str(line[4]).rjust(target_storage_server_col_length+2),"{:13,}".format(int(line[5][1])),"KB @ ","{:8,.2f}".format(float(line[5][4])),"%","{:14,}".format(int(line[5][2])),"KB",str(line[7]).rjust(23),str(line[8]).rjust(22),str(convert_elapsed(line[9])).rjust(14)," ",str(line[6])
        count = count + 1
poorest_reps.close()
sys.stderr.write('\b')
sys.stderr.write(spinner.next())
sys.stderr.flush()

#Report on media server backup throughput numbers:  min, max, and avg
# the below reports are off when dealing with 7.6.x.x jobs because $(NF-27) = kbpersec in 7.7 but = trybyteswritten in 7.6 (and $(NF-24) is the real correct value
if mediaserver_col_length < len(str("Media Server")):   mediaserver_col_length = len(str("Media Server"))
print "\nReport on the min, max, and averaged throughput of each media server used for backup jobs, where job size >= 100MB:\n"
print "\t",str("Media Server").rjust(mediaserver_col_length+2),"|",str("Slowest KB/second").rjust(18),str("Job ID").rjust(11)," | ",str("Fastest MB/second").rjust(18),str("Job ID").rjust(11)," | ",str("Job Count").rjust(10)," | Averaged Throughput MB/second"
for mediaserver in sorted(mediaserversused):
    count = 0
    totalthruput = 0
    min = [0,1000000000]   # [jobid, kb/sec]
    max = [0,0]            # [jobid, kb/sec]
    for job in jobdb:
        if job[7] == mediaserver and job[2] == 3 and (int(job[3]) < 2) and (job[16] >= 102400) and (job[1] == 0 or job[1] == 1 or job[1] == 6 or job[1] == 22):
            count = count + 1
            if int(min[1]) > int(job[17]):
                min[0] = job[0]
                min[1] = job[17]
                #print "(min) jobid = ",job[0],"type = ",job[1],"state = ",job[2],"jobkbwritten = ",job[16],"jobfinalkbpersec = ",job[17]
            if int(max[1]) < int(job[17]):
                max[0] = job[0]
                max[1] = job[17]
                #print "(max) jobid = ",job[0],"type = ",job[1],"state = ",job[2],"jobkbwritten = ",job[16],"jobfinalkbpersec = ",job[17]
            totalthruput = totalthruput + job[17]
    if count > 0:
        avg_thruput = float(totalthruput / count)
        print "\t",str(mediaserver).rjust(mediaserver_col_length+2),"|","{:18,}".format(int(min[1])),str(min[0]).rjust(11)," | ","{:18,.2f}".format(float(max[1])/1024),str(max[0]).rjust(11)," |","{:11,}".format(int(count))," |","{:10,.2f}".format(avg_thruput/1024)
    else:
        print "\t",str(mediaserver).rjust(mediaserver_col_length+2),"does not have any backup jobs counted here."
sys.stderr.write('\b')
sys.stderr.write(spinner.next())
sys.stderr.flush()

#Report on STU throughput numbers:  min, max, and avg
# the below reports are off when dealing with 7.6.x.x jobs because $(NF-27) = kbpersec in 7.7 but = trybyteswritten in 7.6 (and $(NF-24) is the real correct value
stu_col_length = 0
for stu in stusused:
    if (stu_col_length < len(stu)):   stu_col_length = len(stu)
if stu_col_length < len(str("Storage Unit")):   mediaserver_col_length = len(str("Storage Unit"))
print "\nReport on the min, max, and averaged throughput of each storage unit used for backup jobs, where job size >= 100MB:\n"
print "\t",str("Storage Unit").rjust(stu_col_length+2),"|",str("Slowest KB/second").rjust(18),str("Job ID").rjust(11)," | ",str("Fastest MB/second").rjust(18),str("Job ID").rjust(11)," | ",str("Job Count").rjust(10)," | Averaged Throughput MB/second"
for stu in sorted(stusused):
    count = 0
    totalthruput = 0
    min = [0,1000000000]   # [jobid, kb/sec]
    max = [0,0]            # [jobid, kb/sec]
    for job in jobdb:
        if job[8] == stu and job[2] == 3 and (int(job[3]) < 2) and (job[16] >= 102400) and (job[1] == 0 or job[1] == 1 or job[1] == 6 or job[1] == 22):
            count = count + 1
            if int(min[1]) > int(job[17]):
                min[0] = job[0]
                min[1] = job[17]
                #print "(min) jobid = ",job[0],"type = ",job[1],"state = ",job[2],"jobkbwritten = ",job[16],"jobfinalkbpersec = ",job[17]
            if int(max[1]) < int(job[17]):
                max[0] = job[0]
                max[1] = job[17]
                #print "(max) jobid = ",job[0],"type = ",job[1],"state = ",job[2],"jobkbwritten = ",job[16],"jobfinalkbpersec = ",job[17]
            totalthruput = totalthruput + job[17]
    if count > 0:
        avg_thruput = float(totalthruput / count)
        print "\t",str(stu).rjust(stu_col_length+2),"|","{:18,}".format(int(min[1])),str(min[0]).rjust(11)," | ","{:18,.2f}".format(float(max[1])/1024),str(max[0]).rjust(11)," |","{:11,}".format(int(count))," |","{:10,.2f}".format(avg_thruput/1024)
    else:
        print "\t",str(stu).rjust(stu_col_length+2),"does not have any backup jobs counted here."
sys.stderr.write('\b')
sys.stderr.write(spinner.next())
sys.stderr.flush()


#Report on media server replication throughput numbers:  min, max, and avg

#Report on throughput numbers per policy name:  min, max, and avg
# the below reports are off when dealing with 7.6.x.x jobs because $(NF-27) = kbpersec in 7.7 but = trybyteswritten in 7.6 (and $(NF-24) is the real correct value
if policy_col_length < len(str("Policy Name")):   policy_col_length = len(str("Policy Name"))
print "\nReport on the min, max, and averaged throughput of each Policy used for backup jobs, where elapsed time > 1 minute:\n"
print "\t",str("Policy Name").rjust(policy_col_length+2),"|",str("Slowest KB/second").rjust(18),str("Job ID").rjust(11)," | ",str("Fastest MB/second").rjust(18),str("Job ID").rjust(11)," | ",str("Job Count").rjust(10)," | Averaged Throughput MB/second"
policy_avg_backup = collections.defaultdict(list)
for job in jobdb:
    if ((job[1] == 0 or job[1] == 1 or job[1] == 22) and (job[2] == 3) and (int(job[3]) <= 1) and (len(job[5]) > 1)):
        policyname = str(job[4])
        policy_avg_backup[policyname].append(job[17])
pab = collections.OrderedDict(sorted(policy_avg_backup.items()))
for policy in pab.items():
    policyname = policy[0]
    count = 0
    totalthruput = 0
    min = [0,1000000000]   # [jobid, kb/sec]
    max = [0,0]            # [jobid, kb/sec]
    for job in jobdb:
        if job[4] == policyname and job[2] == 3 and (int(job[3]) < 2) and (int(job[11]) >= 60) and job[16] and (job[1] == 0 or job[1] == 1 or job[1] == 6 or job[1] == 22):
            count = count + 1
            if int(min[1]) > int(job[17]):
                min[0] = job[0]
                min[1] = job[17]
                #print "(min) jobid = ",job[0],"type = ",job[1],"state = ",job[2],"jobkbwritten = ",job[16],"jobfinalkbpersec = ",job[17]
            if int(max[1]) < int(job[17]):
                max[0] = job[0]
                max[1] = job[17]
                #print "(max) jobid = ",job[0],"type = ",job[1],"state = ",job[2],"jobkbwritten = ",job[16],"jobfinalkbpersec = ",job[17]
            totalthruput = totalthruput + job[17]
    if count > 0:
        avg_thruput = float(totalthruput / count)
        print "\t",str(policyname).rjust(policy_col_length+2),"|","{:18,}".format(int(min[1])),str(min[0]).rjust(11)," | ","{:18,.2f}".format(float(max[1])/1024),str(max[0]).rjust(11)," |","{:11,}".format(int(count))," |","{:10,.2f}".format(avg_thruput/1024)
    else:
        print "\t",str(policyname).rjust(policy_col_length+2),"does not have any backup jobs counted here."
sys.stderr.write('\b')
sys.stderr.write(spinner.next())
sys.stderr.flush()

#Generate a heat map, of such, reporting on number of concurrent jobs running every 15 minutes, per storage unit.
#           stuA    stuB    stuC    ...
# date1       #       #       #     ...
# date2       #       #       #     ...
# ...
# calculate the first (oldest) timestamp 15-minute mark so we can always be viewing traditional 15 minute segments, like 12:00, 12:15, 12:30, 12:45, ...
sys.stderr.write("\bGenerating STU heatmap.\n")
end_timestamp = base_timestamp
start_timestamp = base_timestamp
#sys.stderr.write("initializing: start_timestamp = "+str(start_timestamp)+" end_timestamp = "+str(end_timestamp)+"\n")
#sys.stderr.write("before checks: oldestjob_start_timestamp = "+str(oldestjob_start_timestamp)+" and start_timestamp = "+str(start_timestamp)+"\n")
if int(oldestjob_start_timestamp) <= int(start_timestamp):
    while int(oldestjob_start_timestamp) <= int(start_timestamp):
        start_timestamp = start_timestamp - heatmap_interval           # decrease in 15 minute intervals.
elif int(oldestjob_start_timestamp) > int(start_timestamp):
    while int(oldestjob_start_timestamp) > int(start_timestamp):
        start_timestamp = start_timestamp + heatmap_interval           # increment in 15 minute intervals.
    start_timestamp = start_timestamp - heatmap_interval              # base_timestamp needs to be the 15 minute interval before the oldestjob_start_timestamp
if newestjob_start_timestamp  > end_timestamp:          # make sure there is a slot for the most recent job start time to be counted
    while newestjob_start_timestamp > end_timestamp:
        end_timestamp = end_timestamp + heatmap_interval
elif newestjob_start_timestamp < end_timestamp:
    while newestjob_start_timestamp < end_timestamp:
        end_timestamp = end_timestamp - heatmap_interval
    end_timestamp = end_timestamp + (heatmap_interval*2)
while end_timestamp < most_recent_job_end:
    end_timestamp = end_timestamp + heatmap_interval
if int(start_timestamp) >= int(oldestjob_start_timestamp):
    sys.stderr.write("hmmm...something didn't calculate correctly when determining the earliest start interval.  oldestjob_start_time = "+str(int(oldestjob_start_time))+" and start_timestamp = "+str(int(start_timestamp))+"\n")
#sys.stderr.write("calculated: start_timestamp = "+str(start_timestamp)+" end_timestamp = "+str(end_timestamp)+"\n")
# create a nested dictionary where heatmap['timestamp']['stu?'] = jobcount
# build the nested dictorionary first
#import random
stu_heatmap = collections.defaultdict(dict)
policy_heatmap = collections.defaultdict(dict)
column_headers = (sorted(stusused)) + (["_total_"])
policy_column_headers = (sorted(policynames)) + (["_total_"])
#sys.stderr.write("column_headers = "+str(column_headers)+" and stusused = "+str(sorted(stusused))+"\n")
#sys.stderr.write("policy_column_headers = "+str(policy_column_headers)+"\n")
for time_interval in range(int(start_timestamp),int(end_timestamp), heatmap_interval):
    for stu in column_headers:
        #stu_heatmap[time_interval][stu] = 0
        stu_heatmap[time_interval][stu] = {'failure': 0,'total': 0}   # (failed count, total count)
    for policy in policy_column_headers:
        policy_heatmap[time_interval][policy] = {'failure': 0,'total': 0}   # (failed count, total count)
#sys.stderr.write("policy_heatmap = "+str(policy_heatmap)+"\n")
time_segments = sorted(stu_heatmap.items())
number_segments = len(time_segments)
#example stu_start_end_times array value to parse: jobid, # of tries, stu, job start, job elapsed, job end, try start, try elapsed, try end, ...
# stu_start_end_times = [96262, '2', '4239', 'stu_disk_mspd5200-1', [('1484982004', '0000000011', '1484982015', '4239'), ('1484982616', '0000000005', '1484982621', '4239')]]
for se_job in stu_start_end_times:
    sys.stderr.write(spinner.next())
    sys.stderr.flush()
    se_jobtry = 1
    #sys.stderr.write("se_job = "+(str(se_job))+"\n")
    while se_job[1] and se_jobtry <= int(se_job[1]):
        jt_start = se_job[4][(-1+se_jobtry)][0]
        jt_end = se_job[4][(-1+se_jobtry)][2]
        jt_status = int(se_job[4][(-1+se_jobtry)][3]) if se_job[4][(-1+se_jobtry)][3].isdigit() else int(0)     # use zero if the job status field is blank in the job try details
        if int(jt_start) == 0 and int(jt_end) == 0:
            se_jobtry = se_jobtry + 1
            continue                    # to account for a job try with zero for both start and end times, as seen in a client's job dump; no need to go on with the below so just skip to the next job try
        if int(jt_end) == 0:            # because the job has not ended
            jt_end = end_timestamp      # set it to the very last timestamp since we still want to count it if it started before the last interval
        if int(jt_start) == 0:          # some kind of abort, like a status 50 or 2074, etc...
            jt_start = jt_end
        jt_stu = se_job[3]
        if not jt_stu and int(jt_start) == 0:   #job may be queued or has not had the STU allocated to it yet so skip it - real world example
            se_jobtry = se_jobtry + 1
            continue
        if jt_stu not in stusused:
            sys.stderr.write("Job "+str(se_job[0])+" doesn't have it's storage unit, "+str(jt_stu)+" defined in the STUs used for some reason.\n")
            se_jobtry = se_jobtry + 1
            continue
        jt_start_marked = 0
        old_datefield = time_segments[-1][0]
        for datefield in time_segments:
            timefield = int(datefield[0])
            if jt_start_marked == 0 and ((int(jt_start) >= int(timefield)) and (int(jt_start) < (int(timefield)+heatmap_interval))):        # since we are starting with a time window just before the 1st job then we need to mark this "box" since the job is starting before the next period
                jt_start_marked = 1
                #sys.stderr.write("se_job = "+str(se_job)+"\n")
                if int(jt_status) <= 1:                 #job status <= 1 then count as success and don't increment failure count
                    stu_heatmap[timefield][jt_stu]['total'] = stu_heatmap[timefield][jt_stu]['total'] + 1
                    stu_heatmap[timefield]["_total_"]['total'] = stu_heatmap[timefield]["_total_"]['total'] + 1
                if int(jt_status) > 1:
                    stu_heatmap[timefield][jt_stu]['failure'] = stu_heatmap[timefield][jt_stu]['failure'] + 1
                    stu_heatmap[timefield]["_total_"]['failure'] = stu_heatmap[timefield]["_total_"]['failure'] + 1
                    stu_heatmap[timefield][jt_stu]['total'] = stu_heatmap[timefield][jt_stu]['total'] + 1
                    stu_heatmap[timefield]["_total_"]['total'] = stu_heatmap[timefield]["_total_"]['total'] + 1
                old_datefield = timefield                           # we have already marked the start of the job so break out of this loop; we don't need to mark anything else
                break
        else:
            sys.stderr.write("Wasn't able to put the start time, "+str(timefield)+", for job "+str(se_job[0])+" into the stu heatmap for job try # "+str(se_jobtry)+"\n")
            sys.stderr.write("se_job = "+(str(se_job))+"\n")
            #sys.stderr.write("jobid = "+str(se_job[0])+" se_jobtry = "+str(se_jobtry)+" jt_start = "+str(jt_start)+" jt_end = "+str(jt_end)+" jt_stu = "+str(jt_stu)+"\n")
        for datefield in time_segments:
            timefield = datefield[0]
            if int(old_datefield) > int(timefield):
                # do nothing
                noop=1
            else:
                if int(old_datefield) == int(timefield) and jt_start_marked == 1:
                    #do nothing again because we've already marked this time period with the start of the job
                    noop=1
                else:
                    if int(old_datefield) < int(timefield) and int(jt_end) > int(timefield):
                        if int(jt_status) <= 1:                 #job status <= 1 then count as success and don't increment failure count
                            stu_heatmap[timefield][jt_stu]['total'] = stu_heatmap[timefield][jt_stu]['total'] + 1
                            stu_heatmap[timefield]["_total_"]['total'] = stu_heatmap[timefield]["_total_"]['total'] + 1
                        if int(jt_status) > 1:
                            stu_heatmap[timefield][jt_stu]['failure'] = stu_heatmap[timefield][jt_stu]['failure'] + 1
                            stu_heatmap[timefield]["_total_"]['failure'] = stu_heatmap[timefield]["_total_"]['failure'] + 1
                            stu_heatmap[timefield][jt_stu]['total'] = stu_heatmap[timefield][jt_stu]['total'] + 1
                            stu_heatmap[timefield]["_total_"]['total'] = stu_heatmap[timefield]["_total_"]['total'] + 1
                    if int(old_datefield) < int(timefield) and int(jt_end) > (int(timefield)+heatmap_interval):          # not really worrying here if jt_end == datefield because that would mean the job ended on the boundary and the stu should be freed up by then
                        break
        se_jobtry = se_jobtry + 1
    sys.stderr.write('\b')
#the below is for readability to remove all the zeros and leave those blank
for time_interval in range(int(start_timestamp),int(end_timestamp), heatmap_interval):
    for stu in sorted(stusused):
        if stu_heatmap[time_interval][stu] == 0:
            stu_heatmap[time_interval][stu] = ""
print "\nBelow is a STU heatmap calculated using the job try start and end times, by storage unit allocation.\nSTUs are counted if they are running at any time between the lower time and the next time interval.\nFormat is (failure/total).\n"
print str("Timestamp").rjust(25),"|  _total_  |","|".join(str(stu).center(len(stu),"_") for stu in sorted(stu_heatmap.items()[0][1].keys()) if stu not in {"_total_"}),"|"        # all this to print the column headers in the order in which they are stored, not how they were created
report_line = 0
for time_interval in sorted(stu_heatmap.items()):
    ms_tz=pytz.timezone(str(get_localzone()))
    ms_dt=ms_tz.localize(datetime.datetime.fromtimestamp(time_interval[0])).astimezone(pytz.timezone(ms_timezone))
    print ms_dt,"|","{:4,}".format(time_interval[1]["_total_"]['failure'])+"/"+"{:4,}".format(time_interval[1]["_total_"]['total']),"|","|".join(str(str(g[1]['failure'])+"/"+str(g[1]['total'])).center(len(str(g[0])),"_") for f,g in enumerate(sorted(time_interval[1].items())) if g[0] not in {"_total_"}),"|"
    report_line = report_line + 1
    if ((report_line % 17) == 0):
        print str("Timestamp").rjust(25),"|  _total_  |","|".join(str(stu).center(len(stu),"_") for stu in sorted(stu_heatmap.items()[0][1].keys()) if stu not in {"_total_"}),"|"        # all this to print the column headers in the order in which they are stored, not how they were created

sys.stderr.write("Generating policy heatmap.\n")
# policy_start_end_times = [96263, '2', '4239', 'Vm_NBU_VMs', '-', 'BMR_opscenter_test', [('1484982005', '0000000010', '1484982015', '4239'), ('1484982617', '0000000006', '1484982623', '4239')]]
for se_job in policy_start_end_times:
    sys.stderr.write(spinner.next())
    sys.stderr.flush()
    se_jobtry = 1
    while se_job[1] and se_jobtry <= int(se_job[1]):
        #sys.stderr.write("se_job = "+str(se_job)+"\n")
        if len(se_job[6]) < 1:
            break
        jt_start = se_job[6][(-1+se_jobtry)][0]
        jt_end = se_job[6][(-1+se_jobtry)][2]
        jt_status = int(se_job[6][(-1+se_jobtry)][3]) if se_job[6][(-1+se_jobtry)][3].isdigit() else int(0)     # use zero if the job status field is blank in the job try details
        if int(jt_start) == 0 and int(jt_end) == 0: # if the job has no start or end time then we can't process it, so skip it
            se_jobtry = se_jobtry + 1
            continue                    # to account for a job try with zero for both start and end times, as seen in a client's job dump; no need to go on with the below so just skip to the next job try
        if int(jt_end) == 0:            # because the job has not ended
            jt_end = end_timestamp      # set it to the very last timestamp since we still want to count it if it started before the last interval
        if int(jt_start) == 0:          # some kind of abort, like a status 50 or 2074, etc...
            jt_start = jt_end
        jt_policy = se_job[3]
        if not jt_policy and int(jt_start) == 0:   #job may be queued or has not had the STU allocated to it yet so skip it - real world example
            se_jobtry = se_jobtry + 1
            continue
        if jt_policy not in policynames:
            sys.stderr.write("Job "+str(se_job[0])+" doesn't have it's policy, "+str(jt_policy)+" defined in the STUs used for some reason.\n")
            se_jobtry = se_jobtry + 1
            continue
        jt_start_marked = 0
        old_datefield = time_segments[-1][0]
        for datefield in time_segments:
            timefield = int(datefield[0])
            if jt_start_marked == 0 and (int(jt_start) >= int(timefield) and (int(jt_start) < (int(timefield)+heatmap_interval))):        # since we are starting with a time window just before the 1st job then we need to mark this "box" since the job is starting before the next period
                jt_start_marked = 1
                #sys.stderr.write("se_job = "+str(se_job)+"\n")
                if not se_job[2]:   # this is a job that has not completed yet so it is still running and we'll consider it not-failed here
                    se_job[2] = 0
                if int(jt_status) <= 1:         #job status <= 1 then count as success and don't increment failure count
                    policy_heatmap[timefield][jt_policy]['total'] = policy_heatmap[timefield][jt_policy]['total'] + 1
                    policy_heatmap[timefield]["_total_"]['total'] = policy_heatmap[timefield]["_total_"]['total'] + 1
                if int(jt_status) > 1:
                    policy_heatmap[timefield][jt_policy]['failure'] = policy_heatmap[timefield][jt_policy]['failure'] + 1
                    policy_heatmap[timefield]["_total_"]['failure'] = policy_heatmap[timefield]["_total_"]['failure'] + 1
                    policy_heatmap[timefield][jt_policy]['total'] = policy_heatmap[timefield][jt_policy]['total'] + 1
                    policy_heatmap[timefield]["_total_"]['total'] = policy_heatmap[timefield]["_total_"]['total'] + 1
                old_datefield = timefield                           # we have already marked the start of the job so break out of this loop; we don't need to mark anything else
                break
        else:
            sys.stderr.write("Wasn't able to put the start time, "+str(timefield)+", for job "+str(se_job[0])+" into the heatmap for job try # "+str(se_jobtry)+"\n")
            sys.stderr.write("se_job = "+(str(se_job))+"\n")
        for datefield in time_segments:
            timefield = datefield[0]
            if int(old_datefield) > int(timefield):
                # do nothing
                noop=1
            else:
                if int(old_datefield) == int(timefield) and jt_start_marked == 1:
                    #do nothing again because we've already marked this time period with the start of the job
                    noop=1
                else:
                    if int(old_datefield) < int(timefield) and int(jt_end) > int(timefield):
                        if int(jt_status) <= 1:         #job status <= 1 then count as success and don't increment failure count
                           policy_heatmap[timefield][jt_policy]['total'] = policy_heatmap[timefield][jt_policy]['total'] + 1
                           policy_heatmap[timefield]["_total_"]['total'] = policy_heatmap[timefield]["_total_"]['total'] + 1
                        if int(jt_status) > 1:
                           policy_heatmap[timefield][jt_policy]['failure'] = policy_heatmap[timefield][jt_policy]['failure'] + 1
                           policy_heatmap[timefield]["_total_"]['failure'] = policy_heatmap[timefield]["_total_"]['failure'] + 1
                           policy_heatmap[timefield][jt_policy]['total'] = policy_heatmap[timefield][jt_policy]['total'] + 1
                           policy_heatmap[timefield]["_total_"]['total'] = policy_heatmap[timefield]["_total_"]['total'] + 1
                    if int(old_datefield) < int(timefield) and int(jt_end) > (int(timefield)+heatmap_interval):          # not really worrying here if jt_end == datefield because that would mean the job ended on the boundary and the policy should be freed up by then
                        break
        se_jobtry = se_jobtry + 1
    sys.stderr.write('\b')
print "\nBelow is the policy failure heatmap.  Times reported are the times the interval when the policy was running through the time it ended with a failure.\nFormat is (failures/totals).\n"
print str("Timestamp").rjust(25),":  _total_  :","|".join(str(policy).center(policy_col_length,'_') for policy in sorted(policy_heatmap.items()[0][1].keys()) if policy not in {"_total_"}),"|"        # all this to print the column headers in the order in which they are stored, not how they were created
report_line = 0
for time_interval in sorted(policy_heatmap.items()):
    ms_tz=pytz.timezone(str(get_localzone()))
    ms_dt=ms_tz.localize(datetime.datetime.fromtimestamp(time_interval[0])).astimezone(pytz.timezone(ms_timezone))
    print ms_dt,"|","{:4,}".format(time_interval[1]["_total_"]['failure'])+"/"+"{:4,}".format(time_interval[1]["_total_"]['total']),"|","|".join(str(str(g[1]['failure'])+"/"+str(g[1]['total'])).center(policy_col_length,"_") for f,g in enumerate(sorted(time_interval[1].items())) if g[0] not in {"_total_"}),"|"
    report_line = report_line + 1
    if ((report_line % 17) == 0):
        print str("Timestamp").rjust(25),":  _total_  :","|".join(str(policy).center(policy_col_length,'_') for policy in sorted(policy_heatmap.items()[0][1].keys()) if policy not in {"_total_"}),"|"        # print a new column header for readability

sys.stdout = orig_stdout
new_stdout.close()
print "The output file is: ","process_jobs_" + str(int(runtime_start)) + "_" + filename
print "This file took %f seconds to process" % (time.time() - runtime_start)

if args['compress'] and not args['email']:      # The email process creates a tarball anyway so don't need to run it twice if also emailing
    create_tarball()

if args['email']:
    tarfilename = create_tarball()
    import smtplib
    from email.MIMEMultipart import MIMEMultipart
    from email.MIMEBase import MIMEBase
    from email.mime.text import MIMEText
    from email import Encoders


    recipients = str(args['email'][2]).split(",")
    SUBJECT = "process_jobs analysis of "+str(filename)

    msg = MIMEMultipart()
    msg['Subject'] = SUBJECT
    msg['From'] = args['email'][1]
    msg['To'] = ", ".join(recipients)

    #print "Msg so far = \n",msg

    if args['encrypt']:
        body = "Please see process_jobs output file in the attached encrypted file for details."
        msg.attach(MIMEText(body,'plain'))
    else:
        opf = open("process_jobs_" + str(int(runtime_start)) + "_" + filename, 'rb')
        msg.attach(MIMEText(opf.read(),'plain'))
        opf.close()

    part = MIMEBase('application', "octet-stream")
    part.set_payload(open(tarfilename, "rb").read())
    Encoders.encode_base64(part)

    part.add_header('Content-Disposition', 'attachment; filename=%s' % tarfilename)

    msg.attach(part)

    try:
        server = smtplib.SMTP(args['email'][0])
        server.sendmail(args['email'][1], recipients, msg.as_string())
    except smtplib.SMTPHeloError:
        print "\n***Failed to send the email.  Failed to Helo",args['email'][0]
    except smtplib.SMTPRecipientsRefused:
        print "\n***Failed to send the email.  Email server rejected",args['email'][2]," as recipient(s)."
    except smtplib.SMTPSenderRefused:
        print "\n***Failed to send the email.  Email server rejected",args['email'][1]," as the sender."
    except IOError as e:
        print "\n***Failed to send the email.  I/O error({0}): {1}".format(e.errno, e.strerror)
    else:
        server.quit()
        print "\nEmailed",args['email'][2],"the results of this execution run.\n"

