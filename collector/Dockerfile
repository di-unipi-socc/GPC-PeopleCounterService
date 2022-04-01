FROM python:3-slim

COPY setup_env.sh ./
RUN apt update --fix-missing
RUN apt -y install libpq-dev gcc libc-dev make git libffi-dev ffmpeg libsm6 libxext6 --fix-missing
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

ENV TZ=Europe/Rome
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY ./app .

RUN python ./users_db_setup.py

RUN chmod ugo+x ./start_server.sh
CMD [ "./start_server.sh"]
