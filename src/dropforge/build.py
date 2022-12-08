#!/usr/bin/env python

import os
import yaml

from distutils.version import StrictVersion
from io import StringIO
from subprocess import Popen, CalledProcessError

import docker
from semantic_version import Version as semver
from dropforge.objs import tagurler


FORGE = 'forge.yaml'
NOBUILD = 'Not building the image...'
SPLITS = '-'


def dockerfile(base_img_url: str) -> StringIO:
    with open(f'{os.getcwd()}/Dockerfile') as fin:
        data = ''
        for line in fin.readlines():
            if line.find('FROM') != -1:
                line = line.replace('{}', base_img_url)
            data += line
    return StringIO(data)


def dockerfile_base(base_img_name: str) -> StringIO:
    with open(f'{os.getcwd()}/Dockerfile_Base') as fin:
        data = ''
        for line in fin.readlines():
            if line.find('WORKDIR') != -1:
                line = line.replace(
                    '{}', 
                    base_img_name
                )
            if line.find('COPY') != -1:
                line = line.replace(
                    '{}', 
                    base_img_name
                )
            data += line
    return StringIO(data)


def popen(comm: list) -> bool:
    err_mssg = 'Something gone wrong!'
    try:
        proc = Popen(comm, shell=False)
        proc.communicate()
        return True
    except CalledProcessError:
        print(err_mssg)
        return False


def build(
    registry: str,
    repo: str,
    tag: str, 
    aws_id: str=str(),
    base_img_name_used: str=str(),
    base_img_ver_used: str=str(), 
    gitsha: str=str()
) -> tuple:
    based = f'{base_img_name_used}-{base_img_ver_used}'
    bargs = dict()
    if aws_id:
        base_img_used_url = f'{aws_id}.{registry}/{repo}:{based}'
        bargs.update(dict(_AWS_ACCT_ID_=aws_id, ))
    if base_img_ver_used:
        bargs.update(dict(_BASE_IMG_VERSION_=base_img_ver_used, ))
    if gitsha:
        bargs.update(dict(_GTIHUB_SHA_=gitsha, ))
    kwargs = dict(
        fileobj=dockerfile(base_img_used_url), 
        tag=tag, 
    )
    if bargs:
        kwargs.update(dict(buildargs=bargs, ))
    return (
        docker
        .from_env()
        .images
        .build(**kwargs)
    )


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
    tag: str, 
    aws_id: str=str(),
    base_img_name_used: str=str(),
    base_img_ver_used: str=str(), 
    gitsha: str=str(),
    registry: str=str(),
    repo: str=str(),
) -> None:
    result = push(
        built=build(
            aws_id=aws_id if aws_id else str(),
            base_img_name_used=base_img_name_used if base_img_name_used else str(),
            base_img_ver_used=base_img_ver_used if base_img_ver_used else str(),
            gitsha=gitsha,
            tag=tag,
            registry=registry,
            repo=repo
        ),
        tag=tag
    )
    if result:
        print(
            f'{tag}'
            ' built & pushed!'
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
    registry: str, 
    repo: str, 
    gitsha: str=str()
) -> dict:

    aws_id = registry.split('.')[0] if registry.find('erc') != - 1 else str()
    tag_kwargs = dict(repo=repo, registry=registry, gitsha=gitsha, )
    dockerit_kwargs = tag_kwargs
    dockerit_kwargs.pop('gitsha')
    dockerit_kwargs.update(dict(aws_id=aws_id, ))

    def base(
        img_tag: str, 
    ) -> None:
        dockerit(
            tag=tagurler(img_tag, **tag_kwargs),
        )

    def prod(
        img_tag: str, 
        build_img: bool,     
        base_img_name_used: str=str(),
        base_img_ver_used: str=str(), 
    ) -> None:
        nodice = 'Same version...  Not dockering it...'        
        if up_version(img_tag, list_images(img_tag)):
            if  build_img:
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

    def dev(
        img_tag: str, 
        build_img: bool,     
        base_img_name_used: str=str(),
        base_img_ver_used: str=str(), 
    ) -> None:
        if build_img:
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
        dev=dev,
        prod=prod,
        qa=dev,
    )


def proc_conf(
    path: str,
    run_env: callable,
    env: str
) -> None:
    with open(path) as forge:
        conf = yaml.safe_load(forge)
        run_env[env](
            img_tag=conf['image_name'],
            build_img=conf.get(f'build_deploy_{env}'),
            base_img_name_used=conf.get('base_image_name_used'),
            base_img_ver_used=conf.get('base_image_version_used')
        )


def build_baseimage(
    dir: str,
    env: str=str(),
    github_sha: str=str(),
    *args
) -> None:
    path = f'{dir}/{FORGE}'
    with open(path) as forge:
        conf = yaml.safe_load(forge)
        registry, repo = conf['container_registry'], conf.get('container_repo')        
        img_tag, ver = conf['image_name'], conf['image_ver']
        tag = f'{img_tag}_{env}-{ver}' if env else f'{img_tag}-{ver}'
        if not repo:
            repo = conf.get('gcp_project_id')
        build_steps(
            registry, 
            repo, 
            github_sha
        )['base'](tag)


def build_image(
    dir: str,
    env: str,
    registry: str,
    repo: str,
    github_sha: str
) -> None:
    proc_conf(
        path=f'{dir}/{FORGE}',
        buildpath=dir,
        run_env=build_steps(
            registry,
            repo,
            github_sha
        ),
        env=env
    )


def build_images(
    env: str,
    registry: str,
    repo: str,
    root: str,
    github_sha: str
) -> None:
    for dir in os.listdir(root):
        build_image(
            f'{root}/{dir}',
            env,
            registry,
            repo,
            github_sha
        )


if __name__ == '__main__':

    pass
