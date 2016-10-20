#/bin/bash

#
# lookup_ids.sh [oasis_location_level_elt] [flamingo_item_dict]
#
# Does a reverse looup to produce an ELT with the source location IDs
#

echo 'event_id,type,location_desc,mean'
join -t , -1 1 -2 1 <(csvgrep -c mean -i -r "^0" $1 | grep -v Summary_id elt.csv | cut -d , -f 1,2,3,4 | sort -t , -k 1,1n) <(grep -v item_id $2 | cut -d , -f 4,5 | uniq | sort -t , -k 1,1n) | sort -t , -k 3n,3 -k 5n,5 | sed -e 's/^\([^,]*\),\([^,]*\),\([^,]*\),\([^,]*\),\([^,]*\)$/\3,\2,\5,\4/'
