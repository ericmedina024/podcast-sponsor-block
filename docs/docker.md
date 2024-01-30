# Running with Docker

podcast-sponsor-block can be run as a container by following these steps:
1. Create a configuration [.env file](https://docs.docker.com/compose/environment-variables/env-file/) (see [configuration.md](configuration.md) and 
[the example configuration](example-configuration.env))
2. Clone the podcast-sponsor-block repository (`git clone https://github.com/ericmedina024/podcast-sponsor-block.git`)
3. Change directories to the cloned repository (`cd podcast-sponsor-block`)
4. Build the container (`docker build -t podcast-sponsor-block .`)
5. Run the container using the following command. Be sure to replace the parts surrounded in `<>` with your values!

    `docker run -it -v <host data path>:<PODCAST_DATA_PATH> --env-file <env file path> -p <host port>:8080 
    podcast-sponsor-block`

You can also run podcast-sponsor-block via `docker-compose`. Below is an example `compose.yml`. Be sure to replace the
parts surrounded in `<>` with your values!
```yaml
version: '3'
services:
  podcast-sponsor-block:
    build:
      context: <podcast-sponsor-block repo path>
      dockerfile: <podcast-sponsor-block Dockerfile path>
    container_name: podcast-sponsor-block
    hostname: podcast-sponsor-block
    env_file:
      - <config.env path>
    volumes:
      - "<host data path>:<PODCAST_DATA_PATH>"
    ports:
      - "<host port>:8080"
```
