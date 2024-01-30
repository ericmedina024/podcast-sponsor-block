FROM python:3.12.1-slim-bookworm

RUN apt-get update -qq && apt-get install ffmpeg -y

ARG user=appuser
ARG group=appuser
ARG user_id=1000
ARG group_id=1000
RUN groupadd -g ${group_id} ${group}
RUN useradd -u ${user_id} -g ${group} -s /bin/sh -m ${user}
USER ${user_id}:${group_id}

ENV PATH="/home/${user}/.local/bin:${PATH}"
COPY requirements.txt requirements.txt
RUN ["pip", "install", "-r", "requirements.txt"]

ARG app_dir=/app/src
COPY src ${app_dir}
WORKDIR ${app_dir}
CMD [ \
    "gunicorn", \
    "--log-level=info", \
    "--logger-class=podcastsponsorblock.AuthKeyFilteringLogger", \
    "--log-file=-", \
    "--access-logfile=-", \
    "-b=0.0.0.0:8080", \
    "podcastsponsorblock:create_app()" \
]
