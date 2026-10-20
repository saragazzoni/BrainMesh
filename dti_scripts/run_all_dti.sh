#!/bin/bash
# =====================================================================================
# Lancia pipeline_dti.sh su tutti i pazienti elencati in una tabella (uno alla volta).
#
# Uso (dalla cartella in cui ci sono pipeline_dti.sh, dicomToNifti.sh e main.sh):
#     bash run_all_dti.sh pazienti_dti.csv               # tutti i pazienti della tabella
#     bash run_all_dti.sh pazienti_dti.csv paz3 paz5     # solo alcuni
#
# Tabella (CSV, separatore virgola, righe che iniziano con # ignorate):
#   paziente,exam_folder,exam_date,dti_series,basename,postop_folder,postop_date,postop_basename
#   paz3,Rm_10-7-18,,,,auto,,
#   paz5,Rm_2-3-19,2019-03-02,DTI_40_dir_B1500 DTI_64_dir_B3000,T1_3D_AX_mdc,postop_20-3-19,,T1_3D_AX_mdc
#
#   paziente         nome della cartella in PATIENTS_ROOT (obbligatorio)
#   exam_folder      cartella dell'esame preop con il DTI (obbligatorio)
#   exam_date        AAAA-MM-GG; vuoto = ricavata dal nome della cartella (es. Rm_10-7-18 -> 2018-07-10)
#   dti_series       serie DTI separate da spazi; vuoto = quelle di default di pipeline_dti.sh
#   basename         nome della T1 di riferimento dopo la conversione; vuoto = default (T1_3D_AX_mdc)
#   postop_folder    cartella dell'esame postop; "auto" = l'unica cartella postop* del paziente;
#                    vuoto = niente postop (solo preop)
#   postop_date      come exam_date, per il postop
#   postop_basename  nome della T1 postop dopo la conversione (la STESSA serie usata per la cavita');
#                    vuoto = default (T1_3D_AX_mdc)
#
# Le maschere vengono prese da RAIDIONICS_OUT: <paziente>/tumor_prob.nii.gz (preop) e
# <paziente>/postop/cavity_mask.nii.gz (postop); se mancano, la pipeline gira senza.
# Ogni paziente scrive il suo log in LOG_DIR; un paziente fallito non ferma gli altri.
# =====================================================================================

# ---------------- DA IMPOSTARE ----------------
PATIENTS_ROOT="/Users/saragazzoni/Desktop/Data/Pazienti"
RAIDIONICS_OUT="/Users/saragazzoni/Desktop/Data/raidionics_out"
LOG_DIR="${PATIENTS_ROOT}/log_dti"
SHOW_OUTPUT="${SHOW_OUTPUT:-0}"   # 1 = mostra anche a schermo tutti i messaggi della pipeline (oltre al log)
# ----------------------------------------------

CSV="$1"
if [ -z "$CSV" ] || [ ! -f "$CSV" ]; then
    echo "Uso: bash run_all_dti.sh pazienti_dti.csv [paziente ...]"
    exit 1
fi
CSV="$(cd "$(dirname "$CSV")" && pwd)/$(basename "$CSV")"
shift
SELECTED=" $* "

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1
for f in pipeline_dti.sh dicomToNifti.sh main.sh; do
    [ -f "$f" ] || { echo "[ERRORE] $f non trovato in $SCRIPT_DIR"; exit 1; }
done
mkdir -p "$LOG_DIR"

trim() { local s="$1"; s="${s//$'\r'/}"; s="${s#"${s%%[![:space:]]*}"}"; s="${s%"${s##*[![:space:]]}"}"; printf '%s' "$s"; }

# "Rm_10-7-18" / "postop_20-7-18" -> 2018-07-10 / 2018-07-20 (giorno-mese-anno nell'ultima parte dopo "_")
date_from_folder() {
    local tail="${1##*_}" d m y
    IFS=- read -r d m y <<< "$tail"
    [[ "$d" =~ ^[0-9]+$ && "$m" =~ ^[0-9]+$ && "$y" =~ ^[0-9]+$ ]] || return 1
    [ ${#y} -le 2 ] && y=$((2000 + 10#$y))
    printf "%04d-%02d-%02d" "$((10#$y))" "$((10#$m))" "$((10#$d))"
}

OK=(); FAILED=(); SKIPPED=()
START_ALL=$(date +%s)

while IFS=, read -r pz exam_folder exam_date dti_series t1_basename postop_folder postop_date postop_basename || [ -n "$pz" ]; do
    pz=$(trim "$pz")
    [ -z "$pz" ] && continue
    [[ "$pz" == \#* ]] && continue
    [ "$pz" = "paziente" ] && continue
    if [ "$SELECTED" != "  " ] && [[ "$SELECTED" != *" $pz "* ]]; then continue; fi

    exam_folder=$(trim "$exam_folder"); exam_date=$(trim "$exam_date"); dti_series=$(trim "$dti_series")
    t1_basename=$(trim "$t1_basename"); postop_folder=$(trim "$postop_folder"); postop_date=$(trim "$postop_date")
    postop_basename=$(trim "$postop_basename")

    echo "=================================================================="
    echo "[$(date '+%H:%M:%S')] $pz"
    patient_dir="${PATIENTS_ROOT}/${pz}"
    problem=""
    [ -d "$patient_dir" ] || problem="cartella $patient_dir non trovata"
    [ -z "$problem" ] && [ -z "$exam_folder" ] && problem="exam_folder vuoto nella tabella"
    if [ -z "$problem" ] && [ -z "$exam_date" ]; then
        exam_date=$(date_from_folder "$exam_folder") || problem="data preop non ricavabile da '$exam_folder': scrivila nella tabella"
    fi
    # servono i DICOM oppure le immagini gia' convertite (images/<data>)
    if [ -z "$problem" ] && [ ! -d "$patient_dir/$exam_folder" ] && [ ! -d "$patient_dir/images/$exam_date" ]; then
        problem="ne' DICOM ($exam_folder) ne' immagini convertite (images/$exam_date) per il preop"
    fi

    if [ -z "$problem" ] && [ "$postop_folder" = "auto" ]; then
        found=( "$patient_dir"/postop* )
        if [ ! -d "${found[0]}" ]; then
            echo "   nessuna cartella postop*: solo preop"
            postop_folder=""
        elif [ ${#found[@]} -gt 1 ]; then
            problem="piu' cartelle postop* in $patient_dir"
        else
            postop_folder="$(basename "${found[0]}")"
        fi
    fi
    if [ -z "$problem" ] && [ -n "$postop_folder" ]; then
        if [ -z "$postop_date" ]; then
            postop_date=$(date_from_folder "$postop_folder") || problem="data postop non ricavabile da '$postop_folder': scrivila nella tabella"
        fi
        if [ -z "$problem" ] && [ ! -d "$patient_dir/$postop_folder" ] && [ ! -d "$patient_dir/images_postop/$postop_date" ]; then
            problem="ne' DICOM ($postop_folder) ne' immagini convertite (images_postop/$postop_date) per il postop"
        fi
    fi
    if [ -n "$problem" ]; then
        echo "   SALTATO: $problem"
        SKIPPED+=("$pz ($problem)")
        continue
    fi

    tumor_mask="${RAIDIONICS_OUT}/${pz}/tumor_prob.nii.gz"
    cavity_mask="${RAIDIONICS_OUT}/${pz}/postop/cavity_mask.nii.gz"
    [ -f "$tumor_mask" ] || { echo "   [AVVISO] manca $tumor_mask: proiezione senza maschera del tumore"; tumor_mask=""; }
    if [ -n "$postop_folder" ] && [ ! -f "$cavity_mask" ]; then
        cavity_prob="${RAIDIONICS_OUT}/${pz}/postop/cavity_prob.nii.gz"
        if [ -f "$cavity_prob" ]; then
            echo "   [AVVISO] manca cavity_mask.nii.gz: uso cavity_prob.nii.gz (binarizzata a 0.5)."
            echo "            Controlla questo paziente: di solito la maschera manca se la cavita' non e' stata trovata."
            cavity_mask="$cavity_prob"
        else
            echo "   [AVVISO] manca $cavity_mask: proiezione senza maschera della cavita'"; cavity_mask=""
        fi
    fi
    [ -z "$postop_folder" ] && { cavity_mask=""; postop_date=""; }

    echo "   preop:  $exam_folder ($exam_date)"
    [ -n "$postop_folder" ] && echo "   postop: $postop_folder ($postop_date)"
    log="${LOG_DIR}/${pz}.log"
    echo "   log:    $log"

    t0=$(date +%s)
    PATH_TO_PATIENT="$patient_dir" \
    EXAM_FOLDER="$exam_folder" EXAM_DATE="$exam_date" \
    DTI_SERIES="$dti_series" BASENAME="$t1_basename" \
    POSTOP_EXAM_FOLDER="$postop_folder" POSTOP_EXAM_DATE="$postop_date" POSTOP_BASENAME="$postop_basename" \
    PREOP_TUMOR_MASK="$tumor_mask" POSTOP_CAVITY_MASK="$cavity_mask" \
        bash ./pipeline_dti.sh < /dev/null > >(if [ "$SHOW_OUTPUT" = "1" ]; then tee "$log"; else cat > "$log"; fi) 2>&1
    status=$?                                            # stdin chiuso: la pipeline non "mangia" le righe della tabella
    sleep 1                                              # lascia finire di scrivere il log
    t1=$(date +%s); minutes=$(( (t1 - t0) / 60 ))
    if [ $status -eq 0 ]; then
        echo "   OK ($minutes min)"
        OK+=("$pz")
    else
        echo "   FALLITO dopo $minutes min (codice $status). Ultime righe del log:"
        tail -n 5 "$log" | sed 's/^/      /'
        FAILED+=("$pz")
    fi
done < "$CSV"

echo "=================================================================="
END_ALL=$(date +%s)
TOTAL_MIN=$(( (END_ALL - START_ALL) / 60 ))
echo "Finito in ${TOTAL_MIN} min: ${#OK[@]} riusciti, ${#FAILED[@]} falliti, ${#SKIPPED[@]} saltati"
[ ${#FAILED[@]} -gt 0 ] && echo "Falliti: ${FAILED[*]}  (vedi i log in $LOG_DIR)"
for s in "${SKIPPED[@]}"; do echo "Saltato: $s"; done
