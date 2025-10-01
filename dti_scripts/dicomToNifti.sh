#!/bin/bash

rootdir=$1
imagedir=${rootdir}/../images
rm -fr $imagedir
mkdir $imagedir
sep=$2

function has_space {
  [[ "$1" != "${1%[[:space:]]*}" ]] && return 0 || return 1
}

for folder in ${rootdir}/*; do
	if has_space "$folder" ; then
		dirnew="${folder// /_}"
		mv "$folder" "$dirnew"
	fi
done

for f in ${rootdir}/*; do
	echo $f
	date=`echo $f | rev | cut -d'_' -f 1 | rev`
	day=`echo $date | cut -d${sep} -f1`
	day=`printf "%02d\n" $day`
	month=`echo $date | cut -d${sep} -f2`
	month=`printf "%02d\n" $month`
	year="20`echo $date | cut -d${sep} -f3`"
	date="$year-$month-$day"
	newdir="${imagedir}/${date}"
	echo $newdir
	rm -fr $newdir
	mkdir $newdir
  dcm2niix -z y -9 -f '%p' -o $newdir $f
done
