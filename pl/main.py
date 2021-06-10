from deezer import Deezer

dz = Deezer()

url = "https://www.deezer.com/us/playlist/91581234901234901327842"
playlist_id = url.split("/playlist/")[1]

pl = dz.api.get_playlist_tracks(playlist_id)

for track in pl['data']:
    track_id = track['id']
    track_title = track['title']
    artist_id = track['artist']['id']
    artist_name = track['artist']['name']
    album_id = track['album']['id']
    album_title = track['album']['title']

    print(f"track_id: {track_id}")
    print(f"track_title: {track_title}")
    print(f"artist_id: {artist_id}")
    print(f"artist_name: {artist_name}")
    print(f"album_id: {album_id}")
    print(f"album_title: {album_title}")
    print()
    print()
