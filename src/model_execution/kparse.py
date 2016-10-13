#!/usr/bin/python

# NOTE all the json keys must be lower case
import sys
import json
from pprint import pprint

pid_monitor_count = 0
apid_monitor_count = 0
lpid_monitor_count = 0

def leccalc_enabled(lec_options):
	for option in lec_options["outputs"]:
		if lec_options["outputs"][option] == True:
			return True
	return False

def do_post_wait_processing(runtype,data):
	global apid_monitor_count
	global lpid_monitor_count
	summary_set=0
	if "{0}_summaries".format(runtype) in data["analysis_settings"]:
		for summary in data["analysis_settings"]["{0}_summaries".format(runtype)]:
			if "id" in summary:
				summary_set = summary["id"]
				if summary.get("aalcalc") == True:
					apid_monitor_count = apid_monitor_count + 1
					print "aalsummary -K{0}_S{1}_aalcalc > output/{0}_S{1}_aalcalc.csv &  apid{2}=$!".format(runtype,summary_set, apid_monitor_count)
				if summary.get("lec_output") == True:
					if "leccalc" in summary:
						if leccalc_enabled(summary["leccalc"]):	
							return_period_option=""
							if summary["leccalc"]["return_period_file"] == True: return_period_option="-r"
							sys.stdout.write("leccalc {0} -K{1}_S{2}_summaryleccalc".format(return_period_option,runtype,summary_set))
							lpid_monitor_count = lpid_monitor_count + 1
							for option in summary["leccalc"]["outputs"]:
								switch=""
								if summary["leccalc"]["outputs"][option] == True:
									if option == "full_uncertainty_aep": switch = "-F"
									if option == "wheatsheaf_aep": switch = "-W"
									if option == "sample_mean_aep": switch = "-S"
									if option == "full_uncertainty_oep": switch = "-f"
									if option == "wheatsheaf_oep": switch = "-w"
									if option == "sample_mean_oep": switch = "-s"
									if option == "wheatsheaf_mean_aep": switch = "-M"
									if option == "wheatsheaf_mean_oep": switch = "-m"
									sys.stdout.write(" {0} output/{1}_S{2}_leccalc_{3}.csv".format(switch,runtype,summary_set, option))
							print "  &  lpid{3}=$!".format(runtype,summary_set, option,lpid_monitor_count,return_period_option)


def do_fifos(action,runtype,data,process_id):
	summary_set=0
	if "{0}_summaries".format(runtype) in data["analysis_settings"]:
		print "{0} fifo/{1}_P{2}".format(action,runtype,process_id)
		print ""
		for summary in data["analysis_settings"]["{0}_summaries".format(runtype)]:
			if "id" in summary:
				summary_set = summary["id"]
				print "{0} fifo/{1}_S{2}_summary_P{3}".format(action,runtype,summary_set,process_id)
				if summary.get("eltcalc") == True:
					print "{0} fifo/{1}_S{2}_summaryeltcalc_P{3}".format(action,runtype,summary_set,process_id)
					print "{0} fifo/{1}_S{2}_eltcalc_P{3}".format(action,runtype,summary_set,process_id)
				if summary.get("summarycalc") == True:
					print "{0} fifo/{1}_S{2}_summarysummarycalc_P{3}".format(action,runtype,summary_set,process_id)
					print "{0} fifo/{1}_S{2}_summarycalc_P{3}".format(action,runtype,summary_set,process_id)
				if summary.get("pltcalc") == True:
					print "{0} fifo/{1}_S{2}_summarypltcalc_P{3}".format(action,runtype,summary_set,process_id)
					print "{0} fifo/{1}_S{2}_pltcalc_P{3}".format(action,runtype,summary_set,process_id)
				if summary.get("aalcalc") == True:
					print "{0} fifo/{1}_S{2}_summaryaalcalc_P{3}".format(action,runtype,summary_set,process_id)


	print ""

def create_workfolders(runtype,data):
	if "{0}_summaries".format(runtype) in data["analysis_settings"]:
		for summary in data["analysis_settings"]["{0}_summaries".format(runtype)]:
			if "id" in summary:
				summary_set = summary["id"]
				if summary.get("lec_output") == True:
					if leccalc_enabled(summary["leccalc"]) == True:
						print "mkdir work/{0}_S{1}_summaryleccalc".format(runtype,summary_set)


def remove_workfolders(runtype,data):
	if "{0}_summaries".format(runtype) in data["analysis_settings"]:
		for summary in data["analysis_settings"]["{0}_summaries".format(runtype)]:
			if "id" in summary:
				summary_set = summary["id"]
				if summary.get("lec_output") == True:
					if leccalc_enabled(summary["leccalc"]) == True:
						print "rm work/{0}_S{1}_summaryleccalc/*".format(runtype,summary_set)
						print "rmdir work/{0}_S{1}_summaryleccalc".format(runtype,summary_set)
	

def do_make_fifos(runtype,data,process_id):	
	do_fifos("mkfifo",runtype,data,process_id)		

def do_remove_fifos(runtype,data,process_id):	
	do_fifos("rm",runtype,data,process_id)	

def do_kats(runtype,data,max_process_id,background):
	global pid_monitor_count
	anykats = False
	strback = ""
	if background == True: strback="& pid"
	if "{0}_summaries".format(runtype) in data["analysis_settings"]:		
		for summary in data["analysis_settings"]["{0}_summaries".format(runtype)]:
			if "id" in summary:
				summary_set = summary["id"]
				if summary.get("eltcalc") == True:
					anykats = True
					sys.stdout.write("kat ")
					for process_id in range (1, max_process_id+1):
						sys.stdout.write("fifo/{0}_S{1}_eltcalc_P{2} ".format(runtype,summary_set,process_id))
					pid_monitor_count = pid_monitor_count + 1
					print "> output/{0}_S{1}_eltcalc.csv & pid{2}=$!".format(runtype,summary_set,pid_monitor_count)
				if summary.get("pltcalc") == True:
					anykats = True
					sys.stdout.write("kat ")
					for process_id in range (1, max_process_id+1):
						sys.stdout.write("fifo/{0}_S{1}_pltcalc_P{2} ".format(runtype,summary_set,process_id))
					pid_monitor_count = pid_monitor_count + 1
					print "> output/{0}_S{1}_pltcalc.csv & pid{2}=$!".format(runtype,summary_set,pid_monitor_count)
				if summary.get("summarycalc") == True:
					anykats = True
					sys.stdout.write("kat ")
					for process_id in range (1, max_process_id+1):
						sys.stdout.write("fifo/{0}_S{1}_summarycalc_P{2} ".format(runtype,summary_set,process_id))
					pid_monitor_count = pid_monitor_count + 1
					print "> output/{0}_S{1}_summarycalc.csv & pid{2}=$!".format(runtype,summary_set,pid_monitor_count)
	return anykats

def do_summarycalcs(runtype,data,process_id):
	global pid_monitor_count
	summarycalc_switch="-g"
	if runtype == "il":
		summarycalc_switch="-f"
	if "{0}_summaries".format(runtype) in data["analysis_settings"]:		
		sys.stdout.write("summarycalc {0} ".format(summarycalc_switch))
		for summary in data["analysis_settings"]["{0}_summaries".format(runtype)]:
			if "id" in summary:
				summary_set = summary["id"]
				sys.stdout.write("-{0} fifo/{1}_S{0}_summary_P{2} ".format(summary_set,runtype,process_id))				
		print " < fifo/{0}_P{1} &".format(runtype,process_id)

def do_tees(runtype,data,process_id):
	global pid_monitor_count
	summary_set=0
	if "{0}_summaries".format(runtype) in data["analysis_settings"]:
		for summary in data["analysis_settings"]["{0}_summaries".format(runtype)]:
			if "id" in summary:
				pid_monitor_count = pid_monitor_count + 1
				summary_set = summary["id"]
				sys.stdout.write("tee < fifo/{0}_S{1}_summary_P{2} ".format(runtype,summary_set,process_id))
				if summary.get("eltcalc") == True:
					sys.stdout.write("fifo/{0}_S{1}_summaryeltcalc_P{2} ".format(runtype,summary_set,process_id))
				if summary.get("pltcalc") == True:
					sys.stdout.write("fifo/{0}_S{1}_summarypltcalc_P{2} ".format(runtype,summary_set,process_id))
				if summary.get("summarycalc") == True:
					sys.stdout.write("fifo/{0}_S{1}_summarysummarycalc_P{2} ".format(runtype,summary_set,process_id))
				if summary.get("aalcalc") == True:
					sys.stdout.write("fifo/{0}_S{1}_summaryaalcalc_P{2} ".format(runtype,summary_set,process_id))
				if summary.get("lec_output") == True:
					if leccalc_enabled(summary["leccalc"]) == True:
						sys.stdout.write("work/{0}_S{1}_summaryleccalc/P{2}.bin ".format(runtype,summary_set,process_id))
				print " > /dev/null & pid{0}=$!".format(pid_monitor_count)

def do_any(runtype,data,process_id):
	global pid_monitor_count
	summarycalc_switch="-g"
	if runtype == "il":
		summarycalc_switch="-f"

	summary_set=0
	if "{0}_summaries".format(runtype) in data["analysis_settings"]:		
		for summary in data["analysis_settings"]["{0}_summaries".format(runtype)]:
			if "id" in summary:
				summary_set = summary["id"]
				if summary.get("eltcalc") == True:
					print "eltcalc < fifo/{0}_S{1}_summaryeltcalc_P{2} > fifo/{0}_S{1}_eltcalc_P{2} &".format(runtype,summary_set,process_id)
				if summary.get("summarycalc") == True:
					print "summarycalctocsv < fifo/{0}_S{1}_summarysummarycalc_P{2} > fifo/{0}_S{1}_summarycalc_P{2} &".format(runtype,summary_set,process_id)
				if summary.get("pltcalc") == True:
					print "pltcalc < fifo/{0}_S{1}_summarypltcalc_P{2} > fifo/{0}_S{1}_pltcalc_P{2} &".format(runtype,summary_set,process_id)
				if summary.get("aalcalc") == True:
					pid_monitor_count = pid_monitor_count + 1
					print "aalcalc < fifo/{0}_S{1}_summaryaalcalc_P{2} > work/{0}_S{1}_aalcalc_P{2} & pid{2}=$!".format(runtype,summary_set,process_id,pid_monitor_count)
			print ""

		do_tees(runtype,data,process_id)
		do_summarycalcs(runtype,data,process_id)


def do_il(data,max_process_id):	
	for process_id in range (1, max_process_id+1):
		do_any("il",data,process_id)


def do_gul(data,max_process_id):
	for process_id in range (1, max_process_id+1):
		do_any("gul",data,process_id)
	

def do_il_make_fifo(data,max_process_id):	
	for process_id in range (1, max_process_id+1):
		do_make_fifos("il",data,process_id)


def do_gul_make_fifo(data,max_process_id):
	for process_id in range (1, max_process_id+1):
		do_make_fifos("gul",data,process_id)

def do_il_remove_fifo(data,max_process_id):	
	for process_id in range (1, max_process_id+1):
		do_remove_fifos("il",data,process_id)


def do_gul_remove_fifo(data,max_process_id):
	for process_id in range (1, max_process_id+1):
		do_remove_fifos("gul",data,process_id)



def do_waits(wait_variable, wait_count):
	if wait_count > 0:
		sys.stdout.write("wait ")
		for pid in range (1, wait_count+1):
			sys.stdout.write("${0}{1} ".format(wait_variable,pid))
		print ""

def do_pwaits():
	do_waits("pid",pid_monitor_count)		
	
def do_awaits():
	do_waits("apid",apid_monitor_count)	

def do_lwaits():
	do_waits("lpid",lpid_monitor_count)	

def genbash(max_process_id,json_filename):
	gul_threshold = 0
	number_of_samples = 0
	use_random_number_file = ""
	gul_output = False
	il_output = False

	with open(json_filename) as data_file:
		data = json.load(data_file)

	if not "analysis_settings" in data:
		print "analysis_settings not found - invalid json"
		exit()


	if "gul_threshold" in data["analysis_settings"]:
		gul_threshold= data["analysis_settings"]["gul_threshold"]

	if "number_of_samples" in data["analysis_settings"]:
		number_of_samples= data["analysis_settings"]["number_of_samples"]

	if "model_settings" in data["analysis_settings"]:
		if "use_random_number_file" in data["analysis_settings"]["model_settings"]:
			if data["analysis_settings"]["model_settings"]["use_random_number_file"] == True:
				use_random_number_file = "-r"

	if "gul_output" in data["analysis_settings"]:
		gul_output = data["analysis_settings"]["gul_output"]

	if "il_output" in data["analysis_settings"]:
		il_output = data["analysis_settings"]["il_output"]

	print "#!/bin/bash"
# slip through json structure seems okay
	if gul_output:	
		do_gul_make_fifo(data,max_process_id)
		create_workfolders("gul",data)

	print ""

	if il_output: 	
		do_il_make_fifo(data,max_process_id)
		create_workfolders("il",data)

	il_anykats = False
	gul_anykats = False


	print ""
	print "# --- Do insured loss kats ---"
	print ""
	if il_output: 	il_anykats = do_kats("il",data,max_process_id,True)

	print ""
	print "# --- Do ground up loss kats ---"
	print ""
	if gul_output:	gul_anykats = do_kats("gul",data,max_process_id,True)

	print ""
	# Sleep to let kats initialize
	if il_anykats == True or  gul_anykats == True: print "sleep 2"

	print ""
	print "# --- Do insured loss computes ---"
	print ""
	if il_output: 	do_il(data,max_process_id)

	print ""
	print "# --- Do ground up loss  computes ---"
	print ""
	if gul_output:	do_gul(data,max_process_id)

	
	print ""

	for process_id in range (1, max_process_id+1):
		if gul_output == True and il_output == True:
			print "eve {3} {4} | getmodel | gulcalc -S{0}  -L{1}  {2} -c fifo/gul_P{3} -i - | fmcalc > fifo/il_P{3}  &".format(number_of_samples,gul_threshold, use_random_number_file,process_id,max_process_id)
			pass
		else:
			#  Now the mainprocessing
			if gul_output:
				if "gul_summaries" in data["analysis_settings"]:
					for x in data["analysis_settings"]["gul_summaries"]:						
						print "eve {3} {4} | getmodel | gulcalc -S{0}  -L{1}  {2}  -c - > fifo/gul_P{3}  &".format(number_of_samples,gul_threshold, use_random_number_file,process_id,max_process_id)

			if il_output:
				if "il_summaries" in data["analysis_settings"]:
					for x in data["analysis_settings"]["il_summaries"]:						
						print "eve {3} {4}  | getmodel | gulcalc -S{0}  -L{1}  {2} -i - | fmcalc > fifo/il_P{3} &".format(number_of_samples,gul_threshold, use_random_number_file,process_id,max_process_id)


	print ""

	do_pwaits()

	print ""
	do_post_wait_processing("il",data)
	do_post_wait_processing("gul",data)

	do_awaits()	# waits for aalcalc
	do_lwaits()	# waits for leccalc


	if gul_output:	
		do_gul_remove_fifo(data,max_process_id)
		remove_workfolders("gul",data)

	print ""

	if il_output: 	
		do_il_remove_fifo(data,max_process_id)
		remove_workfolders("il",data)


# for i in data:
	# print i

# pprint(data)

# print json.dumps(data,sort_keys=False, indent=4, separators=(',', ': '))

if __name__ == "__main__":
	genbash(1,'something.json')