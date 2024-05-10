# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import requests
from werkzeug.security import generate_password_hash, check_password_hash
import random

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Ska4404a@localhost/movie'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    searches = db.relationship('Search', back_populates='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Inside the Search class
class Search(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', back_populates='searches')

class RecommendedMovie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    movie_title = db.Column(db.String(255), nullable=False)

@app.route('/')
def index():
    return render_template('register.html')


@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']

    # Check if the username already exists
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        error_message = 'Username already exists. Please choose a different username.'
        return render_template('register.html', error=error_message)

    # Create a new user with the provided username and password
    new_user = User(username=username)
    new_user.set_password(password)

    # Add the new user to the database
    db.session.add(new_user)
    db.session.commit()

    # Redirect to the login page after successful registration
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'GET':
        # Handle GET request (e.g., display login form)
        return render_template('index.html')
    elif request.method == 'POST':
        username = request.form['username']
    password = request.form['password']

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        # Password is correct, proceed with the login
        return redirect(url_for('dashboard', username=username))
    else:
        error_message = 'Invalid username or password. Please check your credentials and try again.'
        return render_template('index.html', error=error_message)
    

@app.route('/search/<username>', methods=['POST'])
def search(username):
    user = User.query.filter_by(username=username).first()
    # query = request.form.get('query')
    if user:
        # Get the search query from the form data
        query = request.form['query']
        if query:
            remaining_movies = []
        # Create a new Search object and associate it with the user
            url = "https://imdb146.p.rapidapi.com/v1/find/"

            querystring = {"query":query}

            headers = {
	                 "X-RapidAPI-Key": "6fd4b0981fmshb830aa200fe03afp18fa14jsnd046d78cf350",
	                 "X-RapidAPI-Host": "imdb146.p.rapidapi.com"
                     }

            response = requests.get(url, headers=headers, params=querystring)
            if response.status_code == 200:
                current = response.json()
                # print(current)
                titles = [result['titleNameText'] for result in current['titleResults']['results'] if result['imageType'] == 'movie']
                query = titles[0]
                remaining_movies = titles[1:]

                for title in remaining_movies:
    # Check if the movie is already recommended to the user
                    existing_movie = RecommendedMovie.query.filter_by(user_id=user.id, movie_title=title).first()
    
                    if not existing_movie:
        # Movie is not already recommended, add it to the RecommendedMovie table
                        movie = RecommendedMovie(user_id=user.id, movie_title=title)
                        db.session.add(movie)

# Commit the changes to the database
                db.session.commit()

        
            url = f'http://www.omdbapi.com/?t={query}&apikey=6d04196a'
            response = requests.get(url)
            if response.status_code == 200:
                current_movie = []
                current_movie = response.json()
                user_queries = {search.query for search in user.searches}
                if query not in user_queries:
                    new_search = Search(query=query, user=user)
        # Add the new search to the database
                    db.session.add(new_search)
                    db.session.commit()
            else:
                current_movie=[]
                print('Movie not found', 'error')

            recommendations = get_recommendations(user)

            if len(current_movie) > 0:
                if len(remaining_movies) > 0:
                    for remaining_movie in remaining_movies:
                        recommendations.insert(0,remaining_movie)

            

        # Fetch movie information from OMDB for each recommendation
            

            like_movies = get_likely_movies(user)
            recommendations = recommendations + like_movies

            recommendations = list(set(recommendations))
            movies_info = []
            api_key = '6d04196a'  # Replace with your actual OMDB API key

            for title in recommendations:
                movie_info = get_movie_info(title, api_key)
                if movie_info:
                    movies_info.append(movie_info)

            trending = trending_movies()
            trending_movies_info = []
            for title in trending:
                trending_movie_info = get_movie_info(title, api_key)
                if trending_movie_info:
                    trending_movies_info.append(trending_movie_info)


            top_50 = top_movies()
            top_50_info = []
            for title in top_50:
                top_50_infoo = get_movie_info(title, api_key)
                if top_50_infoo:
                    top_50_info.append(top_50_infoo)


            return render_template('dashboard.html', user=user, movies_info=movies_info,current_movie=current_movie,top_50_info=top_50_info,trending_movies_info=trending_movies_info)
    else:
        print('User not found', 'error')

    # Redirect back to the dashboard
    return redirect(url_for('dashboard', username=username))        
    # Your search logic here




@app.route('/dashboard/<username>')
def dashboard(username):
    user = User.query.filter_by(username=username).first()
    if user:
        searches = user.searches  # Accessing searches through the user's relationship
        # print(searches)
        api_key = '6d04196a'
        if len(searches) > 0:
            recommendations = get_recommendations(user)
            movies_info = []
              # Replace with your actual OMDB API key

            like_movies = get_likely_movies(user)

            recommendations = recommendations + like_movies

            recommendations = list(set(recommendations))


            for title in recommendations:
                movie_info = get_movie_info(title, api_key)
                if movie_info:
                    movies_info.append(movie_info)

        
 
        trending = trending_movies()
        trending_movies_info = []
        for title in trending:
            trending_movie_info = get_movie_info(title, api_key)
            if trending_movie_info:
                trending_movies_info.append(trending_movie_info)


        top_50 = top_movies()
        top_50_info = []
        for title in top_50:
            top_50_infoo = get_movie_info(title, api_key)
            if top_50_infoo:
                top_50_info.append(top_50_infoo)


        if len(searches) > 0:    
            return render_template('dashboard.html', user=user,movies_info=movies_info,trending_movies_info=trending_movies_info,top_50_info=top_50_info)
        else:
            return render_template('dashboard.html', user=user,trending_movies_info=trending_movies_info,top_50_info=top_50_info)


    else:
        flash('User not found', 'error')
        return redirect(url_for('index'))

def get_recommendations(user):
    # Basic content-based filtering example (similarity based on search queries)
    other_users = User.query.filter(User.id != user.id).all()

    # Calculate user similarities (using Jaccard similarity as an example)
    user_similarities = {}
    for other_user in other_users:
        user_queries = {search.query for search in user.searches}
        other_user_queries = {search.query for search in other_user.searches}
        # print(user_queries)
        # print(other_user_queries)
        # print(user_queries.intersection(other_user_queries))
        # print(user_queries.union(other_user_queries))
        if len(user_queries.union(other_user_queries)) > 0:
            similarity = len(user_queries.intersection(other_user_queries)) / len(user_queries.union(other_user_queries))
        else:
            similarity = 0 
        
        user_similarities[other_user] = similarity

    # Sort users by similarity in descending order
    sorted_users = sorted(user_similarities.items(), key=lambda x: x[1], reverse=True)
    if not sorted_users:
        return []  # If there are no other users, return an empty list of recommendations
    # Get recommendations from the most similar user
    most_similar_user = sorted_users[0][0]
    recommendations = [search.query for search in most_similar_user.searches]
    recommendations = list(set(recommendations))
    recommendations =  list(filter(lambda x: x not in user_queries, recommendations))
    
    liked_genre_movies = get_genre(user)

    for liked_genre_movie in liked_genre_movies:
        recommendations.append(liked_genre_movie)

    # print(liked_genre_movies)
    
    trending_movie = trending_movies()
    random_trending_movies = random.sample(trending_movie, 5)

    for random_trending_movie in random_trending_movies:
        recommendations.append(random_trending_movie)

    recommendations = list(set(recommendations))
    print(recommendations)
    return recommendations


def get_genre(user):

    user_queries = {search.query for search in user.searches}
    user_queries = list(set(user_queries))
    genres = {}
    for user_query in user_queries:
        api_key = '6d04196a'
        movie_info = get_movie_info(user_query, api_key)
        if 'Genre' in movie_info:
            genre_list = movie_info['Genre'].split(', ')
            for genre in genre_list:
                if genre in genres:
                    genres[genre] =  genres[genre]+1
                else:
                    genres[genre] = 1  

    max_genre = max(genres, key=genres.get)
    sorted_genres = sorted(genres.items(), key=lambda x: x[1], reverse=True)
    second_liked_genre = sorted_genres[1][0] if len(sorted_genres) > 1 else ''
    print(max_genre)
    print(second_liked_genre)
    
    # url = "https://moviesdatabase.p.rapidapi.com/titles"

    # querystring = {"genre":max_genre,"startYear":"2022","titleType":"movie","sort":"year.incr","endYear":"2023","limit":"20"}

    # headers = {
	# "X-RapidAPI-Key": "6fd4b0981fmshb830aa200fe03afp18fa14jsnd046d78cf350",
	# "X-RapidAPI-Host": "moviesdatabase.p.rapidapi.com"
    # }

    # response = requests.get(url, headers=headers, params=querystring)
    url = "https://moviesverse1.p.rapidapi.com/get-by-genre"

    querystring = {"genre":max_genre.lower()}

    headers = {
	"X-RapidAPI-Key": "6fd4b0981fmshb830aa200fe03afp18fa14jsnd046d78cf350",
	"X-RapidAPI-Host": "moviesverse1.p.rapidapi.com"
    }

    response1 = requests.get(url, headers=headers, params=querystring)

    querystring = {"genre":second_liked_genre.lower()}

    response2 = requests.get(url, headers=headers, params=querystring)

    

    # print(response1.json())
    if response1.status_code == 200:
        movies = response1.json()
        # titles = [movie.get('titleText', {}).get('text', '') for movie in movies.get('results', [])]
        titles = [movie['title'] for movie in movies['movies']]
        # print(titles)
        random_10_titles_for_1 = random.sample(titles, 10)
        # return titles
    else:
        print(f"Error: {response1.status_code}")
        if response2.status_code == 200:
            movies = response2.json()
            # titles = [movie.get('titleText', {}).get('text', '') for movie in movies.get('results', [])]
            titles = [movie['title'] for movie in movies['movies']]
            # print(titles)
            random_10_titles_for_2 = random.sample(titles, 10)
            titles = random_10_titles_for_1
            return titles
        else:
            print(f"Error: {response2.status_code}")
            return None
        
    if response2.status_code == 200:
        movies = response2.json()
        # titles = [movie.get('titleText', {}).get('text', '') for movie in movies.get('results', [])]
        titles = [movie['title'] for movie in movies['movies']]
        # print(titles)
        random_10_titles_for_2 = random.sample(titles, 10)
        titles = random_10_titles_for_1 + random_10_titles_for_2
        return titles
    else:
        print(f"Error: {response2.status_code}")
        titles = random_10_titles_for_1
        return titles


    
def top_movies():
    url = "https://moviesverse1.p.rapidapi.com/top-250-movies"

    headers = {
	"X-RapidAPI-Key": "6fd4b0981fmshb830aa200fe03afp18fa14jsnd046d78cf350",
	"X-RapidAPI-Host": "moviesverse1.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers)
    top_movies = response.json()
    titles = [movie['title'] for movie in top_movies['movies']]
    first_50 = titles[:50]
    return first_50

def trending_movies():
    url = "https://movies-tv-shows-database.p.rapidapi.com/"

    querystring = {"page":"1"}

    headers = {
	"Type": "get-trending-movies",
	"X-RapidAPI-Key": "6fd4b0981fmshb830aa200fe03afp18fa14jsnd046d78cf350",
	"X-RapidAPI-Host": "movies-tv-shows-database.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)
    trending_movies = response.json()
    titles = [movie['title'] for movie in trending_movies["movie_results"]]
    # print(titles)
    return titles

def get_likely_movies(user):
    # user_queries = {search.query for search in user.searches}
    # user_queries = list(set(user_queries))
    like_movies = []
    # for user_query in user_queries:
    #     url = "https://imdb146.p.rapidapi.com/v1/find/"

    #     querystring = {"query":user_query}

    #     headers = {
	#                  "X-RapidAPI-Key": "6fd4b0981fmshb830aa200fe03afp18fa14jsnd046d78cf350",
	#                  "X-RapidAPI-Host": "imdb146.p.rapidapi.com"
    #                  }

    #     response = requests.get(url, headers=headers, params=querystring)
    #     if response.status_code == 200:
    #         current = response.json()
    #             # print(current)
    #         titles = [result['titleNameText'] for result in current['titleResults']['results'] if result['imageType'] == 'movie']
    #         like_movies = like_movies + titles[1:2]
    recommendations = RecommendedMovie.query.filter_by(user_id=user.id).all()
    like_movies = [recommendation.movie_title for recommendation in recommendations]
    user_searches = [search.query for search in user.searches]
    
    # Exclude user searches titles from like_movies
    like_movies = [title for title in like_movies if title not in user_searches]

    if len(like_movies) > 10:
        like_movies = random.sample(like_movies, 10)
# Get a random half of the list

    # print(like_movies)
    return like_movies
    



def get_movie_info(title, api_key):
    # Fetch movie information from OMDB API
    url = f'http://www.omdbapi.com/?t={title}&apikey={api_key}'
    response = requests.get(url)
    if response.status_code == 200:
        movie_info = response.json()
        return movie_info
    else:
        return None

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
