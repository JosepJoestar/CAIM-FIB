from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from elasticsearch.exceptions import NotFoundError
import argparse
import os
import codecs
from elasticsearch_dsl import Index, analyzer, tokenizer


def generate_files_list(path):
    """
    Generates a list of all the files inside a path
    :param path:
    :return:
    """
    if path[-1] == '/':
        path = path[:-1]

    lfiles = []

    for lf in os.walk(path):
        if lf[2]:
            for f in lf[2]:
                lfiles.append(lf[0] + '/' + f)
    return lfiles


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', required=True,
                        default=None, help='Path to the files')
    parser.add_argument('--index', required=True,
                        default=None, help='Index for the files')
    args = parser.parse_args()

    path = args.path
    index = args.index

    ldocs = []

    # Reads all the documents in a directory tree and generates an index operation for each
    lfiles = generate_files_list(path)
    print('Indexing %d files' % len(lfiles))
    print('Reading files ...')
    for f in lfiles:
        ftxt = codecs.open(f, "r", encoding='iso-8859-1')
        text = ''
        for line in ftxt:
            text += line
        # Insert operation for a document with fields' path' and 'text'
        ldocs.append({'_op_type': 'index', '_index': index,
                      '_type': 'document', 'path': f, 'text': text})

    client = Elasticsearch()

    try:
        # Drop index if it exists
        ind = Index(index, using=client)
        ind.delete()
    except NotFoundError:
        pass
    # then create it
    ind.settings(number_of_shards=1)
    ind.create()

    ind = Index(index, using=client)

    # configure default analyzer
    ind.close()  # index must be closed for configuring analyzer

    # configure the path field so it is not tokenized and we can do exact match search
    client.indices.put_mapping(doc_type='document', index=index, body={
        "document": {
            "properties": {
                "path": {
                    "type": "keyword",
                }
            }
        }
    })

    # Configure index analyzer, limit tokens length to range [2-10]
    client.indices.put_settings(index=index, body={
        "analysis": {
            "filter": {
                "my_length": {
                    "type": "length",
                    "min": 2,
                    "max": 10
                }
            },
            "analyzer": {
                "default": {
                    "type": "custom",
                    "tokenizer": "letter",
                    "filter": [
                        "lowercase", "stop",
                        "asciifolding", "snowball", "my_length"
                    ]
                }
            }
        }
    })

    ind.open()
    print("Index settings=", ind.get_settings())
    # Bulk execution of elastic search operations (faster than executing all one by one)
    print('Indexing ...')
    bulk(client, ldocs)
