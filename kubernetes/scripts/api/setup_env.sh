#!/bin/bash

set -e

OASIS_USER=$1
OASIS_PASSWORD=$2
ACC_FILE=$3
LOC_FILE=$4

if [ -z "$LOC_FILE" ]; then
  echo "Usage: $0 <oasisuser> <password> <account-file> <location-file>"
  exit 0
fi

source $(dirname $0)/common.sh

PIWIND_VERSION=1

PIWIND_ID=$(curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" -X GET "${BASE_URL}/v1/models/" | jq ".[] | select((.supplier_id | ascii_downcase  == \"oasislmf\") and (.model_id | ascii_downcase == \"piwind\") and (.version_id == \"${PIWIND_VERSION}\")) | .id")
if [ -n "$PIWIND_ID" ]; then
  echo "Piwind found as model id $PIWIND_ID"
else
  echo "Piwind $PIWIND_VERSION not found, add the model"
exit 1
  echo "Create piwind model"

  PIWIND_ID=$(curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" -X POST "${BASE_URL}/v1/models/" -H "Content-Type: application/json" -d "{\"supplier_id\": \"OasisLMF\",\"model_id\": \"PiWind\",\"version_id\": \"${PIWIND_VERSION}\""} | jq .id)
  echo "Created with id $PIWIND_ID"

  TF=$(tempfile)
  cat << EOF > $TF
{
  "data_settings": {
    "group_fields": [
      "PortNumber",
      "AccNumber",
      "LocNumber"
    ]
  },
  "lookup_settings": {
    "supported_perils": [
      {
        "desc": "Single Peril: Storm Surge",
        "id": "WSS"
      },
      {
        "desc": "Single Peril: Tropical Cyclone",
        "id": "WTC"
      },
      {
        "desc": "Group Peril: Windstorm with storm surge",
        "id": "WW1"
      },
      {
        "desc": "Group Peril: Windstorm w/o storm surge",
        "id": "WW2"
      }
    ]
  },
  "model_settings": {
    "event_occurrence_id": {
      "default": "lt",
      "desc": "PiWind Occurrence selection",
      "name": "Occurrence Set",
      "options": [
        {
          "desc": "Long Term",
          "id": "lt"
        }
      ]
    },
    "event_set": {
      "default": "p",
      "desc": "Piwind Event Set selection",
      "name": "Event Set",
      "options": [
        {
          "desc": "Probabilistic",
          "id": "p"
        }
      ]
    }
  }
}
EOF

  curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" -X POST "${BASE_URL}/v1/models/${PIWIND_ID}/settings/" -H "Content-Type: application/json" -d @${TF}

  rm $TF
fi

PORTFOLIO_ID=$(curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" -X GET "${BASE_URL}/v1/portfolios/" | jq '[.[] | select(.name == "P1")][0] | .id // empty')
if [ -n "$PORTFOLIO_ID" ]; then
  echo "Piwind portfolio found with id $PORTFOLIO_ID"
else
  echo "Create piwind portfolio"

  PORTFOLIO_ID=$(curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" -X POST "${BASE_URL}/v1/portfolios/" -H "Content-Type: application/json" -d '{"name": "P1"}' | jq .id)
  echo "Created with id $PORTFOLIO_ID"

  curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" -X POST "${BASE_URL}/v1/portfolios/${PORTFOLIO_ID}/accounts_file/" -H "Content-Type: multipart/form-data" -F "file=@${ACC_FILE};type=application/vnd.ms-excel"
  curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" -X POST "${BASE_URL}/v1/portfolios/${PORTFOLIO_ID}/location_file/" -H "Content-Type: multipart/form-data" -F "file=@${LOC_FILE};type=application/vnd.ms-excel"

fi

ANALYSIS_ID=$(curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" -X GET "${BASE_URL}/v1/analyses/?model=${PIWIND_ID}" | jq '.[0] | .id // empty')
if [ -n "$ANALYSIS_ID" ]; then
  echo "Analysis exists with id $ANALYSIS_ID"
else
  echo "Create analysis"
  ANALYSIS_ID=$(curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" -X POST "${BASE_URL}/v1/analyses/" -H "Content-Type: application/json" -d "{\"name\": \"A1 - ${PIWIND_VERSION}\", \"portfolio\": $PORTFOLIO_ID, \"model\": $PIWIND_ID}" | jq .id)
  echo "Created with id $ANALYSIS_ID"

  TF=$(tempfile)
  cat << EOF > $TF
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
  "model_version_id": "piwind",
  "module_supplier_id": "oasislmf",
  "number_of_samples": 8,
  "ri_output": false
}
EOF

  curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" -X POST "${BASE_URL}/v1/analyses/${ANALYSIS_ID}/settings/" -H "Content-Type: application/json" -d @${TF}

  rm $TF

fi

echo "End"
