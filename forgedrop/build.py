#!/usr/bin/env python

import json
import os
import yaml

from collections import namedtuple
from copy import deepcopy
from distutils.version import StrictVersion
from json.decoder import JSONDecodeError
from subprocess import Popen, CalledProcessError

import docker
from docker import APIClient
from semantic_version import Version as semver

from forgedrop.objs import tagurler


Forger = namedtuple(
    'Forger', (
        'base_img_used',
        'build_it',
        'registry',
        'repo',
        'tag',
    )
)


FORGE = 'forge.yaml'
NOBUILD = 'Not building the image...'
SPLITS = '-'


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
    cli = APIClient(base_url='unix://var/run/docker.sock')
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


def build(dir: str, tag: str, gitsha: str=str()) -> bool:
    bargs, kwargs = dict(), dict(path=dir, tag=tag, )
    if gitsha:
        bargs.update(
            dict(
                _GTISHA_=gitsha, 
            )
        )
    if bargs:
        kwargs.update(
            dict(
                buildargs=bargs, 
            )
        )
    if _build(**kwargs):
        return True
    else:
        return False


def list_images(image_tag: str) -> list:
    kwargs = dict(filters=dict(reference=f'{image_tag}*'))
    return list(
        img.tags[-1].replace('latest', '').replace(':', '') for img in
        docker
        .from_env()
        .images
        .list(**kwargs)
        if img.tags[-1].find('latest') != '-1'
    )


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
    dir: str,
    tag: str, 
    gitsha: str=str(),
) -> None:
    result = push(
        built = build(
            dir,
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


def check_aws_id(registry: str) -> str:
    return registry.split('.')[0] if registry.find('ecr') != - 1 else str()


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
    dir: str,
    registry: str, 
    repo: str, 
    gitsha: str=str()
) -> dict:

    tag_kwargs = dict(repo=repo, registry=registry, gitsha=gitsha, )
    dockerit_kwargs = deepcopy(tag_kwargs)
    dockerit_kwargs.pop('gitsha')
    dockerit_kwargs.pop('registry')
    dockerit_kwargs.pop('repo')
    dockerit_kwargs.update(dict(dir=dir, ))

    def prod(
        img_tag: str, 
        build_it: bool,     
    ) -> None:
        nodice = 'Same version...  Not dockering it...'        
        if up_version(img_tag, list_images(img_tag)):
            if build_it:
                dockerit(
                    tag=tagurler(img_tag, **tag_kwargs),
                    **dockerit_kwargs
                )
            else:
                print(NOBUILD)
        else:
            print(nodice)

    def devqa(
        img_tag: str, 
        build_it: bool,     
    ) -> None:
        if build_it:
            dockerit(
                tag=tagurler(img_tag, **tag_kwargs),
                gitsha=gitsha[0:10],
                **dockerit_kwargs
            )
        else:
            print(NOBUILD)

    return dict(
        dev=devqa,
        prod=prod,
        qa=devqa,
    )


def proc_conf(path: str, env: str) -> None:
    with open(path) as forge:
        conf = yaml.safe_load(forge)
        img_name, registry = conf['image_name'], conf['container_registry']
        repo = conf.get('container_repo')        
        if not repo:
            repo = conf.get('gcp_project_id')
        return Forger(
            base_img_used=conf.get('base_image_used'),
            build_it=conf.get(f'build_{env}'),
            registry=registry,
            repo=repo,
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
        dir,
        f'{aws_acct_id}.{confs.registry}' 
            if aws_acct_id 
            else confs.registry, 
        confs.repo, 
        gitsha
    )[env]( 
        confs.tag,
        confs.build_it,
    )


def build_images(
    root_dir: str,
    env: str,
    aws_acct_id: str=str(),
    github_sha: str=str()
) -> None:
    for dir in os.listdir(root_dir):
        build_an_image(
            f'{root_dir}/{dir}',
            env,
            aws_acct_id,
            github_sha
        )


if __name__ == '__main__':

    pass
