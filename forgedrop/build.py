#!/usr/bin/env python

import json
import os
import yaml

from collections import namedtuple
from copy import deepcopy
from distutils.version import StrictVersion
from json.decoder import JSONDecodeError
from subprocess import Popen, CalledProcessError

from docker import APIClient
from semantic_version import Version as semver

from forgedrop.objs import tagurler


Forger = namedtuple(
    'Forger', (
        'base_img_used',
        'buildargs',
        'build_it',
        'gcp_proj_id',
        'registry',
        'repo',
        'tag',
    )
)


FORGE = 'forge.yaml'
NOBUILD = 'Not building the image...'
SPLITS = '-'
UNIX_SOCK = 'unix://var/run/docker.sock'


def popen(comm: list) -> bool:
    err_mssg = 'Something gone wrong!'
    try:
        proc = Popen(comm, shell=False)
        proc.communicate()
        return True
    except CalledProcessError:
        print(err_mssg)
        return False


def _build(path: str, tag: str, buildargs: dict=dict()) -> None:
    cli = APIClient(base_url=UNIX_SOCK)
    for line in cli.build(
        path=path,
        rm=True,
        buildargs=buildargs,
        tag=tag
    ):
        line = line.decode('utf-8')
        line = line.split('\n')
        for row in line:
            row = ''.join(row)
            try:
                row = json.loads(row)
                stream = row.get('stream')
                if stream:
                    print(
                        stream
                        .replace(
                            '\n',
                            ''
                        )
                    )
                    if stream.find('ERROR') != -1:
                        return False
            except JSONDecodeError:
                pass
    return True


def build(dir: str, tag: str, bargs: dict=dict(), gitsha: str=str()) -> bool:
    kwargs = dict(path=dir, tag=tag, )
    if bargs:
        kwargs.update(
            dict(buildargs=bargs, )
        )
    if gitsha:
        bargs.update(
            dict(
                _GTISHA_=gitsha, 
            )
        )
    if _build(**kwargs):
        return True
    else:
        return False


def push(built: bool, tag: str) -> bool:
    if built:
        return popen(
            comm=[
                'docker',
                'push',
                tag
            ]
        )


def dockerit(
    confs: Forger,
    dir: str,
    tag: str, 
    gitsha: str=str(),
) -> None:
    result = push(
        built = build(
            bargs=confs.buildargs 
                if confs.buildargs 
                else dict(),
            dir=dir,
            gitsha=gitsha,
            tag=tag
        ),
        tag=tag
    )
    if result:
        print(
            f'{tag}'
            ' built & pushed!'
        )


def check_aws_id(confs: Forger, aws_id: str=str()) -> str:
    return (f'{aws_id}.{confs.registry}' 
        if aws_id 
        else confs.registry  
    )


def up_version(img_tag: str, tags: list) -> bool:
    name, curr_ver = img_tag.split(SPLITS)
    if tags:
        semvers = list(t.semver for t in tags if t.name == name)
        try:
            latest = sorted(
                semvers,
                key=StrictVersion
            )[-1]
        except IndexError:
            latest = '0.0.0'
    else:
        latest = '0.0.0'
    if semver(curr_ver) == semver('0.0.0'):
        return True
    if semver(curr_ver) > semver(latest):
        return True
    return False
  

def build_steps(
    confs: Forger,
    env: str,
    dir: str,
    aws_acct_id: str=str(),
    gitsha: str=str()
) -> None:

    registry = check_aws_id(confs=confs, aws_id=aws_acct_id)
    tag_kwargs = dict(repo=confs.repo, registry=registry, gitsha=gitsha, )
    tagged = tagurler(
        img_tag=confs.tag, 
        gcp_proj_id=confs.gcp_proj_id, 
        **tag_kwargs
    )

    if confs.build_it:
        dockerit(
            confs=confs,
            dir=dir,
            gitsha=gitsha[0:10] 
                if env in {'dev', 'qa', } 
                else str(),
            tag=tagged
        )
    else:
        print(NOBUILD)


def proc_conf(path: str, env: str) -> None:
    with open(path) as forge:
        conf = yaml.safe_load(forge)
        img_name, registry = conf['image_name'], conf['container_registry']      
        return Forger(
            base_img_used=conf.get('base_image_used'),
            buildargs=conf.get('buildargs'),
            build_it=conf.get(f'build_{env}'),
            gcp_proj_id=conf.get('gcp_project_id'),
            registry=registry,
            repo=conf.get('container_repo'),
            tag=img_name
        )


def build_an_image(
    dir: str,
    env: str,
    aws_acct_id: str=str(),
    gitsha: str=str(),
) -> None:
    confs = proc_conf(f'{dir}/{FORGE}', env)
    build_steps(
        confs,
        env,
        dir,
        aws_acct_id,
        gitsha
    )


def build_images(
    root_dir: str,
    env: str,
    aws_acct_id: str=str(),
    gitsha: str=str()
) -> None:
    for dir in os.listdir(root_dir):
        build_an_image(
            f'{root_dir}/{dir}',
            env,
            aws_acct_id,
            gitsha
        )


if __name__ == '__main__':

    pass
