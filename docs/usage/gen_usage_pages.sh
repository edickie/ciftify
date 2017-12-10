#!/bin/bash

# generates the usage pages by running help

all_scripts=$(ls ../../ciftify/bin/* | grep -v .py | grep -v '.conf')

for script in ${all_scripts}; do
  script_base=$(basename ${script})
  echo ${script} ${script_base}
  echo "# ${script_base}" > ${script_base}_1.md
  echo ''  >> ${script_base}_1.md
  ${script} --help >> ${script_base}_1.md
  sed 's/Usage:/## Usage \n```/g' ${script_base}_1.md > ${script_base}_2.md
  sed 's/DETAILS/\n```\n## DETAILS /g' ${script_base}_2.md > ${script_base}.md
done

rm *_1.md *_2.md

echo "Update navbar with the following text"
echo "- Usage"
for script in ${all_scripts}; do
  script_base=$(basename ${script})
  echo "  - [ ${script_base} ](usage/${script_base}.md)"
done
