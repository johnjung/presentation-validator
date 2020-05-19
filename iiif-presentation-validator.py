#!/usr/bin/env python
# encoding: utf-8
"""IIIF Presentation Validation Service."""

import codecs
import json
import os
import sys
from gzip import GzipFile
from io import BytesIO
from jsonschema.exceptions import ValidationError, SchemaError

from urllib.request import urlopen, HTTPError, Request
from urllib.parse import urlparse

from schema import schemavalidator

egg_cache = "/path/to/web/egg_cache"
os.environ['PYTHON_EGG_CACHE'] = egg_cache

from iiif_prezi.loader import ManifestReader

from pyld import jsonld
jsonld.set_document_loader(jsonld.requests_document_loader(timeout=60))


class Validator(object):
    """Validator class that runs with Bottle."""

    def __init__(self):
        """Initialize Validator with default_version."""
        self.default_version = "2.1"

    def fetch(self, url):
        """Fetch manifest from url."""
        req = Request(url)
        req.add_header('User-Agent', 'IIIF Validation Service')
        req.add_header('Accept-Encoding', 'gzip')

        try:
            wh = urlopen(req)
        except HTTPError as wh:
            raise wh
        data = wh.read()
        wh.close()

        if wh.headers.get('Content-Encoding') == 'gzip':
            with GzipFile(fileobj=BytesIO(data)) as f:
                data = f.read()

        try:
            data = data.decode('utf-8')
        except:
            raise
        return(data, wh)

    def check_manifest(self, data, version, url=None, warnings=[]):
        """Check manifest data at version, return JSON."""
        infojson = {}
        # Check if 3.0 if so run through schema rather than this version...
        if version == '3.0':
            try:
                infojson = schemavalidator.validate(data, version, url)
                for error in infojson['errorList']:
                    error.pop('error', None)
            except ValidationError as e:
                infojson = {
                    'received': data,
                    'okay': 0,
                    'error': str(e),
                    'url': url
                }
        else:
            reader = ManifestReader(data, version=version)
            err = None
            try:
                mf = reader.read()
                mf.toJSON()
                # Passed!
                okay = 1
            except Exception as e:
                # Failed
                err = e
                okay = 0

            warnings.extend(reader.get_warnings())
            infojson = {
                'received': data,
                'okay': okay,
                'warnings': warnings,
                'error': str(err),
                'url': url
            }
        return json.dumps(infojson)


def main():
    data = sys.stdin.read()
    version = '2.1'

    v = Validator()

    js = json.loads(v.check_manifest(data, version))

    sys.stdout.write('OKAY: {}\n\n'.format(js['okay']))

    sys.stdout.write('WARNINGS:\n')
    for w in js['warnings']:
        sys.stdout.write(w)
    sys.stdout.write('\n')

    sys.stdout.write('ERROR:\n')
    sys.stdout.write(js['error'])
    sys.stdout.write('\n')
    

if __name__ == "__main__":
    main()
