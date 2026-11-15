"""Unprivileged Spinnaker Job client; no Git or signing credentials are mounted."""

import os
from pathlib import Path

from promotion_git import require
from promotion_authority import json_request


def request(operation):
    body = {'execution_id': os.environ['PROMOTION_EXECUTION_ID']}
    if operation == 'preview':
        body.update({field: os.environ['PROMOTION_' + field.upper()] for field in
                    ('config_revision', 'image_digest', 'release_id', 'mode', 'compatibility_reference')})
    else:
        body['approval_ticket'] = os.environ['PROMOTION_APPROVAL_TICKET']
    url = os.environ['PROMOTION_AUTHORITY_URL']
    require(url.startswith('https://'), 'Promotion authority requires HTTPS')
    token = Path('/authority-client/token').read_text().strip()
    return json_request(url.rstrip('/') + '/' + operation, body=body, ca='/authority-client/ca.pem',
                        headers={'Authorization': 'Bearer ' + token},
                        timeout=int(os.environ.get('PROMOTION_TIMEOUT_SECONDS', '900')) + 180)
