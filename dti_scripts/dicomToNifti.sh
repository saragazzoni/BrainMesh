#!/bin/bash

# rootdir=$1
# imagedir=${rootdir}/images
# rm -fr $imagedir
# mkdir $imagedir
# sep=$2

# function has_space {
#   [[ "$1" != "${1%[[:space:]]*}" ]] && return 0 || return 1
# }

# for folder in ${rootdir}/*; do
# 	if has_space "$folder" ; then
# 		dirnew="${folder// /_}"
# 		mv "$folder" "$dirnew"
# 	fi
# done

# for f in ${rootdir}/*; do
# 	echo $f
# 	date=`echo $f | rev | cut -d'_' -f 1 | rev`
# 	day=`echo $date | cut -d${sep} -f1`
# 	day=`printf "%02d\n" $day`
# 	month=`echo $date | cut -d${sep} -f2`
# 	month=`printf "%02d\n" $month`
# 	year="20`echo $date | cut -d${sep} -f3`"
# 	date="$year-$month-$day"
# 	newdir="${imagedir}/${date}"
# 	echo $newdir
# 	rm -fr $newdir
# 	mkdir $newdir
#   dcm2niix -z y -9 -f '%p' -o $newdir $f
# done


#!/bin/bash

# =======================================================
# dicomToNifti.sh (versione modificata)
# Converte una specifica sottocartella DICOM in NIfTI
# =======================================================

# Controllo argomenti
if [ "$#" -lt 3 ]; then
  echo "Uso: $0 pathToPatient examFolder separationTag"
  echo "Esempio: $0 /path/to/patient 2025_10_10 _"
  exit 1
fi

rootdir=$1          # cartella del paziente
examdir=$2          # nome della sottocartella dell’esame
sep=$3              # separatore per la data
imagedir="${rootdir}/images"

# Reset cartella immagini
rm -fr "$imagedir"
mkdir -p "$imagedir"

# Funzione per controllare se ci sono spazi
function has_space {
  [[ "$1" != "${1%[[:space:]]*}" ]] && return 0 || return 1
}

# Rinomina eventuali cartelle con spazi
for folder in "${rootdir}"/*; do
	if has_space "$folder" ; then
		dirnew="${folder// /_}"
		mv "$folder" "$dirnew"
	fi
done

# Percorso completo dell’esame da processare
f="${rootdir}/${examdir}"
if [ ! -d "$f" ]; then
  echo "[ERRORE] La cartella dell’esame non esiste: $f"
  exit 1
fi

echo "Processo: $f"

# Estrai la data dal nome della cartella
date=$(echo "$examdir" | rev | cut -d'_' -f 1 | rev)
day=$(echo "$date" | cut -d${sep} -f1)
day=$(printf "%02d\n" $day)
month=$(echo "$date" | cut -d${sep} -f2)
month=$(printf "%02d\n" $month)
year="20$(echo "$date" | cut -d${sep} -f3)"
date="${year}-${month}-${day}"

echo "Exam dir: $examdir"
echo "Data estratta: $date"


newdir="${imagedir}/${date}"
echo "Cartella di output: $newdir"

rm -fr "$newdir"
mkdir "$newdir"

# Conversione DICOM → NIfTI
dcm2niix -z y -9 -f '%p' -o "$newdir" "$f"
