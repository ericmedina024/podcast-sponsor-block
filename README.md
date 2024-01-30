# podcast-sponsor-block

### What is it?

podcast-sponsor-block provides [SponsorBlock](https://github.com/ajayyy/SponsorBlock) integration for your favorite
podcast apps.

### How does it work?
podcast-sponsor-block works by dynamically generating RSS feeds for a YouTube podcast playlist. When a media file is
requested from the generated RSS feed, podcast-sponsor-block will download the audio of the corresponding YouTube video
with the configured SponsorBlock segments removed and serve it back to your podcast app.

### How do I run it?
The recommended way to run podcast-sponsor-block is as a Docker container. See
[docs/docker.md](docs/docker.md) for more information.
