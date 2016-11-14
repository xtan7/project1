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
import re
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

@app.route('/user/<username>/music', methods=['GET','POST'])
def music(username):
    uid = get_user_uid()

    cmd = "WITH popular AS (SELECT song.songid, song.title, COUNT(song.songid) AS playCount FROM song, listen WHERE song.songid=listen.songid AND listen.time>(NOW()-interval '6 month') GROUP BY song.songid ORDER BY playCount DESC LIMIT 10) "\
            "SELECT popular.songid, popular.title, artist.stagename, popular.playCount FROM popular, artist, song WHERE popular.songid=song.songid and song.uid=artist.uid ORDER BY popular.playCount DESC"
    cursor = g.conn.execute(cmd)
    mostPopular = []
    for result in cursor:
        mostPopular.append((result[0], result[1], result[2]))
    cursor.close()

    cmd = "WITH recent AS (SELECT DISTINCT S.songid, S.title, MAX(L.time) AS time FROM song AS S, listen AS L WHERE L.uid=%s and S.songid=L.songid " \
            "GROUP BY S.songid, S.title ORDER BY MAX(L.time) DESC LIMIT 10) SELECT recent.songid, recent.title, artist.stagename, recent.time FROM recent, artist, song "\
            "WHERE recent.songid=song.songid and song.uid=artist.uid ORDER BY recent.time DESC"
    cursor = g.conn.execute(cmd, uid)
    recentlyPlayed = []
    for result in cursor:
        recentlyPlayed.append((result[0], result[1], result[2]))
    cursor.close()

    context = dict(name = username)
    context['mostPopular'] = mostPopular
    context['recentlyPlayed'] = recentlyPlayed

    return render_template('music.html', now_playing=session['now_playing'], **context)

@app.route('/user/<username>/favorites')
def favorites(username):
    # Find uid
    uid = get_user_uid()

    songs = get_song_favs_for_user()
    albums =  get_album_favs_for_user()
    stations = get_station_favs_for_user()

    context = dict(name = username)
    context['songs'] = songs
    context['albums'] = albums
    context['stations'] = stations

    return render_template('favorites.html', now_playing=session['now_playing'], **context)

@app.route('/user/<username>/create_station', methods=['GET', 'POST'])
def creation_station(username):
    if request.method == 'POST':
        stationName = request.form['stationName']
        if stationName == '':
            error = 'Please enter a station name'
            return render_template('create_station.html', name=username, now_playing=session['now_playing'], error=error)
        elif station_exists(stationName):
            error = 'Station Name already exists'
            return render_template('create_station.html', name=username, now_playing=session['now_playing'], error=error)
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
            try:
                cursor = g.conn.execute(cmd, uid, stationid, stationName, theme)
                message = "New Station '" + stationName + "' Created!"
            except:
                print "problem creating station"
                message = "problem creating station"

            return render_template('create_station.html', name=username, now_playing=session['now_playing'], message=message)
    else:
        return render_template('create_station.html', name=username, now_playing=session['now_playing'])

@app.route('/user/<username>/music_search', methods=['GET'])
def music_search(username):
    query = request.args['query']
    augmented_query = "%" + query + "%"

    cmd = "SELECT S.songid, S.title, S.genre, A.title, artist.stagename FROM song as S, album_release AS A, artist WHERE (artist.stagename ILIKE %s or S.title ILIKE %s or A.title ILIKE %s or S.genre ILIKE %s) and S.albumid=A.albumid and artist.uid=A.uid LIMIT 200"
    cursor = g.conn.execute(cmd, augmented_query, augmented_query, augmented_query, augmented_query)
    songs = {}
    for result in cursor:
        songs[result[0]] = [result[1], result[2], result[3], result[4]]
    cursor.close()

    context = dict(songs = songs)
    context['query'] = query
    context['name'] = username

    return render_template('music_search.html', now_playing=session['now_playing'], **context)

@app.route('/user/<username>/album_search', methods=['GET'])
def album_search(username):
    query = request.args['query']
    augmented_query = "%" + query + "%"

    cmd = "SELECT album_release.albumid, album_release.title, artist.stagename, album_release.genre FROM album_release, artist WHERE (album_release.title ILIKE %s or artist.stagename ILIKE %s) and artist.uid=album_release.uid LIMIT 200"
    cursor = g.conn.execute(cmd, augmented_query, augmented_query)
    albums = {}
    for result in cursor:
        albums[result[0]] = [result[1], result[2], result[3]]
    cursor.close()

    context = dict(albums = albums)
    context['query'] = query
    context['name'] = username

    return render_template('album_search.html', now_playing=session['now_playing'], **context)


@app.route('/user/<username>/station_search', methods=['GET'])
def station_search(username):
    query = request.args['query']
    augmented_query = "%" + query + "%"

    cmd = "SELECT create_station.uid, create_station.stationid, create_station.name, create_station.theme, users.username FROM create_station, users WHERE (create_station.name ILIKE %s or users.username ILIKE %s or create_station.theme ILIKE %s) and users.uid=create_station.uid LIMIT 200"
    cursor = g.conn.execute(cmd, augmented_query, augmented_query, augmented_query)
    stations = {}
    for result in cursor:
        print result
        stations[(result[0],result[1])] = [result[2], result[3], result[4]]
    cursor.close()

    context = dict(stations = stations)
    context['query'] = query
    context['name'] = username

    return render_template('station_search.html', now_playing=session['now_playing'], **context)


@app.route('/user/<username>/station/<stationName>', methods=["GET","POST"])
def station_page(username, stationName):
    uid = get_user_uid()
    cmd = "SELECT theme FROM create_station WHERE uid=%s and name=%s"
    cursor = g.conn.execute(cmd, uid, stationName)
    theme = cursor.first()
    theme = theme[0]
    if theme == '' or theme == None:
        theme = 'no theme'

    stationid = get_station_id(uid, stationName)
    songs = get_songs_in_station(uid, stationid)

    context = dict(stationName = stationName)
    context['theme'] = theme
    context['songs'] = songs
    context['name'] = username
    context['now_playing'] = session['now_playing']
    return render_template('station.html', **context)

@app.route('/user/<username>/delete_station/<stationName>', methods=["POST"])
def delete_station(username, stationName):
    uid = get_user_uid()
    cmd = "DELETE FROM create_station WHERE uid=%s and name=%s"
    try:
        g.conn.execute(cmd, uid, stationName)
    except:
        print 'problem executing command'

    return redirect(url_for('profile', username=username))

@app.route('/user/<username>/delete_sub/<artistuid>', methods=["POST"])
def delete_sub(username, artistuid):
    uid = get_user_uid()
    cmd = "DELETE FROM subscription WHERE uid1=%s and uid2=%s"
    try:
        g.conn.execute(cmd, uid, artistuid)
    except:
        print 'problem deleting subscription'

    return redirect(url_for('subscription', username=username))

@app.route('/user/<username>/station/<stationName>/search', methods=['GET'])
def station_music_search(username, stationName):
    query = request.args['query']
    augmented_query = "%" + query + "%"

    cmd = "SELECT S.songid, S.title, S.genre, A.title, artist.stagename FROM song as S, album_release AS A, artist WHERE (artist.stagename ILIKE %s or S.title ILIKE %s or A.title ILIKE %s or S.genre ILIKE %s) and S.albumid=A.albumid and artist.uid=A.uid LIMIT 200"
    cursor = g.conn.execute(cmd, augmented_query, augmented_query, augmented_query, augmented_query)
    songs = {}
    for result in cursor:
        songs[result[0]] = [result[1], result[2], result[3], result[4]]
    cursor.close()

    context = dict(stationName = stationName)
    context['songs'] = songs
    context['name'] = username
    context['query'] = query
    context['now_playing'] = session['now_playing']

    return render_template('station_song_search.html', **context)

@app.route('/user/<username>/add_to_station/<stationName>/<songid>', methods=["POST"])
def add_to_station(username, stationName, songid):
    uid = get_user_uid()
    stationid = get_station_id(uid, stationName)
    cmd = "INSERT INTO add_to_station (stationid, uid, songid) VALUES (%s, %s, %s)"
    try:
        g.conn.execute(cmd, (stationid, uid, songid))
    except:
        print 'problem adding song to station'

    return redirect(url_for('station_page', username=username, stationName=stationName))

@app.route('/user/<username>/remove_from_station/<stationName>/<songid>', methods=["POST"])
def remove_from_station(username, stationName, songid):
    uid = get_user_uid()
    stationid = get_station_id(uid, stationName)
    cmd = "DELETE FROM add_to_station WHERE stationid=%s and uid=%s and songid=%s"
    try:
        g.conn.execute(cmd, (stationid, uid, songid))
    except:
        print 'problem adding song to station'

    return redirect(url_for('station_page', username=username, stationName=stationName))

@app.route('/user/<username>/friends', methods=['GET','POST'])
def my_friends(username):
    friends = get_friends()
    friend_requests_sent = get_friend_requests_sent()
    friend_requests_received = get_friend_requests_received()

    context = dict(friend_requests_received = friend_requests_received)
    context['friend_requests_sent'] = friend_requests_sent
    context['name'] = username
    context['friends'] = friends
    context['now_playing'] = session['now_playing']
    return render_template('friends.html', **context)

@app.route('/user/<username>/friend_search', methods=['GET'])
def friend_search(username):
    query = request.args['query']
    augmented_query = "%" + query + "%"
    current_friends = get_friends()

    cmd = "SELECT username, name, uid FROM users WHERE username ILIKE %s and username<>%s"
    cursor = g.conn.execute(cmd, augmented_query, username)
    results = {}
    for result in cursor:
        if result[2] not in current_friends.keys():
            results[result[0]] = result[1]
    cursor.close()

    context = dict(results = results)
    context['query'] = query
    context['name'] = username

    return render_template('friend_search.html', now_playing=session['now_playing'], **context)

@app.route('/user/<username>/add_friend/<toUsername>', methods=["POST"])
def send_friend_request(username, toUsername):
    uid1 = get_user_uid()
    cmd = "SELECT uid FROM users WHERE users.username=%s"
    cursor = g.conn.execute(cmd, toUsername)
    result = cursor.first()
    uid2 = result[0]

    cmd = "INSERT INTO friend (uid1, uid2, isfriend) VALUES (%s, %s, FALSE)"
    try:
        g.conn.execute(cmd, (uid1, uid2))
    except:
        print 'problem adding friend'

    return redirect(url_for('my_friends', username=username))

@app.route('/user/<username>/accept_request/<fromUsername>', methods=["POST"])
def accept_friend_request(username, fromUsername):
    uid2 = get_user_uid()
    cmd = "SELECT uid FROM users WHERE users.username=%s"
    cursor = g.conn.execute(cmd, fromUsername)
    result = cursor.first()
    uid1 = result[0]

    cmd = "UPDATE friend SET isfriend=TRUE WHERE uid1=%s and uid2=%s"
    try:
        g.conn.execute(cmd, (uid1, uid2))
    except:
        print 'problem adding friend'

    return redirect(url_for('my_friends', username=username))


@app.route('/user/<username>/subscription')
def subscription(username):
    subs = get_subs()
    context = dict(name=username)
    context['subs'] = subs
    return render_template('subscription.html', **context)

@app.route('/user/<username>/subscription/artist_search', methods=['GET'])
def artist_search(username):
    query = request.args['query']
    augmented_query = "%" + query + "%"

    cmd = "SELECT artist.stagename, artist.uid FROM artist WHERE artist.stagename ILIKE %s LIMIT 100"
    cursor = g.conn.execute(cmd, augmented_query)
    results = {}
    for result in cursor:
        results[result[1]] = result[0]
    cursor.close()

    context = dict(results = results)
    context['name'] = username
    context['query'] = query
    context['now_playing'] = session['now_playing']

    return render_template('artist_search.html', **context)


@app.route('/user/<username>/subscribe/<artistid>', methods=["POST"])
def subscribe(username, artistid):
    uid = get_user_uid()
    cmd = "INSERT INTO subscription (uid1, uid2, since) VALUES (%s, %s, now())"
    try:
        g.conn.execute(cmd, (uid, artistid))
    except:
        print 'problem subscribing to artist'

    return redirect(url_for('subscription', username=username))

@app.route('/user/<username>/add_song_to_favorites/<songid>', methods=["POST"])
def add_song_to_favorites(username, songid):
    uid = get_user_uid()
    cmd = "INSERT INTO song_favorites (uid, songid) VALUES (%s, %s)"
    try:
        g.conn.execute(cmd, (uid, songid))
    except:
        print 'problem adding song to favorites'

    return redirect(url_for('favorites', username=username))

@app.route('/user/<username>/delete_song_fav/<songid>', methods=["POST"])
def delete_song_from_favorites(username, songid):
    uid = get_user_uid()
    cmd = "DELETE FROM song_favorites WHERE uid=%s and songid=%s"
    try:
        g.conn.execute(cmd, (uid, songid))
    except:
        print 'problem deleting song from favorites'

    return redirect(url_for('favorites', username=username))

@app.route('/user/<username>/add_album_to_favorites/<albumid>', methods=["POST"])
def add_album_to_favorites(username, albumid):
    uid = get_user_uid()
    cmd = "INSERT INTO album_favorites (uid, albumid) VALUES (%s, %s)"
    try:
        g.conn.execute(cmd, (uid, albumid))
    except:
        print 'problem adding album to favorites'

    return redirect(url_for('favorites', username=username))

@app.route('/user/<username>/delete_album_fav/<albumid>', methods=["POST"])
def delete_album_from_favorites(username, albumid):
    uid = get_user_uid()
    cmd = "DELETE FROM album_favorites WHERE uid=%s and albumid=%s"
    try:
        g.conn.execute(cmd, (uid, albumid))
    except:
        print 'problem deleting album from favorites'

    return redirect(url_for('favorites', username=username))

@app.route('/user/<username>/add_station_to_favorites/<authoruid>/<stationid>', methods=["POST"])
def add_station_to_favorites(username, authoruid, stationid):
    uid = get_user_uid()
    cmd = "INSERT INTO station_favorites (uid, stationid, stationauthorid) VALUES (%s, %s, %s)"
    try:
        g.conn.execute(cmd, (uid, stationid, authoruid))
    except:
        print 'problem adding station to favorites'

    return redirect(url_for('favorites', username=username))

@app.route('/user/<username>/delete_station_fav/<authoruid>/<stationid>', methods=["POST"])
def delete_station_from_favorites(username, authoruid, stationid):
    uid = get_user_uid()
    cmd = "DELETE FROM station_favorites WHERE uid=%s and stationid=%s and stationauthorid=%s"
    try:
        g.conn.execute(cmd, (uid, stationid, authoruid))
    except:
        print 'problem deleting station from favorites'

    return redirect(url_for('favorites', username=username))


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

def station_exists(stationName):
    user_stations = get_stations_for_user()
    for v in user_stations.itervalues():
        if v[0] == stationName:
            return True
    return False


#AFTER LOGIN - use session username
########################################
def get_user_uid():
    username = session['username']
    cmd = "SELECT uid FROM users WHERE users.username=%s"
    cursor = g.conn.execute(cmd, username)
    result = cursor.first()
    return result[0]

def get_station_id(uid, stationName):
    cmd = "SELECT stationid FROM create_station WHERE uid=%s and name=%s"
    cursor = g.conn.execute(cmd, (uid, stationName))
    result = cursor.first()
    return result[0]

def get_songs_in_station(uid, stationid):
    cmd = "SELECT S.songid, S.title, S.genre, A.title, artist.stagename FROM song as S, album_release AS A, artist, add_to_station AS station WHERE station.uid=%s and station.stationid=%s and S.songid=station.songid and S.albumid=A.albumid and artist.uid=A.uid"
    cursor = g.conn.execute(cmd, (uid, stationid))
    songs = {}
    for result in cursor:
        songs[result[0]] = [result[1], result[2], result[3], result[4]]
    cursor.close()
    return songs

def get_friend_requests_sent():
    username = session['username']
    uid = get_user_uid()
    cmd = "SELECT U.name FROM users AS U, friend AS F WHERE F.uid1=%s and F.isfriend=FALSE and U.uid=F.uid2"
    friends = []
    cursor = g.conn.execute(cmd, uid)
    for result in cursor:
        friends.append(result[0])
    cursor.close()
    return friends

def get_friend_requests_received():
    username = session['username']
    uid = get_user_uid()
    cmd = "SELECT U.name FROM users AS U, friend AS F WHERE F.uid2=%s and F.isfriend=FALSE and U.uid=F.uid1"
    friends = []
    cursor = g.conn.execute(cmd, uid)
    for result in cursor:
        friends.append(result[0])
    cursor.close()
    return friends


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
        user_song_favs[result[0]] = [result[1], result[2], result[3], result[4]]
    cursor.close()
    return user_song_favs

def get_album_favs_for_user():
    username = session['username']
    cmd = 'SELECT album_release.albumid, album_release.title, artist.stagename, album_release.genre FROM album_release, artist, album_favorites, Users WHERE Users.username=:username1 AND Users.uid=album_favorites.uid AND album_release.albumid=album_favorites.albumid AND artist.uid=album_release.uid'
    cursor = g.conn.execute(text(cmd), username1=username)
    user_album_favs = {}
    for result in cursor:
        user_album_favs[result[0]] = [result[1], result[2], result[3]]
    cursor.close()
    return user_album_favs

def get_station_favs_for_user():
    username = session['username']
    cmd = 'SELECT create_station.stationid, create_station.name, U2.username, U2.uid FROM station_favorites, Users AS U1, Users AS U2, create_station WHERE U1.username=:username1 AND U1.uid=station_favorites.uid AND station_favorites.stationid=create_station.stationid AND station_favorites.stationauthorid=create_station.uid and U2.uid=create_station.uid'
    cursor = g.conn.execute(text(cmd), username1=username)
    user_station_favs = {}
    for result in cursor:
        user_station_favs[(result[3], result[0])] = [result[1], result[2]]
    cursor.close()
    return user_station_favs


def get_friends():
    username = session['username']
    cmd = 'SELECT friend.uid1, friend.uid2, friend.isfriend, Users1.username, Users2.username FROM friend, Users AS Users1, Users AS Users2 WHERE friend.uid1=Users1.uid AND friend.uid2=Users2.uid AND (Users1.username=:username1 OR Users2.username=:username1)'
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
    uid = 0
    for result in cursor:
        print result
        uid = result[0]
    cursor.close()
    cmd2 = "INSERT INTO artist (uid, stagename) VALUES(:uid1, :stagename1)"
    g.conn.execute(text(cmd2), uid1=uid, stagename1=stagename)
    return get_artist_uid()

def get_artist_uid():
    username = session['username']
    cmd = "SELECT artist.uid FROM artist, Users WHERE Users.uid=artist.uid AND Users.username=:username1"
    cursor = g.conn.execute(text(cmd), username1=username)
    uid = 0
    for result in cursor:
        print result
        uid = result[0]
    cursor.close()
    return uid

def add_album(title, genre):
    username = session['username']
    cmd="INSERT INTO album_release (albumid, title, genre, uid, releasedate) VALUES(DEFAULT, :title1, :genre1, :uid1, now())"
    uid = get_artist_uid()
    print "add_album", title, genre, uid
    g.conn.execute(text(cmd), title1=title, genre1=genre, uid1=uid)
    cmd2= "SELECT albumid FROM album_release WHERE title=:title1"
    cursor = g.conn.execute(text(cmd2), title1=title)
    albumid = 0
    for result in cursor:
        albumid= result[0]
        print "albumid1", albumid
    cursor.close()
    return albumid

def add_song_to_album(name, genre, albumid, uid):
    cmd="INSERT INTO song (songid, albumid, title, genre, uid) VALUES(DEFAULT, :albumid1, :name1, :genre1, :uid1)"
    g.conn.execute(text(cmd), name1=name, genre1=genre, albumid1=albumid, uid1=uid)

def get_uid():
    username = session['username']
    cmd = "SELECT uid FROM Users WHERE username=:username1"
    cursor = g.conn.execute(text(cmd), username1=username)
    uid = 0
    for result in cursor:
        uid=result[0]
    cursor.close()
    return uid

def add_to_listen(songid):
    uid = 0
    uid = get_uid()
    cmd="INSERT INTO listen (time, uid, songid) VALUES(now(), :uid1, :songid1)"
    g.conn.execute(text(cmd), uid1=uid, songid1=songid)
    cmd2 = "SELECT song.title, artist.stagename FROM song, artist WHERE songid=:songid1 AND song.uid=artist.uid"
    cursor = g.conn.execute(text(cmd2), songid1=songid)
    for result in cursor:
        session['now_playing'] =  '"'+result[0]+'" By '+result[1]
    

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
            session['now_playing'] = ''
            return redirect(url_for('profile', username=session['username']))
        else:
            error = 'Username not found!'
            print error
            return render_template('login.html', error = error)
    else:
        return render_template('login.html')

@app.route('/user/<username>')
def profile(username):
    tokens = request.full_path.split("=")
    song = 0
    for i in tokens:
       print "tokens", i 
    if len(tokens)>1:
        if len(tokens[1])>0:
            song = int(tokens[1])
    print "song", song
    if song!=0:
        add_to_listen(song)
    name = get_name_from_username()
    stations = get_stations_for_user()
    favs = get_song_favs_for_user()
    friends = get_friends()
    subs = get_subs()
    for n in stations:
        print n
    return render_template('user.html', name=name, now_playing=session['now_playing'], username=username, stations=stations, favs=favs, friends=friends, subs=subs)

@app.route('/user/<username>/artist', methods=['GET', 'POST'])
def artist(username):
   print request
   print "path", request.path
   print "full_path", request.full_path
   tokens = request.full_path.split("=")
   for i in tokens:
      print "tokens", i 
   albumname = tokens[1]
   albumname = re.sub(r'[^\w]', ' ', albumname)
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
   return render_template('artist.html', username=session['username'], now_playing=session['now_playing'], albumname=albumname, albums=albums, songs=songs)

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
        print "uid", uid
        if uid!=0:
            print "here"
            albumid=0
            albumid = add_album(request.form['album_title'], request.form['album_genre'])
            print "albumid", albumid
            if albumid!=0:
                print "here2"
                for n in range(1, 21):
                    print request.form
                    try:
                        if request.form["songname"+str(n)]!=None:
                            print "request.form", "songname"+str(n), request.form["songname"+str(n)]
                            if len(request.form["songname"+str(n)])>0:
                                add_song_to_album(request.form["songname"+str(n)], request.form["genre"+str(n)], albumid, uid)
                    except:
                        try:
                            if request.form["songname"+str(n)]!=None:
                                print "request.form", request.form["songname"+str(n)]
                                if len(request.form["songname"+str(n)])>0:
                                    add_song_to_album(request.form["songname"+str(n)], "", albumid, uid)
                        except:
                            print str(n)+"name not in form"
        return redirect(url_for('artist', username=session['username'], albumname=''))
    else:
        is_artist = False
        is_artist = get_artist();
        return render_template('create_album.html', username=session['username'], now_playing=session['now_playing'], is_artist=is_artist)

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    print "logging out"
    session.pop('username', None)
    session.pop('now_playing', None)
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
                session['now_playing'] = ''
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


@app.route("/signout")
def signout():
    return redirect(url_for('logout'))



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
