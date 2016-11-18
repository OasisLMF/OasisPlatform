#!/usr/bin/python

from  kparse import *
import getopt

def usage():
	print "-a analysis settings"
	print "-p No of Processors"

def main(argv):
	processor_count=1
	analysis_filename=""
	try:
		opts, args = getopt.getopt(argv, "p:a:", ["help", "grammar="])

	except getopt.GetoptError:
		usage()
		sys.exit()
	# 
	for opt, arg in opts:
		if opt in ("-p"):
			processor_count=int(arg)						
		elif opt in ("-a"):
			analysis_filename = arg

	genbash(processor_count,analysis_filename)

if __name__ == "__main__":
    main(sys.argv[1:])