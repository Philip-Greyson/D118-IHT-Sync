
# D118-IHT-Sync

Script to take information about PE classes from PowerSchool, massage it into the IHT template, and upload it to their FTPS server.

## Overview

The script first takes the current date and does a query to find all terms from the *terms* table in PowerSchool for the high school, as that is the only building we are interested in. Then each term's start and end dates are compared to today's date to find the term that is currently active.
Once the term is found, a query is run for all the students at the high school to get their information, which is then processed individually.
A third query is run for each student, finding enrollments from the *cc* table that match the course numbers array defined in the top of the script. In our case, it is 6 PE classes. If there are courses that match, a final query is performed to retrieve the teacher information for that course.
Then all the information about the student, course section, and teacher of that section is printed out to a csv file formatted to align with IHT's template, and the file is closed.
Then a FTPS connection is established to the IHT server, the csv file is re-opened in binary mode and uploaded to the server, and the connection is closed.

## Requirements

The following Environment Variables must be set on the machine running the script:

- POWERSCHOOL_READ_USER
- POWERSCHOOL_DB_PASSWORD
- POWERSCHOOL_PROD_DB
- IHT_SFTP_USERNAME
- IHT_SFTP_PASSWORD
- IHT_SFTP_ADDRESS
- IHT_AUTH_TOKEN

These are fairly self explanatory, slightly more context is provided in the script comments.

Additionally,the following Python libraries must be installed on the host machine (links to the installation guide):

- [Python-oracledb](https://python-oracledb.readthedocs.io/en/latest/user_guide/installation.html)

## Customization

For customization or use outside of my specific use case at D118, you will want to edit the following variables:

- **If you are running on Windows** - you must change `strftime("%-m/%-d/%Y")` to `strftime("%#m/%#d/%Y")` in the birthday section as Windows does not have the same strftime [codes](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/strftime-wcsftime-strftime-l-wcsftime-l?view=msvc-170&redirectedfrom=MSDN).
- peCourseNumbers: An array that contains the "course numbers" (which are really strings as they can contain text) of the classes that should be included.
- `stuEmail =  str(idNum) +  "@d118.org"` - should be changed to however the student emails are formatted
- `WHERE schoolid = 5` in multiple SQL queries - This only selects one building in our district, and should be changed if other buildings should be included or at other districts
- `isyearrec = 0` in the term finding query - if you need to include terms that cover a whole year, this should be removed
