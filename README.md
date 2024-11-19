# journaling-fs-project

aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa

it actually works now

## but how?

basically, we use pyinotify to watch the `watched` directory for creation/deletion/modification of text files. when a file is created, we create a Universally Unique Identifier (UUID) and assign it to a journal for that file. when a file is deleted we mark its journal as closed (by setting a `dtime`, for "deletion time").

when a file is modified, we use google's diff-match-patch library (which was originally created for Google Docs, fun fact) to make a patch that will turn the old content into the new content. we store that patch in the database associated to the requisite journal and with an mtime.

when we want to eliminate an old revision to make room for another, we combine the first 2 patches into one. this works because the first patch in the journal always patches an empty string to the first known content of the file; by merging the two patches (specifically, applying them in order to an empty string, and then diffing it to an empty string), we ensure that "start from an empty string and apply consecutive patches until you get to the version of the file you want" is always a valid operation.
