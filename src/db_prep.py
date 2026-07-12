#
# create tables for the first time. Thereafter not required to run this again.
#
from tqdm.auto import tqdm
from dotenv import load_dotenv

from db import init_db
load_dotenv()

if __name__ == "__main__":
    print("Initializing database...")
    init_db()

    