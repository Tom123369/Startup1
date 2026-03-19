import yt_dlp
ydl_opts = {
    'quiet': True,
    'extract_flat': True,
}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info("ytsearch1:The Moon Carl", download=False)
    entry = info['entries'][0]
    print(entry.get('channel'))
    # try to get the channel url and then get logo
    chan_url = entry.get('channel_url')
    print('URL:', chan_url)
    if chan_url:
        info_chan = ydl.extract_info(chan_url, download=False)
        print('Chan uploader:', info_chan.get('uploader'))
        print('Chan thumbnails:', [t.get('url') for t in info_chan.get('thumbnails', [])])
