FROM python:3.11.8-slim

WORKDIR /app

RUN apt-get update
RUN apt-get install gcc g++ ffmpeg libsm6 libxext6 wget git -y

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . /app

ENTRYPOINT [ "python", "utilities/load_neo4j_graph_docker.py"]