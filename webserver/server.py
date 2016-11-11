#!/usr/bin/env python2.7

"""
Columbia W4111 Intro to databases
Example webserver

To run locally

    python server.py

Go to http://localhost:8111 in your browser


A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, session, url_for, request, render_template, g, redirect, Response

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)


#
# The following uses the postgresql test.db -- you can use this for debugging purposes
# However for the project you will need to connect to your Part 2 database in order to use the
# data
#
# XXX: The URI should be in the format of: 
#
#     postgresql://USER:PASSWORD@<IP_OF_POSTGRE_SQL_SERVER>/postgres
#
# For example, if you had username ewu2493, password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://ewu2493:foobar@<IP_OF_POSTGRE_SQL_SERVER>/postgres"
#
# Swap out the URI below with the URI for the database created in part 2
DATABASEURI = "postgresql://qv2106:d642r@104.196.175.120/postgres"
#DATABASEURI = "sqlite:///test.db"


#
# This line creates a database engine that knows how to connect to the URI above
#
engine = create_engine(DATABASEURI)


#
# START SQLITE SETUP CODE
#
# after these statements run, you should see a file test.db in your webserver/ directory
# this is a sqlite database that you can query like psql typing in the shell command line:
# 
#     sqlite3 test.db
#
# The following sqlite3 commands may be useful:
# 
#     .tables               -- will list the tables in the database
#     .schema <tablename>   -- print CREATE TABLE statement for table
# 
# The setup code should be deleted once you switch to using the Part 2 postgresql database
#
#engine.execute("""DROP TABLE IF EXISTS test;""")
#engine.execute("""CREATE TABLE IF NOT EXISTS test (
#  id serial,
#  name text
#);""")
#engine.execute("""INSERT INTO test(name) VALUES ('grace hopper');""")
#engine.execute("""SELECT * FROM Subscription;""")
#
# END SQLITE SETUP CODE
#



@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request

  The variable g is globally accessible
  """
  try:
    g.conn = engine.connect()
  except:
    print "uh oh, problem connecting to database"
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass

#LOGIN VALIDATIONS
######################################
def is_valid_username(username):
    isAlphaNum = username.isalnum()
    print "username", username, " isalphanum:", isAlphaNum 
    return isAlphaNum 

def add_user(username, name, dob):
    cmd = 'INSERT INTO Users (uid, since, name, dob, username) VALUES(DEFAULT, now(), :name1, :dob1, :username1)'
    try:
        result = g.conn.execute(text(cmd), name1=name, dob1=dob, username1=username)
        print "result of insert", result
        #print result.is_insert
        #print result.inserted_primary_key
    except:
        print "exception while inserting ", username, name, dob
        return False
    return True

@app.route('/user/<username>/music', methods=["POST"])
def music(username):
    # Find uid
    cmd = "SELECT uid FROM users WHERE users.username=%s"
    cursor = g.conn.execute(cmd, username)
    result = cursor.first()
    uid = result[0]

    cursor = g.conn.execute("SELECT stagename FROM artist ORDER BY stagename LIMIT 10")
    artists = []
    for result in cursor:
        artists.append(result[0])  # can also be accessed using result[0]
    cursor.close()

    cursor = g.conn.execute("select song.title, count(song.songid) AS playCount from song, listen WHERE song.songid=listen.songid AND listen.time>(NOW()-interval '6 month') GROUP BY song.songid ORDER BY playCount DESC LIMIT 10")
    songs = []
    for result in cursor:
        songs.append(result[0])  # can also be accessed using result[0]
    cursor.close()

    cursor = g.conn.execute("(SELECT distinct(genre) FROM song ORDER BY GENRE LIMIT 5) UNION (SELECT distinct(genre) FROM album_release ORDER BY GENRE LIMIT 5)")
    genres = []
    for result in cursor:
        genres.append(result[0])  # can also be accessed using result[0]
    cursor.close()

    cursor = g.conn.execute("SELECT title FROM album_release ORDER BY title LIMIT 10")
    albums = []
    for result in cursor:
        albums.append(result[0])  # can also be accessed using result[0]
    cursor.close()

    cmd = "SELECT S.name FROM create_station AS S WHERE S.uid=%s LIMIT 10"
    cursor = g.conn.execute(cmd, uid)
    stations = []
    for result in cursor:
        stations.append(result[0])  # can also be accessed using result[0]
    cursor.close()

    cmd = "SELECT DISTINCT S.title, MAX(L.time) FROM song AS S, listen AS L WHERE L.uid=%s and S.songid=L.songid GROUP BY S.title ORDER BY MAX(L.time) DESC LIMIT 10"
    cursor = g.conn.execute(cmd, uid)
    played = []
    for result in cursor:
        played.append(result[0])  # can also be accessed using result[0]
    cursor.close()

    context = dict(name = username)
    context['artists'] = artists
    context['songs'] = songs
    context['genres'] = genres
    context['albums'] = albums
    context['stations'] = stations
    context['played'] = played

    return render_template('music.html', **context)

@app.route('/user/<username>/create_station', methods=['GET', 'POST'])
def creation_station(username):
    if request.method == 'POST':
        stationName = request.form['stationName']
        if stationName == '':
            error = 'Please enter a station name'
            return render_template('create_station.html', name=username, error=error)
        else:
            theme = request.form['theme']
            cmd = "SELECT count(*) FROM create_station AS S, users as U WHERE U.username=%s and S.uid=U.uid"
            cursor = g.conn.execute(cmd, username)
            result = cursor.first()
            stationid = int(result[0]) + 1

            cmd = "SELECT uid FROM users WHERE users.username=%s"
            cursor = g.conn.execute(cmd, username)
            result = cursor.first()
            uid = result[0]
            
            cmd = "INSERT INTO create_station VALUES(now(), %s, %s, %s, %s)"
            cursor = g.conn.execute(cmd, uid, stationid, stationName, theme)

            message = "New Station '" + stationName + "' Created!"
            return render_template('create_station.html', name=username, message=message)
    else:
        return render_template('create_station.html', name=username)

@app.route('/user/<username>/search/<query>')
def search(username, query):
    cmd = "SELECT stagename FROM artist WHERE stagename ILIKE " + "'%" + "%s" + "%'" 
    cursor = g.conn.execute(cmd, query)
    songResults = []
    for result in cursor:
        songResults.append(result[0])  # can also be accessed using result[0]
    cursor.close()

    context = dict(songResults = songResults)

    return render_template('search.html', **context)

def valid_login(username):
    cmd = 'SELECT uid FROM Users where name=:name1'
    cursor = g.conn.execute(text(cmd), name1=username)
    for result in cursor:
        print result
        #print result.rowcount
        cursor.close()
        print 'logging in'
        return True
    cursor.close()
    print 'wrong login'
    return False

def username_exists(username):
    cmd = 'SELECT uid FROM Users where username=:username1'
    cursor = g.conn.execute(text(cmd), username1=username)
    for result in cursor:
        print result
        #print result.rowcount
        cursor.close()
        print 'duplicate username', username
        return True
    cursor.close()
    print 'username doesnt exist', username
    return False


#AFTER LOGIN - user session username
########################################
def get_stations_for_user():
    username = session['username']
    cmd = 'SELECT create_station.stationid, create_station.name, create_station.theme FROM create_station, Users WHERE Users.username=:username1 AND Users.uid=create_station.uid'
    cursor = g.conn.execute(text(cmd), username1=username)
    user_stations = {}
    for result in cursor:
        print result
        for i in result:
            print i
        print "result0", result[0]
        print "result1", result[1]
        user_stations[result[0]] = [result[1], result[2]]
    cursor.close()
    return user_stations

def get_song_favs_for_user():
    username = session['username']
    cmd = 'SELECT song.songid, song.title, song.genre, album_release.title, artist.stagename FROM song, album_release, artist, song_favorites, Users WHERE Users.username=:username1 AND Users.uid=song_favorites.uid AND song.songid=song_favorites.songid AND album_release.albumid=song.albumid AND song.uid=artist.uid'
    cursor = g.conn.execute(text(cmd), username1=username)
    user_song_favs = {}
    for result in cursor:
        print result
        user_song_favs[result[0]] = [result[1], result[2], result[3], result[4]]
    cursor.close()
    return user_song_favs

def get_friends():
    username = session['username']
    cmd = 'SELECT friend.uid1, friend.uid2, friend.isfriend, Users1.name, Users2.name FROM friend, Users AS Users1, Users AS Users2 WHERE friend.uid1=Users1.uid AND friend.uid2=Users2.uid AND (Users1.username=:username1 OR Users2.username=:username1)'
    cursor = g.conn.execute(text(cmd), username1=username)
    friends = {}
    for result in cursor:
        print result
        if result[0]==username:
            friends[result[1]] = [result[4], result[2]]
        else: 
            friends[result[0]] = [result[3], result[2]]
    cursor.close()
    return friends

def get_name_from_username():
    username = session['username']
    cmd = 'SELECT name FROM Users where username=:username1'
    cursor = g.conn.execute(text(cmd), username1=username)
    for result in cursor:  
        name = result[0]
        cursor.close()
        return name

def get_subs():
    username = session['username']
    cmd = 'SELECT artist.stagename, artist.uid FROM artist, subscription, Users WHERE subscription.uid1=Users.uid AND Users.username=:username1 AND subscription.uid2=artist.uid'
    cursor = g.conn.execute(text(cmd), username1=username)
    subs = {}
    for result in cursor:
        print result
        subs[result[1]] = [result[0]]
    cursor.close();
    return subs


#ROUTE FUNCTIONS
###############################################
@app.route('/')
def index():
    print request.args
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    print request.args
    if request.method == 'POST':
        if valid_login(request.form['username'])==True:
            print 'valid session for ', request.form['username']
            session['username'] = request.form['username']
            return redirect(url_for('profile', username=session['username']))
        else:
            error = 'Username not found!'
            print error
            return render_template('login.html', error = error)
    else:
        return render_template('login.html')

@app.route('/user/<username>')
def profile(username):
    name = get_name_from_username()
    stations = get_stations_for_user()
    favs = get_song_favs_for_user()
    friends = get_friends()
    subs = get_subs()
    for n in stations:
        print n
    return render_template('user.html', name=name, username=username, stations=stations, favs=favs, friends=friends, subs=subs)

@app.route('/logout', methods=['POST'])
def logout():
    print "logging out"
    session.pop('username', None)
    print "redirecting to login page"
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    print "signing up"
    print request.args
    if request.method == 'POST':
        print "here POST"
        username = request.form['username']
        name = request.form['name']
        dob = request.form['dob']
        print "username", username
        print "name", name
        if is_valid_username(username)==True:
            print "valid username:", username
            if username_exists(username) == True:
                error = "Duplicate username. Please select another name."
                print error
                return render_template('signup.html', error =error)
            if add_user(username, name, dob)==True:
                session['username'] = username
                print session['username']
                return redirect(url_for('profile', username=session['username']))
            else:
                error = "Please enter a valid date"
                print error
                return render_template('signup.html', error =error)
        else:
            error = 'Invalid username. Please use alphanumeric characters only.'
            print error
            return render_template('signup.html', error = error)
    else:
        print "here GET"
        return render_template('signup.html')

app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to e.g., localhost:8111/foobar/ with POST or GET then you could use
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
# 
# see for routing: http://flask.pocoo.org/docs/0.10/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#
#@app.route('/')
#def index():
#  """
#  request is a special object that Flask provides to access web request information:
#
#  request.method:   "GET" or "POST"
#  request.form:     if the browser submitted a form, this contains the data in the form
#  request.args:     dictionary of URL arguments e.g., {a:1, b:2} for http://localhost?a=1&b=2
#
#  See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
#  """

  # DEBUG: this is debugging code to see what request looks like
#  print request.args


  #
  # example of a database query
  #
  #cursor = g.conn.execute("SELECT name FROM test")
  #names = []
  #for result in cursor:
  #  names.append(result['name'])  # can also be accessed using result[0]
  #cursor.close()

  #
  # Flask uses Jinja templates, which is an extension to HTML where you can
  # pass data to a template and dynamically generate HTML based on the data
  # (you can think of it as simple PHP)
  # documentation: https://realpython.com/blog/python/primer-on-jinja-templating/
  #
  # You can see an example template in templates/index.html
  #
  # context are the variables that are passed to the template.
  # for example, "data" key in the context variable defined below will be 
  # accessible as a variable in index.html:
  #
  #     # will print: [u'grace hopper', u'alan turing', u'ada lovelace']
  #     <div>{{data}}</div>
  #     
  #     # creates a <div> tag for each element in data
  #     # will print: 
  #     #
  #     #   <div>grace hopper</div>
  #     #   <div>alan turing</div>
  #     #   <div>ada lovelace</div>
  #     #
  #     {% for n in data %}
  #     <div>{{n}}</div>
  #     {% endfor %}
  #
  #context = dict(data = names)


  #
  # render_template looks in the templates/ folder for files.
  # for example, the below file reads template/index.html
  #
  #return render_template("index.html", **context)

#
# This is an example of a different path.  You can see it at
# 
#     localhost:8111/another
#
# notice that the functio name is another() rather than index()
# the functions for each app.route needs to have different names
#
#@app.route('/another')
#def another():
#  return render_template("anotherfile.html")


# Example of adding new data to the database
#@app.route('/add', methods=['POST'])
#def add():
#  name = request.form['name']
#  print name
#  cmd = 'INSERT INTO test(name) VALUES (:name1), (:name2)';
#  g.conn.execute(text(cmd), name1 = name, name2 = name);
#  return redirect('/')


#@app.route('/login')
#def login():
#    abort(401)
#    this_is_never_executed()


if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using

        python server.py

    Show the help text using

        python server.py --help

    """

    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
