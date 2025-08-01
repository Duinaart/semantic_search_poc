FROM python:3.10

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
COPY ./README.md /code/README.md
COPY ./app.py /code/app.py
COPY ./query_transformer.py /code/query_transformer.py
COPY ./elastic_query.py /code/elastic_query.py

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

EXPOSE 7860

CMD ["python", "app.py"]
