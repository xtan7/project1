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

@app.route('/user/<username>/friends', methods=['GET','POST'])
def friends(username):
    return render_template('friends.html')

@app.route('/user/<username>/music', methods=['GET','POST'])
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

@app.route('/user/<username>/favorites')
def favorites(username):
    # Find uid
    cmd = "SELECT uid FROM users WHERE users.username=%s"
    cursor = g.conn.execute(cmd, username)
    result = cursor.first()
    uid = result[0]

    cmd = "SELECT A.stagename FROM artist AS A, subscription as S WHERE S.uid1=%s and S.uid2=A.uid LIMIT 10"
    cursor = g.conn.execute(cmd, uid)
    artists = []
    for result in cursor:
        artists.append(result[0])  # can also be accessed using result[0]
    cursor.close()

    cmd = "SELECT S.title FROM song_favorites AS fav, song as S WHERE fav.uid=%s and S.songid=fav.songid LIMIT 10"
    cursor = g.conn.execute(cmd, uid)
    songs = []
    for result in cursor:
        songs.append(result[0])  # can also be accessed using result[0]
    cursor.close()

    cmd = "SELECT A.title FROM album_favorites AS fav, album_release as A WHERE fav.uid=%s and A.albumid=fav.albumid LIMIT 10"
    cursor = g.conn.execute(cmd, uid)
    albums = []
    for result in cursor:
        albums.append(result[0])  # can also be accessed using result[0]
    cursor.close()

    cmd = "SELECT S.name FROM station_favorites AS fav, create_station as S WHERE fav.uid=%s and S.stationid=fav.stationid and S.uid=fav.stationauthorid LIMIT 10"
    cursor = g.conn.execute(cmd, uid)
    stations = []
    for result in cursor:
        stations.append(result[0])  # can also be accessed using result[0]
    cursor.close()

    context = dict(name = username)
    context['artists'] = artists
    context['songs'] = songs
    context['albums'] = albums
    context['stations'] = stations

    return render_template('favorites.html', **context)

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

@app.route('/user/<username>/music_search', methods=['GET', 'POST'])
def validate_music_search(username):
    if request.method == 'POST':
        if request.form['query'] != '':
            return redirect(url_for('music_search', username=session['username'], query=request.form['query']))
        else:
            error = 'Please enter search query'
            print error
            return render_template('music.html', error=error)
    else:
        return render_template('music.html')

@app.route('/user/<username>/music_search/<query>', methods=['GET', 'POST'])
def music_search(username, query):
    cmd = "SELECT stagename FROM artist WHERE stagename ILIKE " + "'%" + "%s" + "%'" 
    cursor = g.conn.execute(cmd, query)
    songResults = []
    for result in cursor:
        songResults.append(result[0])  # can also be accessed using result[0]
    cursor.close()

    context = dict(songResults = songResults)

    return render_template('music_search.html')

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


#AFTER LOGIN - use session username
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

def get_albums_for_user():
    username = session['username']
    cmd = 'SELECT album_release.albumid, album_release.title, album_release.genre, album_release.releasedate FROM album_release, Users WHERE Users.name=:username1 AND Users.uid=album_release.uid ORDER BY album_release.releasedate DESC'
    cursor = g.conn.execute(text(cmd), username1=username)
    albums = {}
    for result in cursor:
        print 'album', result
        albums[result[0]] = [result[1], result[2], result[3]]
    cursor.close()
    return albums


def get_songs_in_album(albumname):
    cmd = 'SELECT song.songid, song.title, song.genre FROM album_release, song WHERE album_release.title=:albumname1 AND album_release.albumid=song.albumid'
    cursor = g.conn.execute(text(cmd), albumname1=albumname)
    songs = {}
    for result in cursor:
        print 'song', result
        songs[result[0]] = [result[1], result[2]]
    cursor.close()
    return songs

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
        if result[3]==username:
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

def get_artist():
    username = session['username']
    cmd = "SELECT artist.stagename FROM artist, Users WHERE Users.username=:username1 AND Users.uid=artist.uid"
    cursor = g.conn.execute(text(cmd), username1=username)
    for result in cursor:
        print "stagename", result
        cursor.close();
        return True
    return False

def add_artist(stagename):
    username = session['username']
    cmd = "SELECT uid FROM Users where username=:username1"
    cursor = g.conn.execute(text(cmd), username1=username)
    uid = 0;
    for result in cursor:
        print result
        uid = result
    cusror.close()
    cmd2 = "INSERT INTO artist (uid, stagename) VALUES(:uid1, :stagename1)"
    g.conn.execute(text(cmd), uid1=uid, stagename1=stagename)
    return get_artist_uid()

def get_artist_uid():
    username = session['username']
    cmd = "SELECT artist.uid FROM artist, Users WHERE Users.uid=artist.uid AND Users.username=:username1"
    cursor = g.conn.execute(text(cmd), username1=username)
    uid = 0
    for result in cursor:
        print result
        uid = result
    cursor.close()
    return uid

def add_album(title, genre):
    username = session['username']
    cmd="INSERT INTO album_release (albumid, title, genre, uid, releasedate) VALUES(DEFAULT, :title1, :genre1, :uid1, now())"
    uid = get_artist_uid()
    g.conn.execute(text(cmd), title1=title, genre1=genre, uid1=uid)
    cmd2= "SELECT albumid FROM album_release WHERE title=:title1"
    cursor = g.conn.execute(text(cmd), title1=title)
    albumid = 0
    for result in cursor:
        print result
        albumid= result
    cursor.close()
    return albumid

def add_song_to_album(name, genre, albumid, uid):
    cmd="INSERT INTO song (songid, albumid, title, genre, uid) VALUES(DEFAULT, :name1, :genre1, :albumid1, :uid1)"
    g.conn.execute(text(cmd), name1=name, genre1=genre, albumid1=albumid, uid1=uid)
    

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
    #username = session['username']
    name = get_name_from_username()
    stations = get_stations_for_user()
    favs = get_song_favs_for_user()
    friends = get_friends()
    subs = get_subs()
    for n in stations:
        print n
    return render_template('user.html', name=name, username=username, stations=stations, favs=favs, friends=friends, subs=subs)

@app.route('/user/<username>/artist', methods=['GET', 'POST'])
def artist(username):
   print request
   print "path", request.path
   print "full_path", request.full_path
   tokens = request.full_path.split("=")
   for i in tokens:
      print "tokens", i 
   albumname = tokens[1]
   print "albumname", albumname
   albums = get_albums_for_user()
   songs = {}
   if len(albumname) !=0:
       songs = get_songs_in_album(albumname)
   else:
       for i in albums:
           print "getting songs for album", albums[i][0]
           albumname = albums[i][0]
           songs = get_songs_in_album(albums[i][0])
           break;
   return render_template('artist.html', username=session['username'], albumname=albumname, albums=albums, songs=songs)

@app.route('/user/<username>/create_album', methods=['GET', 'POST'])
def create_album(username):
    if request.method == 'POST':
        is_artist = False
        is_artist = get_artist();
        uid = 0;
        if is_artist!=True:
            uid = add_artist(request.form['stagename'])
        else:
            uid = get_artist_uid()
        if uid!=0:
            albumid=0
            albumid = add_album(request.form['album_title'], request.form['album_genre'])
            if albumid!=0:
                for n in range(1, 21):
                    if request.form[""+n+"name"]!=None:
                        add_song_to_album(request.form[""+n+"name"], request.form[""+n+"genre"], albumid, uid)
        return redirect(url_for('artist', username=session['username']))
    else:
        is_artist = False
        is_artist = get_artist();
        return render_template('create_album.html', username=session['username'], is_artist=is_artist)

@app.route('/logout', methods=['GET', 'POST'])
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


import datetime
@app.template_filter()
def datetimefilter(value, format='%Y/%m/%d %H:%M'):
     """convert a datetime to a different format."""
     return value.strftime(format)

app.jinja_env.filters['datetimefilter'] = datetimefilter

@app.route("/template")
def template_test():
     return render_template('template.html', my_string="Wheeeee!", 
         my_list=[0,1,2,3,4,5], title="Index", current_time=datetime.datetime.now())

@app.route("/home")
def home():
    return redirect(url_for('profile', username=session['username']))
#     #     my_list=[6,7,8,9,10,11], title="Home", current_time=datetime.datetime.now())
#     return redirect(url_for('profile', username=session['username']))


# @app.route("/about")
# def about():
#     return render_template('template.html', my_string="Bar", 
#         my_list=[12,13,14,15,16,17], title="About", current_time=datetime.datetime.now())

@app.route("/signout")
def signout():
    # return render_template('template.html', my_string="Foo", 
    #     my_list=[6,7,8,9,10,11], title="Home", current_time=datetime.datetime.now())
    return redirect(url_for('logout'))

@app.route("/about")
def about():
    return render_template('template.html', my_string="Bar", 
        my_list=[12,13,14,15,16,17], title="About", current_time=datetime.datetime.now())

# @app.route("/contact")
# def contact():
#     return render_template('template.html', my_string="FooBar"
#         , my_list=[18,19,20,21,22,23], title="Contact Us", current_time=datetime.datetime.now())




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
