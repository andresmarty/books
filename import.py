import os
import csv


from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    f = open("books.csv")
    reader = csv.reader(f)
    for isbn, title, author, year in reader:
        if year=="year":
            print ('skipped first line')
        else:
            db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:a, :b, :c, :d)", {"a":isbn, "b":title, "c":author, "d": year})
            print(f'added {title} to database') 
    db.commit()

if __name__ == "__main__":
    main()