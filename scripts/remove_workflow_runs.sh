#!/bin/bash

OWNER=OasisLMF
REPO=OasisPlatform
BRANCH=hotfix/ghactions



workflows_list=( $(gh api -X GET /repos/$OWNER/$REPO/actions/workflows | jq '.workflows[] | .id') ) 
for wf in "${workflows_list[@]}"; do 
    WORKFLOW_ID=$wf
    echo " -- Workflow --"
    echo 
    gh api -X GET /repos/$OWNER/$REPO/actions/workflows/$WORKFLOW_ID | jq '. | .name,.id'

    if [ -z $BRANCH ]; then 
        echo 'Delete ALL runs'
        echo '----------------'
        FIRST=$(gh api -X GET /repos/$OWNER/$REPO/actions/workflows/$WORKFLOW_ID/runs | jq ' first( .workflow_runs[] | .id )')
        while [ ! -z "$FIRST" ]; do 
            # PRINT LIST
            gh api -X GET /repos/$OWNER/$REPO/actions/workflows/$WORKFLOW_ID/runs | jq ' .workflow_runs[] | "\(.id)   \(.display_title)" '
            # DEL 
            gh api -X GET /repos/$OWNER/$REPO/actions/workflows/$WORKFLOW_ID/runs | jq '.workflow_runs[] | .id' | xargs -I{} gh api -X DELETE /repos/$OWNER/$REPO/actions/runs/{}
            # CHECK EMPTY 
            FIRST=$(gh api -X GET /repos/$OWNER/$REPO/actions/workflows/$WORKFLOW_ID/runs | jq ' first( .workflow_runs[] | .id )')
        done    
        echo '----------------\n'
    else
        echo "Delete runs from branch ($BRANCH)"
        echo '----------------'
        FIRST=$(gh api -X GET /repos/$OWNER/$REPO/actions/workflows/$WORKFLOW_ID/runs | jq 'first( .workflow_runs[] | select(.head_branch | contains("'$BRANCH'")) | "\(.id)   \(.display_title)" )')
        while [ ! -z "$FIRST" ]; do 
            # PRINT LIST
            gh api -X GET /repos/$OWNER/$REPO/actions/workflows/$WORKFLOW_ID/runs | jq ' .workflow_runs[] | select(.head_branch | contains("'$BRANCH'")) | "\(.id)   \(.display_title)" '
            # DEL
            gh api -X GET /repos/$OWNER/$REPO/actions/workflows/$WORKFLOW_ID/runs | jq '.workflow_runs[] | select(.head_branch | contains("'$BRANCH'")) | .id' | xargs -I{} gh api -X DELETE /repos/$OWNER/$REPO/actions/runs/{}
            # CHECK EMPTY
            FIRST=$(gh api -X GET /repos/$OWNER/$REPO/actions/workflows/$WORKFLOW_ID/runs | jq 'first( .workflow_runs[] | select(.head_branch | contains("'$BRANCH'")) | "\(.id)   \(.display_title)" )')
        done    
        echo '----------------\n'
    fi     
done 
