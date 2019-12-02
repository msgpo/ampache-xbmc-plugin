import sys
import os
import socket
import re
import random,xbmcplugin,xbmcgui, datetime, time, urllib,urllib2
import xml.etree.ElementTree as ET
import hashlib
import xbmcaddon
import ssl

# Shared resources

ampache = xbmcaddon.Addon("plugin.audio.ampache")

ampache_dir = xbmc.translatePath( ampache.getAddonInfo('path') )
BASE_RESOURCE_PATH = os.path.join( ampache_dir, 'resources' )
mediaDir = os.path.join( BASE_RESOURCE_PATH , 'media' )
cacheDir = os.path.join( mediaDir , 'cache' )
imagepath = os.path.join( mediaDir ,'images')


#   string to bool function : from string 'true' or 'false' to boolean True or
#   False, raise ValueError
def str_to_bool(s):
    if s == 'true':
        return True
    elif s == 'false':
        return False
    else:
        raise ValueError

def cacheArt(url):
	strippedAuth = url.split('&')
	imageID = re.search(r"id=(\d+)", strippedAuth[0])
        #security check:
        #also nexcloud server doesn't send images
        if imageID == None:
            raise NameError
        
        imageNamePng = imageID.group(1) + ".png"
        imageNameJpg = imageID.group(1) + ".jpg"
        pathPng = os.path.join( cacheDir , imageNamePng )
        pathJpg = os.path.join( cacheDir , imageNameJpg )
	if os.path.exists( pathPng ):
                xbmc.log("AmpachePlugin::CacheArt: png cached",xbmc.LOGDEBUG)
		return pathPng
        elif os.path.exists( pathJpg ):
                xbmc.log("AmpachePlugin::CacheArt: jpg cached",xbmc.LOGDEBUG)
		return pathJpg
	else:
                xbmc.log("AmpachePlugin::CacheArt: File needs fetching ",xbmc.LOGDEBUG)
                opener = handle_request(url)
		if opener.headers.maintype == 'image':
			extension = opener.headers['content-type']
			tmpExt = extension.split("/")
			if tmpExt[1] == "jpeg":
				fname = imageNameJpg
			else:
				fname = imageID.group(1) + '.' + tmpExt[1]
                        pathJpg = os.path.join( cacheDir , fname )
			open( pathJpg, 'wb').write(opener.read())
                        xbmc.log("AmpachePlugin::CacheArt: Cached " + str(fname), xbmc.LOGDEBUG )
                        opener.close()
			return pathJpg
		else:
                        xbmc.log("AmpachePlugin::CacheArt: It didnt work", xbmc.LOGDEBUG )
                        opener.close()
                        raise NameError
			#return False

#return album and artist name, only album could be confusing
def get_album_artist_name(node):
    fullname = node.findtext("name").encode("utf-8")
    fullname += " - "
    fullname += node.findtext("artist").encode("utf-8")
    return fullname

def get_artLabels(albumArt):
    art_labels = {
            'banner' : albumArt, 
            'thumb': albumArt, 
            'icon': albumArt,
            'fanart': albumArt
            }
    return art_labels

def get_art(node):
    try:
        albumArt = cacheArt(node.findtext("art"))
    except NameError:
        albumArt = "DefaultFolder.png"
    xbmc.log("AmpachePlugin::get_art: albumArt - " + str(albumArt), xbmc.LOGDEBUG )
    return albumArt

def get_infolabels(object_type , node):
    infoLabels = None
    if object_type == 'albums':
        infoLabels = {
            'Title' : unicode(node.findtext("name")) ,
            'Album' : unicode(node.findtext("name")) ,
            'Artist' : unicode(node.findtext("artist")),
            'Discnumber' : unicode(node.findtext("disk")),
            'Year' : node.findtext("year") ,
            'Rating' : node.findtext("preciserating"),
            'Mediatype' : 'album'
        }
 
    elif object_type == 'artists':
        
        infoLabels = {
            'Title' : unicode(node.findtext("name")) ,
            'Artist' : unicode(node.findtext("name")),
            'Rating' : node.findtext("preciserating"),
            'Mediatype' : 'artist'
        }

    elif object_type == 'songs':
        infoLabels = {
            'Title' : unicode(node.findtext("title")) ,
            'Artist' : unicode(node.findtext("artist")),
            'Album' :  unicode(node.findtext("album")),
            'Size' : node.findtext("size") ,
            'Duration' : node.findtext("time"),
            'Year' : node.findtext("year") ,
            'Tracknumber' : node.findtext("track"),
            'Rating' : node.findtext("preciserating"),
            'Mediatype' : 'song'
        }

    return infoLabels

#handle albumArt and song info
def fillListItemWithSongInfo(liz,node):
    albumArt = get_art(node)
    liz.setLabel(unicode(node.findtext("title")))
    liz.setArt( get_artLabels(albumArt) )
    #needed by play_track to play the song, added here to uniform api
    liz.setPath(node.findtext("url"))
    liz.setInfo( type="music", infoLabels=get_infolabels("songs", node) )
    liz.setMimeType(node.findtext("mime"))

# Used to populate items for songs on XBMC. Calls plugin script with mode == 9 and object_id == (ampache song id)
# TODO: Merge with addDir(). Same basic idea going on, this one adds links all at once, that one does it one at a time
#       Also, some property things, some different context menu things.
def addSongLinks(elem):
   
    #win_id is necessary to avoid problems in musicplaylist window, where this
    #script doesn't work
    curr_win_id = xbmcgui.getCurrentWindowId()
    xbmcplugin.setContent(int(sys.argv[1]), "songs")
    ok=True
    it=[]
    for node in elem.iter("song"):
        liz=xbmcgui.ListItem()
        fillListItemWithSongInfo(liz,node)
        liz.setProperty("IsPlayable", "true")

        cm = []
        try:
            artist_elem = node.find("artist")
            artist_id = int(artist_elem.attrib["id"])
            cm.append( ( "Show artist from this song",
            "XBMC.Container.Update(%s?object_id=%s&mode=15&win_id=%s)" % (
                sys.argv[0],artist_id, curr_win_id ) ) )
        except:
            pass
        
        try:
            album_elem = node.find("album")
            album_id = int(album_elem.attrib["id"])
            cm.append( ( "Show album from this song",
            "XBMC.Container.Update(%s?object_id=%s&mode=16&win_id=%s)" % (
                sys.argv[0],album_id, curr_win_id ) ) )
        except:
            pass
        
        try:
            song_elem = node.find("song")
            song_title = unicode(node.findtext("title"))
            cm.append( ( "Search all songs with this title",
            "XBMC.Container.Update(%s?title=%s&mode=17&win_id=%s)" % (
                sys.argv[0],song_title, curr_win_id ) ) )
        except:
            pass

        if cm != []:
            liz.addContextMenuItems(cm)

        song_elem = node.find("song")
        song_id = int(node.attrib["id"])
        track_parameters = { "mode": 9, "object_id": song_id}
        url = sys.argv[0] + '?' + urllib.urlencode(track_parameters)
        tu= (url,liz)
        it.append(tu)
    
    ok=xbmcplugin.addDirectoryItems(handle=int(sys.argv[1]),items=it,totalItems=len(elem))
    xbmc.log("AmpachePlugin::addSongLinks " + str(ok), xbmc.LOGDEBUG)
    return ok

# The function that actually plays an Ampache URL by using setResolvedUrl. Gotta have the extra step in order to make
# song album art / play next automatically. We already have the track URL when we add the directory item so the api
# hit here is really unnecessary. Would be nice to get rid of it, the extra request adds to song gaps. It does
# guarantee that we are using a legit URL, though, if the session expired between the item being added and the actual
# playing of that item.
def play_track(id):
    ''' Start to stream the track with the given id. '''
    try:
        elem = ampache_http_request("song",filter=id)
    except:
        return
    for thisnode in elem:
        node = thisnode
    liz = xbmcgui.ListItem()
    fillListItemWithSongInfo(liz,node)
    xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True,listitem=liz)

# Main function for adding xbmc plugin elements
def addDir(name,object_id,mode,iconImage=None,elem=None,infoLabels=None):
    xbmc.log("AmpachePlugin::addDir name " + name, xbmc.LOGDEBUG)
    if iconImage == None:
        iconImage = "DefaultFolder.png"
    
    if infoLabels == None:
        infoLabels={ "Title": name }
    
    liz=xbmcgui.ListItem(name)
    liz.setInfo( type="Music", infoLabels=infoLabels )
    liz.setArt(  get_artLabels(iconImage) )
    liz.setProperty('IsPlayable', 'false')

    try:
        artist_elem = elem.find("artist")
        artist_id = int(artist_elem.attrib["id"]) 
        cm = []
        cm.append( ( "Show all albums from artist", "XBMC.Container.Update(%s?object_id=%s&mode=2)" % ( sys.argv[0],artist_id ) ) )
        liz.addContextMenuItems(cm)
    except:
        pass

    u=sys.argv[0]+"?object_id="+str(object_id)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
    xbmc.log("AmpachePlugin::addDir url " + u, xbmc.LOGDEBUG)
    ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
    xbmc.log("AmpachePlugin::addDir ok " + str(ok), xbmc.LOGDEBUG)
    return ok

#catch all function to add items to the directory using the low level addDir
#or addSongLinks functions
def addItem( object_type, mode , elem, useCacheArt=True):
    image = "DefaultFolder.png"
    xbmc.log("AmpachePlugin::addItem: object_type - " + str(object_type) , xbmc.LOGDEBUG )
    if object_type == 'albums':
        allid = set()
        for node in elem.iter('album'):
            #no unicode function, cause urllib quot_plus error ( bug )
            album_id = int(node.attrib["id"])
            #remove duplicates in album names ( workaround for a problem in server comunication )
            if album_id not in allid:
                allid.add(album_id)
            else:
                continue
            fullname = get_album_artist_name(node)
            if useCacheArt:
                image = get_art(node)
            addDir(fullname,node.attrib["id"],mode,image,node,infoLabels=get_infolabels("albums",node))
    elif object_type == 'artists':
        for node in elem.iter('artist'):
            addDir(node.findtext("name").encode("utf-8"),node.attrib["id"],mode,image,node,infoLabels=get_infolabels("artists",node))
    elif object_type == 'playlists':
        for node in elem.iter('playlist'):
            addDir(node.findtext("name").encode("utf-8"),node.attrib["id"],mode,image,node)
    elif object_type == 'tags':
        for node in elem.iter('tag'):
            addDir(node.findtext("name").encode("utf-8"),node.attrib["id"],mode,image,node)
    elif object_type == 'songs':
        addSongLinks(elem)

def get_params():
    xbmc.log("AmpachePlugin::get_params " + sys.argv[2], xbmc.LOGDEBUG)
    param=[]
    paramstring=sys.argv[2]
    if len(paramstring)>=2:
            params=sys.argv[2]
            cleanedparams=params.replace('?','')
            if (params[len(params)-1]=='/'):
                    params=params[0:len(params)-2]
            pairsofparams=cleanedparams.split('&')
            param={}
            for i in range(len(pairsofparams)):
                    splitparams={}
                    splitparams=pairsofparams[i].split('=')
                    if (len(splitparams))==2:
                            param[splitparams[0]]=splitparams[1]
                            
    return param
    
def getFilterFromUser():
    kb =  xbmcgui.Dialog()
    result = kb.input('', type=xbmcgui.INPUT_ALPHANUM)
    if result:
        filter = result
    else:
        return False
    return(filter)

def get_user_pwd_login_url(nTime):
    myTimeStamp = str(nTime)
    sdf = ampache.getSetting("password")
    hasher = hashlib.new('sha256')
    hasher.update(ampache.getSetting("password"))
    myKey = hasher.hexdigest()
    hasher = hashlib.new('sha256')
    hasher.update(myTimeStamp + myKey)
    myPassphrase = hasher.hexdigest()
    myURL = ampache.getSetting("server") + '/server/xml.server.php?action=handshake&auth='
    myURL += myPassphrase + "&timestamp=" + myTimeStamp
    myURL += '&version=' + ampache.getSetting("api-version") + '&user=' + ampache.getSetting("username")
    return myURL

def get_auth_key_login_url():
    myURL = ampache.getSetting("server") + '/server/xml.server.php?action=handshake&auth='
    myURL += ampache.getSetting("api_key")
    myURL += '&version=' + ampache.getSetting("api-version")
    return myURL

def handle_request(url):
    try:
        xbmc.log(url,xbmc.LOGNOTICE)
        req = urllib2.Request(url)
        ssl_certs_str = ampache.getSetting("disable_ssl_certs")
        if str_to_bool(ssl_certs_str):
            gcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            response = urllib2.urlopen(req, context=gcontext, timeout=400)
            xbmc.log("AmpachePlugin::AmpacheConnect: ssl",xbmc.LOGDEBUG)
        else:
            response = urllib2.urlopen(req, timeout=400)
            xbmc.log("AmpachePlugin::AmpacheConnect: nossl",xbmc.LOGDEBUG)
    except:
        xbmc.log("AmpachePlugin::ConnectionError",xbmc.LOGDEBUG)
        xbmc.executebuiltin("ConnectionError" )
        raise ConnectionError
    return response

def AMPACHECONNECT():
    socket.setdefaulttimeout(3600)
    nTime = int(time.time())
    use_api_key = ampache.getSetting("use_api_key")
    if str_to_bool(use_api_key):
        myURL = get_auth_key_login_url() 
    else: 
        myURL = get_user_pwd_login_url(nTime)
    try:
        response = handle_request(myURL)
    except ConnectionError:
        raise ConnectionError
    tree=ET.parse(response)
    response.close()
    elem = tree.getroot()
    token = elem.findtext('auth')
    version = elem.findtext('api')
    #setSettings only string or unicode
    ampache.setSetting("api-version", version)
    total_artists = elem.findtext("artists")
    ampache.setSetting('artists',total_artists)
    total_albums = elem.findtext("albums")
    ampache.setSetting('albums',total_albums)
    total_songs = elem.findtext("songs")
    ampache.setSetting('songs',total_songs)
    total_playlists = elem.findtext("playlists")
    ampache.setSetting('playlists',total_playlists)
    ampache.setSetting('add',elem.findtext("add"))
    ampache.setSetting('token',token)
    ampache.setSetting('token-exp',str(nTime+24000))
    return elem

def ampache_http_request(action,add=None, filter=None, limit=5000,
        offset=0,amtype=None, exact=None, ampmode=None):
    thisURL = build_ampache_url(action,filter=filter,add=add,limit=limit,offset=offset,amtype=amtype,exact=exact,ampmode=ampmode)
    try:
        response = handle_request(thisURL)
    except ConnectionError:
        raise ConnectionError
    contents = response.read()
    contents = contents.replace("\0", "")
    #remove bug & it is not allowed as text in tags
    
    #code useful for debugging/parser needed
    xbmc.log("AmpachePlugin::ampache_http_request: contents " + contents, xbmc.LOGDEBUG)
    #parser = ET.XMLParser(recover=True)
    #tree=ET.XML(contents, parser = parser)
    tree=ET.XML(contents)
    response.close()
    if tree.findtext("error"):
        errornode = tree.find("error")
        if errornode.attrib["code"]=="401":
            try:
                tree = AMPACHECONNECT()
            except ConnectionError:
                raise ConnectionError
            thisURL = build_ampache_url(action,filter=filter,add=add,limit=limit,offset=offset,amtype=amtype,exact=exact)
            try:
                response = handle_request(thisURL)
            except ConnectionError:
                raise ConnectionError
            contents = response.read()
            tree=ET.XML(contents)
            response.close()
    return tree

def get_items(object_type, object_id=None, add=None,
        filter=None,limit=5000,useCacheArt=True, object_subtype=None, exact=None ):
    
    amtype = None
    mode = None
    ampmode = None

    xbmcplugin.setContent(int(sys.argv[1]), object_type)
    xbmc.log("AmpachePlugin::get_items: object_type " + object_type, xbmc.LOGDEBUG)
    if object_subtype:
        xbmc.log("AmpachePlugin::get_items: object_subtype " + object_subtype, xbmc.LOGDEBUG)

    #default: object_type is the action,otherwise see the if list below
    action = object_type
    
    #do not use action = object_subtype cause in tags it is used only to
    #discriminate between subtypes
    if object_type == 'albums':
        if object_subtype == 'artist_albums':
            action = 'artist_albums'
            addDir("All Songs",object_id,12)
        elif object_subtype == 'tag_albums':
            action = 'tag_albums'
        elif object_subtype == 'album':
            action = 'album'
        #stats management 
        elif object_subtype == 'hightest':
            action = 'stats'
            if(int(ampache.getSetting("api-version"))) > 400001:
                amtype = 'album'
                filter = 'hightest'
            else:
                amtype = object_subtype
        elif object_subtype == 'frequent':
            action = 'stats'
            if(int(ampache.getSetting("api-version"))) > 400001:
                amtype = 'album'
                filter = 'frequent'
            else:
                amtype = object_subtype
        elif object_subtype == 'flagged':
            action = 'stats'
            if(int(ampache.getSetting("api-version"))) > 400001:
                amtype = 'album'
                filter = 'flagged'
            else:
                amtype = object_subtype
    elif object_type == 'artists':
        if object_subtype == 'tag_artists':
            action = 'tag_artists'
        if object_subtype == 'artist':
            action = 'artist'
    elif object_type == 'songs':
        if object_subtype == 'tag_songs':
            action = 'tag_songs'
        elif object_subtype == 'playlist_songs':
            action = 'playlist_songs'
        elif object_subtype == 'album_songs':
            action = 'album_songs'
        elif object_subtype == 'artist_songs':
            action = 'artist_songs'
        elif object_subtype == 'search_songs':
            action = 'search_songs'

    if object_id:
        filter = object_id
    
    try:
        elem = ampache_http_request(action,add=add,filter=filter, limit=limit,
            amtype=amtype, exact=exact, ampmode=ampmode)
    except:
        return

    #after the request, set the mode 

    if object_type == 'artists':
        mode = 2
    elif object_type == 'albums':
        mode = 3
    elif object_type == 'playlists':
        mode = 14
    if object_type == 'tags':
        if object_subtype == 'tag_artists':
            mode = 19
        elif object_subtype == 'tag_albums':
            mode = 20
        elif object_subtype == 'tag_songs':
            mode = 21

    addItem( object_type, mode , elem, useCacheArt)

def build_ampache_url(action,filter=None,add=None,limit=5000,offset=0,amtype=None,exact=None,ampmode=None):
    tokenexp = int(ampache.getSetting('token-exp'))
    if int(time.time()) > tokenexp:
        xbmc.log("refreshing token...", xbmc.LOGNOTICE )
        try:
            elem = AMPACHECONNECT()
        except:
            return

    token=ampache.getSetting('token')    
    thisURL = ampache.getSetting("server") + '/server/xml.server.php?action=' + action 
    thisURL += '&auth=' + token
    thisURL += '&limit=' +str(limit)
    thisURL += '&offset=' +str(offset)
    if filter:
        thisURL += '&filter=' +urllib.quote_plus(str(filter))
    if add:
        thisURL += '&add=' + add
    if amtype:
        thisURL += '&type=' + amtype
    if ampmode:
        thisURL += '&mode=' + ampmode
    if exact:
        thisURL += '&exact=' + exact
    return thisURL

def get_time(time_offset):
    d = datetime.date.today()
    dt = datetime.timedelta(days=time_offset)
    nd = d + dt
    return nd.isoformat()

def do_search(object_type,object_subtype=None,thisFilter=None):
    if not thisFilter:
        thisFilter = getFilterFromUser()
    if thisFilter:
        get_items(object_type=object_type,filter=thisFilter,object_subtype=object_subtype)

def get_recent(object_type,object_id,object_subtype=None):   
    if object_id == 9999998:
        update = ampache.getSetting("add")        
        xbmc.log(update[:10],xbmc.LOGNOTICE)
        get_items(object_type=object_type,add=update[:10],object_subtype=object_subtype)
    elif object_id == 9999997:
        get_items(object_type=object_type,add=get_time(-7),object_subtype=object_subtype)
    elif object_id == 9999996:
        get_items(object_type=object_type,add=get_time(-30),object_subtype=object_subtype)
    elif object_id == 9999995:
        get_items(object_type=object_type,add=get_time(-90),object_subtype=object_subtype)

#get rid of this function in the near future and use simply get_items with limit = None
def get_all(object_type):
    try:
        elem = AMPACHECONNECT()
    except:
        return
    limit=int(elem.findtext(object_type))
    get_items(object_type=object_type, limit=limit, useCacheArt=False)

def get_random(object_type):
    xbmc.log("AmpachePlugin::get_random: object_type " + object_type, xbmc.LOGDEBUG)
    mode = None
    #object type can be : albums, artists, songs, playlists
    
    if object_type == 'albums':
        amtype='album'
        mode = 3
    elif object_type == 'artists':
        amtype='artist'
        mode = 2
    elif object_type == 'playlists':
        amtype='playlist'
        mode = 14
    elif object_type == 'songs':
        amtype='song'
    
    xbmcplugin.setContent(int(sys.argv[1]), object_type)
        
    random_items = (int(ampache.getSetting("random_items"))*3)+3
    xbmc.log("AmpachePlugin::get_random: random_items " + str(random_items), xbmc.LOGDEBUG )
    if(int(ampache.getSetting("api-version"))) > 400001:
        action = 'stats'
        filter = 'random'
        try:
            elem = ampache_http_request(action,filter=filter,
                    limit=random_items,amtype=amtype)
            addItem( object_type, mode , elem)
        except:
            return
    
    else: 
        items = int(ampache.getSetting(object_type))
        xbmc.log("AmpachePlugin::get_random: total items in the catalog " + str(items), xbmc.LOGDEBUG )
        if random_items > items:
            random_items = items
        seq = random.sample(xrange(items),random_items)
        xbmc.log("AmpachePlugin::get_random: seq " + str(seq), xbmc.LOGDEBUG )
        elements = []
        for item_id in seq:
            try:
                elem = ampache_http_request(object_type,offset=item_id,limit=1)
                elements.append(elem)
            except:
                pass
   
        for el in elements:
            addItem( object_type, mode , el)


params=get_params()
name=None
mode=None
object_id=None
win_id=None
title=None

try:
        name=urllib.unquote_plus(params["name"])
        xbmc.log("AmpachePlugin::name " + name, xbmc.LOGDEBUG)
except:
        pass
try:
        mode=int(params["mode"])
        xbmc.log("AmpachePlugin::mode " + str(mode), xbmc.LOGDEBUG)
except:
        pass
try:
        object_id=int(params["object_id"])
        xbmc.log("AmpachePlugin::object_id " + str(object_id), xbmc.LOGDEBUG)
except:
        pass
try:
        win_id=int(params["win_id"])
        xbmc.log("AmpachePlugin::win_id " + str(win_id), xbmc.LOGDEBUG)
except:
        pass
try:
        title=urllib.unquote_plus(params["title"])
        xbmc.log("AmpachePlugin::title " + title, xbmc.LOGDEBUG)
except:
        pass



if mode==None:
    try:
        elem = AMPACHECONNECT()
    except:
        elem = ET.Element("")
    addDir("Search...",0,4,"DefaultFolder.png")
    addDir("Recent...",0,5,"DefaultFolder.png")
    addDir("Random...",0,7,"DefaultFolder.png")
    addDir("Various...",0,23,"DefaultFolder.png")
    addDir("Artists (" + ampache.getSetting("artists")+ ")",None,1,"DefaultFolder.png")
    addDir("Albums (" + ampache.getSetting("albums") + ")",None,2,"DefaultFolder.png")
    addDir("Playlists (" + ampache.getSetting("playlists") + ")",None,13,"DefaultFolder.png")
    addDir("Tags",None,18,"DefaultFolder.png")

#   artist list ( called from main screen  ( mode None ) , search
#   screen ( mode 4 ) and recent ( mode 5 )  )

elif mode==1:
    #artist, album, songs, playlist follow the same structure
    #search function
    if object_id == 9999999:
        do_search("artists")
    #recent function
    elif object_id > 9999994 and object_id < 9999999:
        get_recent( "artists", object_id )
    elif object_id == 9999994:
        #removed cause nasty recursive call using some commands in web interface
        #addDir("Refresh..",9999994,2,os.path.join(imagepath,'refresh_icon.png'))
        get_random('artists')
    #all artists list
    else:
        get_all("artists")
       
#   albums list ( called from main screen ( mode None ) , search
#   screen ( mode 4 ) and recent ( mode 5 )  )

elif mode==2:
    num_items = (int(ampache.getSetting("random_items"))*3)+3
    if object_id == 9999999:
        do_search("albums")
    elif object_id > 9999994 and object_id < 9999999:
        get_recent( "albums", object_id )
    elif object_id == 9999994:
        get_items(object_type="albums",object_subtype="hightest",limit=num_items)
    elif object_id == 9999993:
        get_items(object_type="albums",object_subtype="frequent",limit=num_items)
    elif object_id == 9999992:
        get_items(object_type="albums",object_subtype="flagged",limit=num_items)
    elif object_id == 9999990:
        #removed cause nasty recursive call using some commands in web interface
        #addDir("Refresh..",9999990,2,os.path.join(imagepath, 'refresh_icon.png'))
        get_random('albums')
    elif object_id:
        get_items(object_type="albums",object_id=object_id,object_subtype="artist_albums")
    else:
        get_all("albums")

#   song mode ( called from search screen ( mode 4 ) and recent ( mode 5 )  )
        
elif mode==3:
        if object_id == 9999999:
            do_search("songs")
        elif object_id > 9999994 and object_id < 9999999:
            get_recent( "songs", object_id )
        elif object_id == 9999994:
            #removed cause nasty recursive call using some commands in web interface
            #addDir("Refresh..",9999994,2,os.path.join(imagepath, 'refresh_icon.png'))
            get_random('songs')
        else:
            get_items(object_type="songs",object_id=object_id,object_subtype="album_songs")


# search screen ( called from main screen )

elif mode==4:
    addDir("Search Artists...",9999999,1,"DefaultFolder.png")
    addDir("Search Albums...",9999999,2,"DefaultFolder.png")
    addDir("Search Songs...",9999999,3,"DefaultFolder.png")
    addDir("Search Playlists...",9999999,13,"DefaultFolder.png")
    addDir("Search All...",9999999,11,"DefaultFolder.png")
    addDir("Search Tags...",9999999,18,"DefaultFolder.png")

# recent additions screen ( called from main screen )

elif mode==5:
    addDir("Recent Artists...",9999998,6,"DefaultFolder.png")
    addDir("Recent Albums...",9999997,6,"DefaultFolder.png")
    addDir("Recent Songs...",9999996,6,"DefaultFolder.png")
    addDir("Recent Playlists...",9999995,6,"DefaultFolder.png")

#   screen with recent time possibilities ( subscreen of recent artists,
#   recent albums, recent songs ) ( called from mode 5 )

elif mode==6:
    #not clean, but i don't want to change too much the old code
    if object_id > 9999995:
        #object_id for playlists is 9999995 so 9999999-object_id is 4 that is search mode
        #i have to use another method, so i use the hardcoded mode number (13)
        mode_new = 9999999-object_id
    elif object_id == 9999995:
        mode_new = 13
    
    addDir("Last Update",9999998,mode_new,"DefaultFolder.png")
    addDir("1 Week",9999997,mode_new,"DefaultFolder.png")
    addDir("1 Month",9999996,mode_new,"DefaultFolder.png")
    addDir("3 Months",9999995,mode_new,"DefaultFolder.png")

# general random mode screen ( called from main screen )

elif mode==7:
    addDir("Random Artists...",9999994,1,"DefaultFolder.png")
    addDir("Random Albums...",9999990,2,"DefaultFolder.png")
    addDir("Random Songs...",9999994,3,"DefaultFolder.png")
    addDir("Random Playlists...",9999994,13,"DefaultFolder.png")

#old mode 
#
#random mode screen ( display artists, albums or songs ) ( called from mode
#   7  )
#elif mode==8:
#end old mode

#   play track mode  ( mode set in add_links function )

elif mode==9:
    play_track(object_id)

# mode 11 : search all
elif mode==11:
    do_search("songs","search_songs")

# mode 12 : artist_songs
elif mode==12:
    get_items(object_type="songs",object_id=object_id,object_subtype="artist_songs" )

#   playlist full list ( called from main screen )

elif mode==13:
        if object_id == 9999999:
            do_search("playlists")
        elif object_id > 9999994 and object_id < 9999999:
            get_recent( "playlists", object_id )
        elif object_id == 9999994:
            #removed cause nasty recursive call using some commands in web interface
            #addDir("Refresh..",9999994,2,os.path.join(imagepath, 'refresh_icon.png'))
            get_random('playlists')
        elif object_id:
            get_items(object_type="playlists",object_id=object_id)
        else:
            get_items(object_type="playlists")

#   playlist song mode

elif mode==14:
    get_items(object_type="songs",object_id=object_id,object_subtype="playlist_songs")
#        "Ampache Playlists"
# search for playlist song or recent playlist song ( this one for sure ) will
# be implemented if i will find a valid reason ( now i have no one )
#    get_items(object_type="playlists")
#        if object_id == 9999999:
#            thisFilter = getFilterFromUser()
#            if thisFilter:
#                get_items(object_type="playlist_songs",filter=thisFilter)
#        elif object_id == 9999998:
#            elem = AMPACHECONNECT()
#            update = elem.findtext("add")        
#            xbmc.log(update[:10],xbmc.LOGNOTICE)
#            get_items(object_type="playlist_songs",add=update[:10])
#        elif object_id == 9999997:
#            get_items(object_type="playlist_songs",add=get_time(-7))
#        elif object_id == 9999996:
#            get_items(object_type="playlist_songs",add=get_time(-30))
#        elif object_id == 9999995:
#            get_items(object_type="playlist_songs",add=get_time(-90))
#        else:
#           get_items(object_type="playlist_songs",object_id=object_id)

elif mode==15:
    if xbmc.getCondVisibility("Window.IsActive(musicplaylist)"):
        xbmc.executebuiltin("XBMC.ActivateWindow(%s)" % (win_id,))
    get_items(object_type="artists",object_id=object_id,object_subtype="artist")

elif mode==16:
    if xbmc.getCondVisibility("Window.IsActive(musicplaylist)"):
        xbmc.executebuiltin("XBMC.ActivateWindow(%s)" % (win_id,))
    get_items(object_type="albums",object_id=object_id,object_subtype="album")

elif mode==17:
    if xbmc.getCondVisibility("Window.IsActive(musicplaylist)"):
        xbmc.executebuiltin("XBMC.ActivateWindow(%s)" % (win_id,))
    do_search("songs",thisFilter=title)

elif mode==18:
    addDir("Artist tags...",object_id,19)
    addDir("Album tags...",object_id,20)
    addDir("Song tags...",object_id,21)

elif mode==19:
        if object_id == 9999999:
            do_search("tags","tag_artists")
        elif object_id:
            get_items(object_type="artists", object_subtype="tag_artists",object_id=object_id)
        else:
            get_items(object_type = "tags", object_subtype="tag_artists")

elif mode==20:
        if object_id == 9999999:
            do_search("tags","tag_albums")
        elif object_id:
            get_items(object_type="albums", object_subtype="tag_albums",object_id=object_id)
        else:
            get_items(object_type = "tags", object_subtype="tag_albums")

elif mode==21:
        if object_id == 9999999:
            do_search("tags","tag_songs")
        elif object_id:
            get_items(object_type="songs", object_subtype="tag_songs",object_id=object_id)
        else:
            get_items(object_type = "tags", object_subtype="tag_songs")

elif mode==23:
    addDir("Hightest Rated Albums...",9999994,2)
    addDir("Frequent Albums...",9999993,2)
    addDir("Flagged Albums...",9999992,2)

if mode < 30:
    xbmc.log("AmpachePlugin::endOfDirectory " + sys.argv[1],  xbmc.LOGDEBUG)
    xbmcplugin.endOfDirectory(int(sys.argv[1]))
