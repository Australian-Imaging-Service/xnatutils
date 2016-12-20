# Bash script for manually importing a dicom session into XNAT using dcmsend

if [ "$#" -ne 4 ]; then
    echo "Incorrect number of arguments, expects 'dirname', 'project', 'subject' and 'session'"
    exit
fi

dir=$1
project=$2
subject=$3
session=$4

find "$dir" -name "*.dcm" -exec dcmodify -i "(0010,4000)=project: $project; subject: ${project}_$subject; session: ${project}_${subject}_$session" {} \; -exec dcmsend -aet DARISIMPORT -aec XNAT localhost 8104 {} \;
