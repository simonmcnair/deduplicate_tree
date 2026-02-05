#This runs rdfind on directories that match on both paths.  This is useful to deduplicate files after copying them from one place to another using RSYNC to verify they are identical.
#This will delete duplicates in each path too though
#I thould probably make it take a command line rather than hardcoding.  Maybe later.

A="/keep/media/tv/adults"
B="/dedupe/media/tv/adults"

for dir in "$A"/*; do
    name=$(basename "$dir")
    other="$B/$name"

    [ -d "$other" ] || continue

    echo "Processing $name"
    rdfind -deleteduplicates true "$dir" "$other"
done
