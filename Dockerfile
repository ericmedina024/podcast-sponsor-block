FROM python:3.12.1-slim-bookworm

RUN apt-get update -qq && apt-get install ffmpeg -y

ARG user=appuser
ARG group=appuser
ARG uid=1000
ARG gid=1000
RUN groupadd -g ${gid} ${group}
RUN useradd -u ${uid} -g ${group} -s /bin/sh -m ${user}
USER ${uid}:${gid}

ENV PATH="/home/${user}/.local/bin:${PATH}"
COPY requirements.txt requirements.txt
RUN ["pip", "install", "-r", "requirements.txt"]



RUN echo 12
COPY src ${APP_DIR}
WORKDIR ${APP_DIR}
CMD [ \
    "gunicorn", \
    "--log-level=info", \
    "--logger-class=podcastsponsorblock.AuthKeyFilteringLogger", \
    "--log-file=-", \
    "--access-logfile=-", \
    "-b=0.0.0.0:8080", \
    "podcastsponsorblock:create_app()" \
]