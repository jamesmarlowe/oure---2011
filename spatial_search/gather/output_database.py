#
## gather.py
## screen scrape yellow pages for data to store
#

from models import *
from excel import *

def output_database_to_excel():
    results = Building.objects.all()
    writeToFile(results,'Listings')
    return "Success writing to file"

#handles running the file from the python shell
if __name__ == '__main__':
    output_database_to_excel()
    