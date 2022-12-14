#!/usr/bin/env python

import json
import os
import yaml

from collections import namedtuple
from copy import deepcopy
from distutils.version import StrictVersion
from io import BytesIO
from json.decoder import JSONDecodeError
from pathlib import Path
from subprocess import Popen, CalledProcessError

import docker
from docker import APIClient
from semantic_version import Version as semver

from forgedrop.objs import tagurler


Forger = namedtuple(
    'Forger', (
        'base_img_name_used',
        'base_img_ver_used',
        'build_it',
        'img_name',
        'img_ver',
        'registry',
        'repo',
        'tag',
    )
)


DFILE = 'Dockerfile'
FORGE = 'forge.yaml'
NOBUILD = 'Not building the image...'
SPLITS = '-'


def basedonfiles():
    path = str(Path(__file__)).split('/')
    path.pop()
    return f'{"/".join(path)}/pckgdata'


def dockerfile_child(base_img_url: str, dir: str) -> BytesIO:
    with open(f'{basedonfiles()}/{DFILE}') as fin:
        data = ''
        for line in fin.readlines(): 
            if line.find('FROM') != -1:
                line = line.replace('{}', base_img_url)
            data += line
        with open(
            f'{dir}/{DFILE}', 'w') as fout:
            fout.write(data)
    return BytesIO(
        data.encode('utf-8')
    )


def dockerfile_base(dir: str, img_name: str) -> BytesIO:
    with open(f'{basedonfiles()}/{DFILE}_Based') as fin:
        data = ''
        for line in fin.readlines():              
            if line.find('WORKDIR') != -1:
                line = line.replace(
                    '{}', 
                    img_name
                )
            if line.find('COPY') != -1:
                line = line \
                .replace(
                    '{}', 
                    img_name
                )  
            data += line
        with open(
            f'{dir}/{DFILE}', 'w') as fout:
            fout.write(data)
    return BytesIO(
        data.encode('utf-8')
    )   


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


def build(
    dir: str,
    registry: str,
    repo: str,
    tag: str, 
    aws_id: str=str(),
    base_img_name_used: str=str(),
    base_img_ver_used: str=str(), 
    gitsha: str=str(),
    img_name: str=str()
) -> tuple:

    based, bargs = f'{base_img_name_used}-{base_img_ver_used}', dict()
    upd = dict(
        a=dict(_AWS_ACCT_ID_=aws_id, ),
        b=dict(_BASE_IMG_VERSION_=base_img_ver_used, ),
        c=dict(_GTIHUB_SHA_=gitsha, ),
    )

    def dockerfiler(base_img_used_url: str) -> bytes:
        return (
            dockerfile_child(dir, base_img_used_url)
            if base_img_name_used 
            else dockerfile_base(
                dir, 
                img_name
            )
        )

    kwargs = dict(path=dir, tag=tag, )

    if aws_id:
        base_img_used_url = \
            f'{aws_id}.{registry}/{repo}:{based}'
        bargs.update(upd['a'])
    if base_img_ver_used:
        bargs.update(upd['b'])
    if gitsha:
        bargs.update(upd['c'])
    if bargs:
        kwargs.update(
            dict(
                buildargs=bargs, 
            )
        )
    
    dockerfiler(base_img_used_url)
    if _build(**kwargs):
        os.remove(f'{dir}/Dockerfile')
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
    aws_id: str=str(),
    base_img_name_used: str=str(),
    base_img_ver_used: str=str(), 
    gitsha: str=str(),
    img_name: str=str(),
    registry: str=str(),
    repo: str=str(),
) -> None:
    result = push(
        built=build(
            dir,
            aws_id=aws_id if aws_id else str(),
            base_img_name_used=base_img_name_used if base_img_name_used else str(),
            base_img_ver_used=base_img_ver_used if base_img_ver_used else str(),
            gitsha=gitsha,
            img_name=img_name,
            registry=registry,
            repo=repo,
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
    return registry.split('.')[0] if registry.find('erc') != - 1 else str()


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

    aws_id = check_aws_id(registry)
    tag_kwargs = dict(repo=repo, registry=registry, gitsha=gitsha, )
    dockerit_kwargs = deepcopy(tag_kwargs)
    dockerit_kwargs.pop('gitsha')
    dockerit_kwargs.update(dict(dir=dir, aws_id=aws_id, ))

    def base(img_name: str, img_tag: str) -> None:
        dockerit(
            dir,
            tag=tagurler(img_tag, **tag_kwargs), 
            img_name=img_name
        )

    def prod(
        img_tag: str, 
        build_it: bool,     
        base_img_name_used: str=str(),
        base_img_ver_used: str=str(), 
    ) -> None:
        nodice = 'Same version...  Not dockering it...'        
        if up_version(img_tag, list_images(img_tag)):
            if build_it:
                dockerit(
                    tag=tagurler(img_tag, **tag_kwargs),
                    base_img_name_used=base_img_name_used,
                    base_img_ver_used=base_img_ver_used,
                    **dockerit_kwargs
                )
            else:
                print(NOBUILD)
        else:
            print(nodice)

    def devqa(
        img_tag: str, 
        build_it: bool,     
        base_img_name_used: str=str(),
        base_img_ver_used: str=str(), 
    ) -> None:
        if build_it:
            dockerit(
                tag=tagurler(img_tag, **tag_kwargs),
                base_img_name_used=base_img_name_used,
                base_img_ver_used=base_img_ver_used,
                gitsha=gitsha[0:10],
                **dockerit_kwargs
            )
        else:
            print(NOBUILD)

    return dict(
        base=base,
        dev=devqa,
        prod=prod,
        qa=devqa,
    )


def proc_conf(
    path: str, 
    env: str, 
    ecr_reg_full_url: str=str(),
) -> None:
    with open(path) as forge:
        conf = yaml.safe_load(forge)
        img_name, ver = conf['image_name'], conf['image_version']  
        registry = ecr_reg_full_url if ecr_reg_full_url else conf['container_registry']
        repo = conf.get('container_repo')        
        if not repo:
            repo = conf.get('gcp_project_id')
        return Forger(
            base_img_name_used=conf.get('base_image_name_used'),
            base_img_ver_used=conf.get('base_image_version_used'),
            build_it=conf.get(f'build_deploy_{env}'),
            img_name=img_name,
            img_ver=ver,
            registry=registry,
            repo=repo,
            tag=f'{img_name}-{ver}'
        )


def build_a_baseimage(
    dir: str,
    env: str,
    ecr_reg_full_url: str=str(),
    gitsha: str=str(),
    *args
) -> None:
    confs = proc_conf(f'{dir}/{FORGE}', env, ecr_reg_full_url)
    build_steps(
        dir,
        confs.registry, 
        confs.repo, 
        gitsha
    )['base'](
        confs.img_name, 
        confs.tag
    )


def build_an_image(
    dir: str,
    env: str,
    ecr_reg_full_url: str=str(),
    gitsha: str=str(),
) -> None:
    confs = proc_conf(f'{dir}/{FORGE}', env, ecr_reg_full_url)
    build_steps(
        dir,
        confs.registry, 
        confs.repo, 
        gitsha
    )[env]( 
        confs.tag,
        confs.build_it,
        confs.base_img_name_used,
        confs.base_img_ver_used
    )


def build_images(
    env: str,
    registry: str,
    repo: str,
    root: str,
    github_sha: str
) -> None:
    for dir in os.listdir(root):
        build_an_image(
            f'{root}/{dir}',
            env,
            registry,
            repo,
            github_sha
        )


if __name__ == '__main__':

    pass
