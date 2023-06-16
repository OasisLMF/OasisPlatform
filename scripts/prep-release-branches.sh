#!/bin/bash


# Regular expression pattern to match branches
regex="backports/1.*.x"

# Execute 'git branch' command and store the result
branches=$(git branch --format="%(refname:short)")

# Read the branches into a Bash array
branch_array=()
while IFS= read -r branch; do
  if [[ $branch =~ $regex ]]; then
    branch_array+=("$branch")
  fi
done <<< "$branches"


last_release() {
    branch_name=$1
    release_tags=( $(git tag --merged $branch_name --sort=creatordate | grep -oP "^$version_prefix(\d+)\.(\d+)\.(\d+)$") )
    echo ${release_tags[-1]}
}    



# Print the matching branches
for branch in "${branch_array[@]}"; do
    echo "Preparing release for $branch"
    
    git co $branch && git pull
    semver=$(last_release $branch)

    echo $semver
    regex="([0-9]+)\.([0-9]+)\.([0-9]+)"
    if [[ $semver =~ $regex ]]; then
      major="${BASH_REMATCH[1]}"
      minor="${BASH_REMATCH[2]}"
      patch="${BASH_REMATCH[3]}"
    else
      echo "Invalid semver format: $semver"
    fi

    patch=$((patch + 1))
    new_release="$major.$minor.$patch"
    new_branch="release/$new_release"
    echo "Create release for: $new_branch"
    
    
    if git branch "$new_branch"; then
        git push --set-upstream origin $new_branch
    fi

    git checkout $new_branch
    #gh pr create --base $branch

done
