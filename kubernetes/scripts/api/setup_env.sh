#!/bin/bash

set -e

ACC_FILE=$1
LOC_FILE=$2

if [ -z "$LOC_FILE" ]; then
  echo "Usage: $0 <account-file> <location-file>"
  echo
  echo "For example: $0 ~/git/OasisPiWind/tests/inputs/SourceAccOEDPiWind.csv ~/git/OasisPiWind/tests/inputs/SourceLocOEDPiWind.csv"
  exit 0
fi

source $(dirname $0)/common.sh

PIWIND_VERSION=1
PIWIND_ID=$(curlf -X GET "${API_URL}/v1/models/" | jq ".[] | select((.supplier_id | ascii_downcase  == \"oasislmf\") and (.model_id | ascii_downcase == \"piwind\") and (.version_id == \"${PIWIND_VERSION}\")) | .id")
if [ -n "$PIWIND_ID" ]; then
  echo "Piwind found as model id $PIWIND_ID"
else
  echo "Piwind $PIWIND_VERSION not found, add the model"
  exit 1
fi

echo "Updating model chunking configuration..."
cat << EOF | curlf -X POST "${API_URL}/v1/models/${PIWIND_VERSION}/chunking_configuration/" -H "Content-Type: application/json" -d @- | jq .
{
  "strategy": "FIXED_CHUNKS",
  "dynamic_locations_per_lookup": 10000,
  "dynamic_events_per_analysis": 1,
  "fixed_analysis_chunks": 10,
  "fixed_lookup_chunks": 10
}
EOF

echo "Updating model scaling configuration..."
cat << EOF | curlf -X POST "${API_URL}/v1/models/${PIWIND_VERSION}/scaling_configuration/" -H "Content-Type: application/json" -d @- | jq .
{
  "scaling_strategy": "FIXED_WORKERS",
  "worker_count_fixed": 1,
  "worker_count_max": 4,
  "chunks_per_worker": 2
}
EOF


PORTFOLIO_ID=$(curlf -X GET "${API_URL}/v1/portfolios/" | jq '[.[] | select(.name == "P1")][0] | .id // empty')
if [ -n "$PORTFOLIO_ID" ]; then
  echo "Piwind portfolio found with id $PORTFOLIO_ID"
else
  echo "Create piwind portfolio"

  PORTFOLIO_ID=$(curlf -X POST "${API_URL}/v1/portfolios/" -H "Content-Type: application/json" -d '{"name": "P1"}' | jq .id)
  echo "Created portfolio with id $PORTFOLIO_ID"

fi

echo "Uploads account file..."
curlf -X POST "${API_URL}/v1/portfolios/${PORTFOLIO_ID}/accounts_file/" -H "Content-Type: multipart/form-data" -F "file=@${ACC_FILE};type=application/vnd.ms-excel"
echo

echo "Uploads location file..."
curlf -X POST "${API_URL}/v1/portfolios/${PORTFOLIO_ID}/location_file/" -H "Content-Type: multipart/form-data" -F "file=@${LOC_FILE};type=application/vnd.ms-excel"
echo

for ANAME_ID in $(seq 1 10); do

  ANALYSIS_NAME="A${ANAME_ID} - ${PIWIND_VERSION}"

  echo "Looking for $ANALYSIS_NAME"

  ANALYSIS_ID=$(curlf -X GET "${API_URL}/v1/analyses/?model=${PIWIND_ID}" | jq ".[] | select(.name ==  \"${ANALYSIS_NAME}\") | .id // empty")
  if [ -n "$ANALYSIS_ID" ]; then
    echo "Analysis exists with id $ANALYSIS_ID"
  else
    echo "Create analysis"

    ANALYSIS_ID=$(curlf -X POST "${API_URL}/v1/analyses/" -H "Content-Type: application/json" -d "{\"name\": \"${ANALYSIS_NAME}\", \"portfolio\": $PORTFOLIO_ID, \"model\": $PIWIND_ID}" | jq .id)
    echo "Created with id $ANALYSIS_ID"
  fi

  echo "Set priority"
  cat << EOF | curlf -X PATCH "${API_URL}/v1/analyses/${ANALYSIS_ID}/" -H "Content-Type: application/json" -d @- &> /dev/null
{
  "name": "${ANALYSIS_NAME}",
  "portfolio": $PORTFOLIO_ID,
  "model": $PIWIND_ID,
  "priority": $(($ANAME_ID - 0))
}
EOF

  echo "Updating analysis settings"

  cat << EOF | curlf -X POST "${API_URL}/v1/analyses/${ANALYSIS_ID}/settings/" -H "Content-Type: application/json" -d @-
{
  "full_correlation": false,
  "gul_output": true,
  "gul_summaries": [
    {
      "aalcalc": true,
      "eltcalc": false,
      "id": 1,
      "lec_output": true,
      "leccalc": {
        "full_uncertainty_aep": true,
        "full_uncertainty_oep": true,
        "return_period_file": true,
        "sample_mean_aep": false,
        "sample_mean_oep": false,
        "wheatsheaf_aep": false,
        "wheatsheaf_mean_aep": false,
        "wheatsheaf_mean_oep": false,
        "wheatsheaf_oep": false
      },
      "pltcalc": false,
      "summarycalc": false
    }
  ],
  "gul_threshold": 0,
  "il_output": true,
  "il_summaries": [
    {
      "aalcalc": true,
      "eltcalc": false,
      "id": 1,
      "lec_output": true,
      "leccalc": {
        "full_uncertainty_aep": true,
        "full_uncertainty_oep": true,
        "return_period_file": true,
        "sample_mean_aep": false,
        "sample_mean_oep": false,
        "wheatsheaf_aep": false,
        "wheatsheaf_mean_aep": false,
        "wheatsheaf_mean_oep": false,
        "wheatsheaf_oep": false
      },
      "pltcalc": false,
      "summarycalc": false
    }
  ],
  "model_settings": {
    "event_occurrence_id": "lt",
    "event_set": "p"
  },
  "module_supplier_id": "oasislmf",
  "model_supplier_id": "oasislmf",
  "model_name_id": "piwind",
  "model_version_id": "1",
  "number_of_samples": 8,
  "ri_output": false
}
EOF
  echo
done

echo "Done"
