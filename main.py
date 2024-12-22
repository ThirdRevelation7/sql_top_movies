from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float, desc, asc
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import requests
import json


# json config/sensitive data variables
def load_config():
    with open("config.json") as f:
        config = json.load(f)
    return config


config = load_config()
DATABASE_URI = config["database_uri"]
DATABASE_KEY = config["secret_key"]

MOVIE_DB_API_KEY = config["moviedb_api_key"]
MOVIE_DB_SEARCH_URL = config["movie_db_search_url"]
MOVIE_DETAILS_URL = config["movie_db_details_url"]
MOVIE_DB_IMG_URL = config["movie_db_img_url"]


# Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = DATABASE_KEY
Bootstrap5(app)


# CREATE DB
class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
db.init_app(app)

# CREATE TABLE


class Movie(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(250), nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    ranking: Mapped[int] = mapped_column(Integer, nullable=True)
    review: Mapped[str] = mapped_column(String(250), nullable=True)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)


# Commented out after creating database and table
# with app.app_context():
#     db.create_all()

class UpdateMovieForm(FlaskForm):
    rating = StringField(label="Your Rating out of 10 e.g. 7.5")
    review = StringField(label="What did you think of the movie?")
    submit = SubmitField(label="Update")


class FindMovieForm(FlaskForm):
    title = StringField(label="Movie Title", validators=[DataRequired()])
    submit = SubmitField(label="Find Movie")


@app.route("/")
def home():
    result = db.session.execute(db.select(Movie).order_by(asc(Movie.rating)))
    all_movies = result.scalars().all()

    for i in range(len(all_movies)):
        all_movies[i].ranking = len(all_movies) - i
    db.session.commit()

    return render_template("index.html", movies=all_movies)


@app.route("/add", methods=["GET", "POST"])
def add_movie():
    form = FindMovieForm()
    if form.validate_on_submit():
        movie_title = form.title.data
        response = requests.get(url=MOVIE_DB_SEARCH_URL, params={
            "api_key": MOVIE_DB_API_KEY,
            "query": movie_title
        })
        data = response.json()["results"]
        return render_template("select.html", options=data)
    return render_template("add.html", form=form)

@app.route("/find")
def find_movie():
    movie_api_id = request.args.get("id")
    if movie_api_id:
        movie_api_url = f"{MOVIE_DETAILS_URL}/{movie_api_id}"
        response = requests.get(url=movie_api_url, params={
            "api_key": MOVIE_DB_API_KEY,
            "language": "en-US"
        })
        data = response.json()
        new_movie = Movie(
            title=data["title"],
            year=data["release_date"].split("-")[0],
            img_url=f"{MOVIE_DB_IMG_URL}{data['poster_path']}",
            description=data["overview"]
        )
        db.session.add(new_movie)
        db.session.commit()
        return redirect(url_for('edit', id=new_movie.id))



@app.route("/edit", methods=["GET", "POST"])
def edit():
    form = UpdateMovieForm()
    movie_id = request.args.get("id")
    movie = db.get_or_404(Movie, movie_id)
    if form.validate_on_submit():
        movie.rating = float(form.rating.data)
        movie.review = form.review.data
        db.session.commit()
        return redirect(url_for('home'))
    return render_template("edit.html", form=form, movie=movie)


@app.route("/<movie_id>")
def delete(movie_id):
    movie = db.get_or_404(Movie, movie_id)
    db.session.delete(movie)
    db.session.commit()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
