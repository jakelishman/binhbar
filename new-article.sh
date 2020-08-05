#!/bin/bash

original=$(realpath "$(dirname "$0")")

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


## Generate an ID and drop the metadata in the file.

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


## Update store file with the path to the new article.

cd "$original" || exit 16

store_file=".hbar-store"

if [[ ! -f "$store_file" ]]; then
    echo -e "{\n}" >"$store_file"
fi

cp "$store_file" "${store_file}_backup"

head -n-1 "$store_file" >"${store_file}_new"
echo "    '$id': '$directory'," >>"${store_file}_new"
echo "}" >>"${store_file}_new"
mv "${store_file}_new" "${store_file}"
