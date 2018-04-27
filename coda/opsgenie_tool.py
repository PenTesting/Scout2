#!/usr/bin/env python3
from __future__ import print_function

import argparse
import os

import requests

from opsgenie.swagger_client import AlertApi
from opsgenie.swagger_client import configuration
from opsgenie.swagger_client.models import *
from opsgenie.swagger_client.rest import ApiException


OPS_GENIE_API_KEY = os.environ['OPS_GENIE_API_KEY']
CIRCLE_API_TOKEN = os.environ['CIRCLE_CI_API_TOKEN']
CIRCLE_BUILD_NUM = os.environ['CIRCLE_BUILD_NUM']
CIRCLE_PROJECT_REPONAME = os.environ['CIRCLE_PROJECT_REPONAME']
CIRCLE_PROJECT_USERNAME = os.environ['CIRCLE_PROJECT_USERNAME']
BRANCH_NAME = os.environ['CIRCLE_BRANCH']

configuration.api_key_prefix['Authorization'] = 'GenieKey'
configuration.api_key['Authorization'] = OPS_GENIE_API_KEY

# When this is ready, switch it to [TeamRecipient(name='eng_livesite')]
TEAMS = [UserRecipient(username='chris@coda.io', type='user')]

ALERT_IDENTIFIER = 'AWSSecurityAudit'
IDENTIFIER_TYPE = 'alias'
SOURCE = 'CircleCI Auditor'
USER = 'security-audit@coda.io'


def create_alert(detail):
    report_url = get_report_url()

    body = CreateAlertRequest(
        message='AWS Security Audit Failure',
        alias=ALERT_IDENTIFIER,
        description='Failed an AWS security audit sweep: Report at {}'.format(report_url),
        teams=TEAMS,
        visible_to=TEAMS,
        tags=['security', 'infra'],
        priority='P2',
        source=SOURCE,
        user=USER,
        note='Alert created')

    try:
        print('body: {}'.format(body))
        response = AlertApi().create_alert(body=body)
        print('request id: {}'.format(response.request_id))
        print('took: {}'.format(response.took))
        print('result: {}'.format(response.result))
    except ApiException as err:
        print("Exception when calling AlertApi->create_alert: %s\n" % err)


def alert_exists():
    try:
        AlertApi().get_alert(identifier=ALERT_IDENTIFIER, identifier_type=IDENTIFIER_TYPE)
        return True
    except ApiException:
        return False


def close_alert():
    if not alert_exists():
        return 0

    body = CloseAlertRequest(
        source=SOURCE,
        user=USER,
        note='Passed AWS security audit')

    try:
        response = AlertApi().close_alert(identifier=ALERT_IDENTIFIER, identifier_type=IDENTIFIER_TYPE, body=body)
        print(response)
    except ApiException as err:
        print("Exception when calling AlertApi->close_alert: %s\n" % err)


def get_report_url():
    """Retrieve the URL for the report produced by Scout2 and stored in CircleCI artifacts."""
    params = {'circle-token': CIRCLE_API_TOKEN}
    url = 'https://circleci.com/api/v1.1/project/github/{}/{}/{}/artifacts'.format(
        CIRCLE_PROJECT_USERNAME,
        CIRCLE_PROJECT_REPONAME,
        CIRCLE_BUILD_NUM)
    r = requests.get(url, params=params)
    response = r.json()
    for entry in response:
        path = entry['path']
        if path.endswith('report.html'):
            return entry['url']
    return ''

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['create_alert', 'close_alert'])
    parser.add_argument('--detail', default='')
    return parser.parse_args()


def main():
    args = parse_args()

    if BRANCH_NAME != 'master':
        print('Skipping reporting on branch {}'.format(BRANCH_NAME))
        return 0

    if args.command == 'create_alert':
        return create_alert(args.detail)
    elif args.command == 'close_alert':
        return close_alert()
    else:
        print('Command is required')
        return 1


if __name__ == "__main__":
    main()
