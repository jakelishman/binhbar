#!/bin/bash

if [[ -z $1 ]]; then
    echo "Missing argument: storage directory." >&2
    exit 1
fi

directory="$1"

if [[ -d $directory ]]; then
    echo "Directory already exists: '$directory'." >&2
    exit 2
fi

mkdir -p "$directory"
cd "$directory" || exit 4

IFS='' read -r -p "Title: " title
if [[ -z $title ]]; then
    exit 8
fi

id=$(date -Ins | sha256sum | head -c6)

cat >"__article__.py" <<INFO_END
{
    "id": "$id",
    "title": "$title",
    "date": "$(date -I)",
    "tags": [],
}
INFO_END
touch "article.md"
