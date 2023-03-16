#!/bin/bash

tag_select='1'
major='\d+'
minor='\d+'

print_usage() {
      echo "find_latest.sh - Find release tags from repo"
      echo " "
      echo "find_latest.sh [options] application [arguments]"
      echo " "
      echo "options:"
      echo " --help                show brief help"
      echo " -j=<Major Verion>   "
      echo " -i=<Minor Version>  "
      exit 0
}

while getopts 'j:i:' flag; do
  case "${flag}" in
    j) major=${OPTARG} ;;
    i) minor=${OPTARG} ;;
    *) print_usage
       exit 1 ;;
  esac
done

release_tags=( $(git tag --sort=creatordate | grep -oP "^($major)\.($minor)\.(\d+)$") )
echo "${release_tags[-$tag_select]}"
