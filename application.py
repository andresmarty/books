import os
import json
import requests

from flask import Flask, session, render_template, request, url_for, abort, redirect, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True)
db = scoped_session(sessionmaker(bind=engine))


@app.route("/", methods=["GET", 'POST'])
def index():
    print(session.get("user"))
    if "user" in session:
        user = session.get("user")
        return render_template ("Home.html", user=user)
    return render_template("Login.html")

@app.route("/login", methods=['POST'])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    if (db.execute("SELECT * FROM users WHERE (username=:username) AND (password=:password)", {"username":username, "password":password,}).rowcount <=0):
        return render_template("Login.html", message="Wrong Username/Password")
    else:
        user = db.execute("SELECT * FROM users WHERE (username=:username)", {"username":username}).fetchone()
        session["user"] = user

    return render_template("Home.html", user=user)


@app.route("/user", methods=['POST'])
def registerUser():
    username = request.form.get("user")
    password = request.form.get("pass")
    password2 = request.form.get("pass2")

    if (password != password2):
        return  render_template("Registration.html", message="Wrong Password")
    
    if (db.execute("SELECT * FROM users WHERE (username=:user)", {"user":username,}). rowcount >= 1):
        return render_template("Registration.html", message="User already exists!")
    
    db.execute("INSERT INTO users (username, password) VALUES (:user,:pass)", {"user": username, "pass": password})
    db.commit()

    return render_template("Login.html")

@app.route("/registration", methods=['GET'])
def registration():
    return render_template ("Registration.html")


@app.route("/search", methods=['POST'])
def search():
    column = request.form.get("column").lower().strip()
    value = request.form.get("value").lower().strip()
    user = session.get("user")
    books = []  
    
    if(column == "author"): 
        books = db.execute("SELECT * FROM books WHERE (LOWER(author) LIKE :value)", {"value":f"%{value}%"}).fetchall()
    
    elif(column == "title"): 
        books = db.execute("SELECT * FROM books WHERE (LOWER(title) LIKE :value)", {"value":f"%{value}%"}).fetchall()
    
    elif(column == "isbn"): 
        books = db.execute("SELECT * FROM books WHERE (LOWER()isbn LIKE :value)", {"value":f"%{value}%"}).fetchall()

    else:
        return render_template("notfound.html")

    return render_template("results.html", books=books, user=user)

@app.route("/book/<string:book_id>")
def bookDetails(book_id):
    book = {}
    reviews = []
    user = session.get("user")

    book = db.execute("SELECT * FROM books WHERE id=:book_id", {"book_id":book_id}).fetchone()

    statisticsRes = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key":"uMK6Os6C9S7PLnQ7ts8AA", "isbns":[book.isbn]})
    if statisticsRes.status_code != 200:
        raise Exception("ERROR: API request unsuccesful.")

    statistics = statisticsRes.json()['books'][0]

    reviews = db.execute("SELECT username, review, rating FROM reviews r JOIN books b ON r.book_id = b.id JOIN users u ON r.user_id=u.id WHERE r.book_id=:book_id", {"book_id":book_id}).fetchall()

    return render_template("book.html", book=book, reviews=reviews, statistics=statistics, user=user)

@app.route("/review/<string:book_id>", methods=["POST"])
def review(book_id):
    rating = request.form.get('rating')
    review = request.form.get('review')
    user = session.get("user")
    user_id = user.id

    alreadyReviewed= db.execute("SELECT * FROM reviews where (book_id=:book_id) and (user_id=:user_id)", {"book_id": book_id, "user_id": user.id}).rowcount >= 1

    if not alreadyReviewed and user_id != None and (int(rating)>=1 and int(rating)<=5):
        db.execute("INSERT INTO reviews(user_id, book_id, review, rating) VALUES (:user_id,:book_id, :review,:rating)", {"user_id": user_id, "book_id": book_id, "review": review, "rating":rating})
        db.commit()
        return render_template("reviewed.html", success=True, user=user, book_id=book_id)
    else:
        return render_template("reviewed.html", success=False, book_id=book_id, user=user)

@app.route("/api/<string:isbn>")
def api(isbn):
    book = db.execute("SELECT title, author, year, isbn FROM books WHERE (isbn=:isbn)", {"isbn": isbn}).fetchone()
    reviewStats = db.execute("SELECT avg(rating), count(review) FROM reviews r JOIN books b ON r.book_id = b.id WHERE isbn=:isbn GROUP by book_id", {"isbn": isbn}).fetchone()
    if reviewStats == None:
        review_count=0
        average_score= None
    else:
        review_count = reviewStats[1]
        average_score = float(reviewStats[0])
    print(book)
    if book != None:
        res = {
                "title": book[0],
                "author": book[1],
                "year": book[2],
                "isbn": book[3],
                "review_count": review_count,
                "average_score": average_score
        }
        return json.dumps(res)
    else:
        return abort(404)


@app.route("/searchMore")
def searchMore():
    user = session.get("user")
    return render_template("Home.html", user=user)

@app.route("/logout")
def logout():
    session.pop("user", None)
    return render_template("Login.html")

