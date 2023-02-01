#!/bin/bash


branch_name=$(git rev-parse --abbrev-ref HEAD)
pre_release='false'
tag_select='1'
version_prefix=''

print_usage() {
      echo "find_release.sh - Find release tags from repo"
      echo " "
      echo "find_release.sh [options] application [arguments]"
      echo " "
      echo "options:"
      echo " --help               show brief help"
      echo " -b=<branch_name>     branch to search for tags"
      echo " -p=<true|false>      Ignore tags marked with '{n}.{n}.{n}rc{n}'"
      echo " -t=<int>             Select tag from most recent to least '1 = most recent by date'"
      echo " -v=<string>          Version tag prefix, e.g. ktools needs 'v' for tag format v{n}.{n}.{n}"
      exit 0
}

while getopts 'b:p:t:v:' flag; do
  case "${flag}" in
    b) branch_name=${OPTARG} ;;
    p) pre_release=${OPTARG} ;;
    t) tag_select=${OPTARG} ;;
    v) version_prefix=${OPTARG} ;;
    *) print_usage
       exit 1 ;;
  esac
done

if [[ "$pre_release" = "false" ]]; then
    release_tags=( $(git tag --merged $branch_name --sort=creatordate | grep -oP "^$version_prefix(\d+)\.(\d+)\.(\d+)$") )
else
    release_tags=( $(git tag --merged $branch_name --sort=creatordate | grep -oP "^$version_prefix(\d+)\.(\d+)\.(\d+)$|^(\d+)\.(\d+)\.(\d+)rc(\d+)|^(\d+)\.(\d+)\.(\d+)-dev") )
fi

# --  DEBUG inputs ----------
#echo "${release_tags[*]}"
#echo "path: "pwd
#echo "branch_name: "$branch_name
#echo "pre_release: "$pre_release
#echo "tag_select: "$tag_select

echo "${release_tags[-$tag_select]}"
