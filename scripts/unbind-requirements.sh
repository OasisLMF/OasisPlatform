#!/bin/bash

# Script to remove version constraints from all requirements .in files

set -e

# Enable debugging (uncomment next line if needed)
# set -x

# Define all requirements files (without .in extension for easier processing)
requirements_files=(
    "requirements-worker"
    "requirements-server"
    "requirements"
    "kubernetes/worker-controller/requirements"
)

# Function to unbind a single requirements file
unbind_requirements_file() {
    local base_name="$1"
    local in_file="${base_name}.in"
    local backup_file="${in_file}.unbound.backup"
    
    echo ""
    echo "========================================="
    echo "Unbinding: $in_file"
    echo "========================================="
    
    # Check if file exists
    if [ ! -f "$in_file" ]; then
        echo "Warning: $in_file not found - skipping"
        return 0
    fi
    
    # Create backup
    cp "$in_file" "$backup_file"
    echo "Created backup: $backup_file"
    
    # Process .in file
    echo "Removing version constraints from $in_file..."
    temp_file=$(mktemp)
    trap "rm -f $temp_file" RETURN
    
    local changes_made=0
    
    while IFS= read -r line; do
        # Keep empty lines and comments as-is
        if [[ -z "$line" ]] || [[ "$line" =~ ^[[:space:]]*# ]]; then
            echo "$line" >> "$temp_file"
            continue
        fi
        
        # Extract just the package name (remove all version constraints)
        # This handles formats like:
        # package>=1.0,<2.0
        # package==1.5.0
        # package~=1.0
        # package>=1.0
        # package
        if [[ "$line" =~ ^([a-zA-Z0-9_.-]+) ]]; then
            pkg_name="${BASH_REMATCH[1]}"
            
            # Check if this line had version constraints
            if [[ "$line" != "$pkg_name" ]]; then
                echo "$pkg_name" >> "$temp_file"
                echo "  Unbound: $line -> $pkg_name"
                ((changes_made++)) || true
            else
                # Line was already just a package name
                echo "$line" >> "$temp_file"
                echo "  Unchanged: $line"
            fi
        else
            # Keep any lines that don't match package pattern
            echo "$line" >> "$temp_file"
            echo "  Kept as-is: $line"
        fi
    done < "$in_file"
    
    # Replace original file with updated content
    mv "$temp_file" "$in_file"
    
    echo ""
    echo "Successfully unbound $in_file"
    echo "Preview of updated file:"
    echo "------------------------"
    head -10 "$in_file"
    
    echo ""
    echo "File summary:"
    echo "- Made $changes_made changes in $in_file"
    echo "- Removed all version constraints"
    echo "- Backup saved as: $backup_file"
    
    return 0
}

# Main execution
echo "Starting requirements files unbinding..."
echo "Files to process: ${requirements_files[*]}"

processed_count=0
failed_count=0

# Process each requirements file
for req_file in "${requirements_files[@]}"; do
    echo "About to unbind: $req_file"
    if unbind_requirements_file "$req_file"; then
        ((processed_count++)) || true
        echo "Successfully completed: $req_file"
    else
        ((failed_count++)) || true
        echo "Failed to process: $req_file"
    fi
    echo "Continuing to next file..."
done

# Final summary
echo ""
echo "========================================="
echo "FINAL SUMMARY"
echo "========================================="
echo "Successfully processed: $processed_count files"
echo "Failed/Skipped: $failed_count files"
echo ""

if [ $processed_count -gt 0 ]; then
    echo "All version constraints have been removed!"
    echo ""
    echo "Your .in files now contain only package names."
    echo "Next steps:"
    echo "----------"
    for req_file in "${requirements_files[@]}"; do
        if [ -f "${req_file}.in" ]; then
            echo "pip-compile ${req_file}.in  # Will get latest versions"
        fi
    done
    
    echo ""
    echo "Or run all at once to get latest versions:"
    pip_compile_commands=""
    for req_file in "${requirements_files[@]}"; do
        if [ -f "${req_file}.in" ]; then
            pip_compile_commands="$pip_compile_commands pip-compile ${req_file}.in &&"
        fi
    done
    # Remove the trailing &&
    pip_compile_commands=${pip_compile_commands%% &&}
    echo "$pip_compile_commands"
    
    echo ""
    echo "WARNING: This will install the LATEST versions of all packages!"
    echo "Make sure to test thoroughly after running pip-compile."
fi
