#!/bin/bash

# Script to update all requirements .in files with major version bounds based on their corresponding .txt files

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

# Function to process a single requirements file
process_requirements_file() {
    local base_name="$1"
    local in_file="${base_name}.in"
    local txt_file="${base_name}.txt"
    local backup_file="${in_file}.backup"
    
    echo ""
    echo "========================================="
    echo "Processing: $in_file"
    echo "========================================="
    
    # Check if files exist
    if [ ! -f "$in_file" ]; then
        echo "Warning: $in_file not found - skipping"
        return 0
    fi
    
    if [ ! -f "$txt_file" ]; then
        echo "Warning: $txt_file not found - skipping $in_file"
        return 0
    fi
    
    # Create backup
    cp "$in_file" "$backup_file"
    echo "Created backup: $backup_file"
    
    # Create temporary files to store package mappings (workaround for associative array issues)
    local temp_versions=$(mktemp)
    trap "rm -f $temp_versions" RETURN
    
    # Read versions from .txt file
    echo "Reading versions from $txt_file..."
    while IFS= read -r line; do
        # Skip empty lines and comments
        if [[ -z "$line" ]] || [[ "$line" =~ ^[[:space:]]*# ]]; then
            continue
        fi
        
        # Extract package name and version (handle various formats including extras)
        # First, check if line has == pattern
        if [[ "$line" =~ ^(.+)==([0-9]+\.[0-9]+[^[:space:]]*) ]]; then
            pkg_name="${BASH_REMATCH[1]}"
            full_version="${BASH_REMATCH[2]}"
            major_version=$(echo "$full_version" | cut -d'.' -f1)
            
            # Convert package name to lowercase for consistent matching (but preserve original case)
            pkg_name_lower=$(echo "$pkg_name" | tr '[:upper:]' '[:lower:]')
            
            # Store in temp file instead of associative array
            echo "$pkg_name_lower:$major_version" >> "$temp_versions"
            
            echo "  Found: $pkg_name -> $full_version (major: $major_version)"
        fi
    done < "$txt_file"
    
    # Process .in file
    echo "Updating $in_file..."
    temp_file=$(mktemp)
    trap "rm -f $temp_file" RETURN
    
    while IFS= read -r line; do
        # Keep empty lines and comments as-is
        if [[ -z "$line" ]] || [[ "$line" =~ ^[[:space:]]*# ]]; then
            echo "$line" >> "$temp_file"
            continue
        fi
        
        # Extract package name from the line (including extras like [azure])
        # Use a simpler approach that captures everything before version operators
        if [[ "$line" =~ ^([^><=!~[:space:]]+) ]]; then
            pkg_name="${BASH_REMATCH[1]}"
            pkg_name_lower=$(echo "$pkg_name" | tr '[:upper:]' '[:lower:]')
        else
            # Fallback: just take the whole line if no match
            pkg_name="$line"
            pkg_name_lower=$(echo "$pkg_name" | tr '[:upper:]' '[:lower:]')
        fi
        
        # Check if line already has version constraints
        if [[ "$line" == *">="* ]] || [[ "$line" == *"<="* ]] || [[ "$line" == *"=="* ]] || [[ "$line" == *"~="* ]] || [[ "$line" == *"!="* ]] || [[ "$line" == *">"* ]] || [[ "$line" == *"<"* ]]; then
            # Keep existing version constraints
            echo "$line" >> "$temp_file"
            echo "  Kept existing constraint: $line"
            continue
        fi
        
        # Look up version from temp file (escape special regex characters)
        escaped_pkg_name=$(echo "$pkg_name_lower" | sed 's/\[/\\[/g; s/\]/\\]/g')
        major_version=$(grep "^${escaped_pkg_name}:" "$temp_versions" 2>/dev/null | cut -d':' -f2 || true)
        
        # Check if we have version info for this package
        if [[ -n "$major_version" ]]; then
            next_major=$((major_version + 1))
            
            # Create new line with major version bounds
            new_line="${pkg_name}>=${major_version}.0,<${next_major}.0"
            echo "$new_line" >> "$temp_file"
            echo "  Added constraint: $line -> $new_line"
        else
            # Keep original line if no version found
            echo "$line" >> "$temp_file"
            echo "  Kept unchanged: $line (no version found in $txt_file)"
        fi
    done < "$in_file"
    
    # Replace original file with updated content
    mv "$temp_file" "$in_file"
    
    echo ""
    echo "Successfully updated $in_file"
    echo "Preview of updated file:"
    echo "------------------------"
    head -10 "$in_file"
    
    # Count processed packages
    local package_count=$(wc -l < "$temp_versions" 2>/dev/null || echo "0")
    
    echo ""
    echo "File summary:"
    echo "- Processed $package_count packages from $txt_file"
    echo "- Updated $in_file with major version bounds"
    echo "- Backup saved as: $backup_file"
    
    return 0
}

# Main execution
echo "Starting requirements files update..."
echo "Files to process: ${requirements_files[*]}"

processed_count=0
failed_count=0

# Process each requirements file
for req_file in "${requirements_files[@]}"; do
    echo "About to process: $req_file"
    if process_requirements_file "$req_file"; then
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
    echo "Next steps:"
    echo "----------"
    for req_file in "${requirements_files[@]}"; do
        if [ -f "${req_file}.in" ]; then
            echo "pip-compile --upgrade ${req_file}.in"
        fi
    done
    
    echo ""
    echo "Or run all at once:"
    pip_compile_commands=""
    for req_file in "${requirements_files[@]}"; do
        if [ -f "${req_file}.in" ]; then
            pip_compile_commands="$pip_compile_commands pip-compile --upgrade ${req_file}.in &&"
        fi
    done
    # Remove the trailing &&
    pip_compile_commands=${pip_compile_commands%% &&}
    echo "$pip_compile_commands"
fi
