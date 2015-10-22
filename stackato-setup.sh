#!/bin/bash
#echo "This scripts does Stackato setup related to filesystem."
FS=$STACKATO_FILESYSTEM

echo "Migrating data to shared filesystem..."
pwd
ls -al
ls -al $FS
mkdir -p $FS/static
cp -r static/* $FS/static

echo "Symlink to folders in shared filesystem..."
rm -fr static
ln -s $FS/static static

echo "All Done!"
