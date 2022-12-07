#!/usr/bin/env python

from collections import namedtuple


try:
    import boto3
    from dropforge.aws import boto_conf
except ImportError:
    raise Exception('This module isn\'t here!')


SPLITS = '-'


Splitter = namedtuple(
    'Splitter', (
        'name', 
        'semver'
    )
)


def ecr_img_list(aws_id: str, registry: str, repo: str) -> list:
    ecr = boto3.client('ecr', config=boto_conf())
    resp = ecr.list_images(
        registryId=aws_id,
        repositoryName=repo,
        maxResults=1000,
        filter=dict(tagStatus='TAGGED', )
    )
    if resp:
        tags = list(
            t['imageTag'].split(SPLITS)
            for t in resp['imageIds']
        )
        return list(
            Splitter(name=t[0], semver=t[1])
            for t in tags 
            if len(t) == 2
        )
