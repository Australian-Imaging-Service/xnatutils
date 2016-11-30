# Bash script for manually importing a dicom session into XNAT using dcmsend

if [ "$#" -ne 4 ]; then
    echo "Incorrect number of arguments, expects 'dirname', 'project', 'subject' and 'session'"
    exit
fi

session_dir=$1
project=$2
subject=$3
session=$4

for scan_dir in `ls $session_dir`; do 
    scan_path=$session_dir/$scan_dir
    if [ -d $scan_path ]; then
        dcmodify -i "(0010,4000)=project: $project; subject: ${project}_$subject; session: ${project}_${subject}_$session" "$scan_path"/*.dcm
        dcmsend -aet DARISIMPORT -aec XNAT localhost 8104 "$scan_path"/*.dcm
    fi
done
