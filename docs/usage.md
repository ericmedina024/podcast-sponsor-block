# How to use podcast-sponsor-block

To use podcast-sponsor-block, open your podcast app and add the following URL as an RSS feed:
```
http://<your instance>/rss/youtube/<youtube playlist id>
```

For example, if your instance was running on `https://podcasts.ericmedina024.com` and you wanted to add the
[Sleep With Me](https://www.youtube.com/watch?v=M5DjqEp9ugc&list=PLMdYRoC0mZlW2uoesMXUrac26lsvOupSx) podcast whose
playlist ID is `PLMdYRoC0mZlW2uoesMXUrac26lsvOupSx`, then your
url would look like:
```
https://podcasts.ericmedina024.com/rss/youtube/PLMdYRoC0mZlW2uoesMXUrac26lsvOupSx
```

If you have configured any aliases, you can use them in place of the playlist ID. Please
see [configuration.md](configuration.md) for more info.

If you have configured an auth key, you will need to supply the
auth key as HTTP basic auth password in your podcast app. The process to do so varies depending on which app you use,
but it's generally pretty easy and your app should have documentation online explaining it. If your podcast app doesn't
support basic auth, there is an option you can enable to allow the auth key to be specified as a query parameter. Please
see [configuration.md](configuration.md) for more info.

**Where do I find the ID of a YouTube playlist?**

You can find the ID of a YouTube playlist by navigating to the playlist in your browser. The playlist ID is the
`list` query parameter in the URL.
