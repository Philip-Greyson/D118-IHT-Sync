"""Script to send student PE course info to IHT via FTPS.

https://github.com/Philip-Greyson/D118-IHT-Sync

Does a few SQL queries to find the current active term in PS for the building desired,
then finds students in courses matching a specific list (PE courses). Outputs the student
and staff information for that course to an output file, then uploads it to IHT via FTPS.

Needs oracledb: pip install oracledb --upgrade
"""

# importing module
import datetime  # used to get current date for course info
import os  # needed to get environement variables
import sys
from datetime import *
from ftplib import *  # needed for the ftps upload

import oracledb  # used to connect to PowerSchool database
import pysftp  # used to connect to the IHT SFTP server and upload the file

un = os.environ.get('POWERSCHOOL_READ_USER')  # username for read-only database user
pw = os.environ.get('POWERSCHOOL_DB_PASSWORD')  # the password for the database account
cs = os.environ.get('POWERSCHOOL_PROD_DB')  # the IP address, port, and database name to connect to

#set up ftps login info, stored as environment variables on system
SFTP_UN = os.environ.get('IHT_SFTP_USERNAME')  # the username provided by IHT to log into the ftps server
SFTP_PW = os.environ.get('IHT_SFTP_PASSWORD')  # the password provided by IHT to log in using the username above
SFTP_HOST = os.environ.get('IHT_SFTP_ADDRESS')  # the URL/server IP provided by IHT
CNOPTS = pysftp.CnOpts(knownhosts='known_hosts')  # connection options to use the known_hosts file for key validation

auth = os.environ.get('IHT_AUTH_TOKEN')  # unique auth code provided by IHT to uniquely identify our districts files, students, etc
peCourseNumbers = ['800', '803', '804', '805', '806', '813', '814', '815', '816', '828', '829', '850']  # the course numbers in PowerSchool that should be included in the export. Stored as strings because course numbers can be text in PS. So dumb

OUTPUT_FILENAME = 'iht.csv'  # define the filename for the output file

print(f"Username: {un} |Password: {pw} |Server: {cs}")  # debug so we can see where oracle is trying to connect to/with
print(f"SFTP Username: {SFTP_UN} |SFTP Password: {SFTP_PW} |SFTP Server: {SFTP_HOST}")  # debug so we can see what SFTP info is trying to be used

if __name__ == '__main__':  # main file execution
    with oracledb.connect(user=un, password=pw, dsn=cs) as con:  # create the connecton to the database
        with con.cursor() as cur:  # start an entry cursor
            with open('IHTLog.txt', 'w') as log:
                with open(OUTPUT_FILENAME, 'w') as outputfile:
                    startTime = datetime.now()
                    startTime = startTime.strftime('%H:%M:%S')
                    print(f'INFO: Execution started at {startTime}')
                    print(f'INFO: Execution started at {startTime}', file=log)
                    print('auth token,system,facilitator,facilitator first name,facilitator last name,facilitator email,grade level,section,student id,last name,first name,email,secondary email,gender,height,weight,birthdate,rhr,max',file=outputfile)  # create the header row in the output file
                    today = datetime.now()  # get todays date and store it for finding the correct term later
                    # print("today = " + str(today))  # debug
                    # print("today = " + str(today), file=log)  # debug
                    termid = None
                    cur.execute("SELECT id, firstday, lastday, schoolid, dcid FROM terms WHERE schoolid = 5 AND isyearrec = 0 ORDER BY dcid DESC")  # get a list of terms for the school, filtering to not full years
                    terms = cur.fetchall()
                    for term in terms:  # go through every term
                        termStart = term[1]
                        termEnd = term[2]
                        #compare todays date to the start and end dates with 2 days before start so it populates before the first day of the term
                        if ((termStart - timedelta(days=2) < today) and (termEnd + timedelta(days=1) > today)):
                            termid = str(term[0])
                            termDCID = str(term[4])
                            print(f'INFO: Found good term: {termid} | {termDCID}')
                            print(f'INFO: Found good term: {termid} | {termDCID}', file=log)
                    # check to see if we found a valid term before we continue
                    if termid:
                        # select all students, only at the high school
                        cur.execute("SELECT student_number, first_name, last_name, id, enroll_status, dcid, gender, grade_level, dob FROM students WHERE schoolid = 5 ORDER BY student_number DESC")
                        students = cur.fetchall()
                        for student in students:
                            idNum = int(student[0])  # what we would refer to as their "ID Number" aka 6 digit number starting with 22xxxx or 21xxxx
                            stuEmail = str(idNum) + "@d118.org"  # "create" the email from their ID number
                            firstName = str(student[1])
                            lastName = str(student[2])
                            internalID = int(student[3])  # get the internal id of the student that is referenced in the classes entries
                            status = int(student[4])  # active on 0 , inactive 1 or 2, 3 for graduated
                            stuDCID = str(student[5])
                            gender = str(student[6])
                            grade = int(student[7])
                            birthday = student[8].strftime("%#m/%#d/%Y")  # convert datetime object into M/D/YYYY format
                            if status == 0:  # only process the active students, they shouldnt be enrolled anyways but we save some time not querying for their courses
                                try:
                                    cur.execute("SELECT course_number, sectionid, teacherid FROM cc WHERE studentid = :studentid AND termid = :term ORDER BY course_number", studentid=internalID, term=termid)  # using bind variables as best practice https://python-oracledb.readthedocs.io/en/latest/user_guide/bind.html#bind
                                    courses = cur.fetchall()
                                    for course in courses:
                                        courseNum = str(course[0])  # annoyingly, some course "numbers" are actually text
                                        # print(courseNum, file=log)
                                        if courseNum in peCourseNumbers:
                                            sectionID = str(course[1])
                                            teacherID = int(course[2])  # the teacher ID
                                            # print(f'Course Number: {courseNum} | Section ID {sectionID}', file=log)
                                            cur.execute("SELECT users.dcid, users.first_name, users.last_name, users.email_addr FROM schoolstaff LEFT JOIN users ON schoolstaff.users_dcid = users.dcid WHERE schoolstaff.id = :staffid", staffid=teacherID)
                                            teachers = cur.fetchall()  # there should really only be one row, so don't bother doing a loop and just take the first result
                                            staffDCID = int(teachers[0][0])
                                            staffFirst = str(teachers[0][1])
                                            staffLast = str(teachers[0][2])
                                            staffEmail = str(teachers[0][3])
                                            print(f'Student {idNum} --- Course Number: {courseNum} | Section ID {sectionID} --- Teacher: {staffFirst} {staffLast}, {staffEmail} - {staffDCID}')
                                            print(f'Student {idNum} --- Course Number: {courseNum} | Section ID {sectionID} --- Teacher: {staffFirst} {staffLast}, {staffEmail} - {staffDCID}', file=log)
                                            print(f'{auth},5,{staffDCID},{staffFirst},{staffLast},{staffEmail},{grade},{sectionID},{idNum},{lastName},{firstName},{stuEmail},,{gender},,,{birthday},,', file=outputfile)
                                except Exception as er:
                                    print(f'ERROR retrieving courses for student {idNum}: {er}')
                                    print(f'ERROR retrieving courses for student {idNum}: {er}', file=log)
                    else:  # if we did not find a valid term, just print out an error
                        print(f'WARN: Could not find a valid term for todays date of {today}, ending execution')
                        print(f'WARN: Could not find a valid term for todays date of {today}, ending execution', file=log)
                        sys.exit()
                # upload the file to the IHT server via SFTP
                try:
                    with pysftp.Connection(SFTP_HOST, username=SFTP_UN, password=SFTP_PW, cnopts=CNOPTS, port=880) as sftp:  # creates the sftp connection using the specified port, connection options
                        print(f'INFO: SFTP connection to {SFTP_HOST} established successfully')
                        print(f'INFO: SFTP connection to {SFTP_HOST} established successfully', file=log)
                        # print(sftp.pwd) # debug, show what folder we connected to/
                        # print(sftp.listdir())  # debug, show what other files/folders are in the current directory
                        sftp.put(OUTPUT_FILENAME, confirm=False)  # upload the first file onto the sftp server, confirm false because it gets ingested immediately and that causes its check to fail
                        print("INFO: Student file placed on remote server")
                        print("INFO: Student file placed on remote server", file=log)
                except Exception as er:
                    print(f'ERROR while connecting via SFTP to {SFTP_HOST} or putting file on server: {er}')
                    print(f'ERROR while connecting via SFTP to {SFTP_HOST} or putting file on server: {er}', file=log)

                endTime = datetime.now()
                endTime = endTime.strftime('%H:%M:%S')
                print(f'INFO: Execution ended at {endTime}')
                print(f'INFO: Execution ended at {endTime}', file=log)
