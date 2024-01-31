# podcast-sponsor-block

### What is it?

podcast-sponsor-block provides [SponsorBlock](https://github.com/ajayyy/SponsorBlock) integration for your favorite
podcast apps.

### How does it work?
podcast-sponsor-block works by dynamically generating RSS feeds for a YouTube podcast playlist. When a media file is
requested from the generated RSS feed, podcast-sponsor-block will download the audio of the corresponding YouTube video
with the configured SponsorBlock segments removed and serve it back to your podcast app.

### Why only YouTube?
[SponsorBlock](https://github.com/ajayyy/SponsorBlock) currently only collects data for YouTube, so podcasts not
available on YouTube won't have data available :(. Early on, I tried allowing the source audio to be downloaded from
another RSS source but discovered a few problems:
1. Finding the YouTube video that corresponds to a podcast episode can be unreliable
2. Podcast audio can differ between platforms which would cause the [SponsorBlock](https://github.com/ajayyy/SponsorBlock)
   offsets to be inaccurate and, ultimately, the wrong segments of the audio would be removed

### How do I run it?
The recommended way to run podcast-sponsor-block is as a Docker container. See
[docs/docker.md](docs/docker.md) for more information.
