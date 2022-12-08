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


def dockerfile(base_img_url: str):
    with open(f'{os.getcwd()}/Dockerfile') as fin:
        data = ''
        for line in fin.readlines():
            if line.find('FROM') != -1:
                line = line.replace('{}', base_img_url)
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


def build_old(
    tag: str, 
    build_path: str, 
    aws_id: str=str(),
    base_img_ver: str=str(), 
    gitsha: str=str()
) -> bool:
    comm=[
        'docker', 'build', build_path, '--file', f'{build_path}/Dockerfile', 
        '--tag', 
        tag,
    ]
    if base_img_ver:
        comm.extend([
        '--build-arg',
        f'_BASE_IMG_VERSION_={base_img_ver}',
        ])
    if aws_id:
        comm.extend([
        '--build-arg', 
        f'_AWS_ACCT_ID_={aws_id}',
        ])        
    if gitsha:
        comm.extend([
        '--build-arg', 
        f'_GITHUB_SHA_=-{gitsha}',
        ])
    return popen(
        comm
    )


def build(
    registry: str,
    repo: str,
    tag: str, 
    aws_id: str=str(),
    base_img_name: str=str(),
    base_img_ver: str=str(),
    proj_id: str=str(), 
    gitsha: str=str()
) -> tuple:
    based = f'{base_img_name}-{base_img_ver}'
    bargs = dict()
    if aws_id:
        base_img_url = f'{aws_id}.{registry}/{repo}:{based}'
        bargs.update(dict(_AWS_ACCT_ID_=aws_id, ))
    if base_img_ver:
        bargs.update(dict(_BASE_IMG_VERSION_=base_img_ver, ))
    if gitsha:
        bargs.update(dict(_GTIHUB_SHA_=gitsha, ))
    kwargs = dict(
        buildargs=bargs, 
        fileobj=dockerfile(base_img_url), 
        tag=tag, 
    )
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
    proj_id: str = str(),
    base_img_name: str=str(), 
    base_img_ver: str=str(), 
    gitsha: str=str(),
    registry: str=str(),
    repo: str=str(),
) -> None:
    result = push(
        built=build(
            aws_id=aws_id if aws_id else str(),
            base_img_name=base_img_name if base_img_name else str(),
            base_img_ver=base_img_ver if base_img_ver else str(),
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

    def base(img_tag: str) -> None:
        dockerit(
            tag=tagurler(img_tag, **tag_kwargs)
        )

    def prod(
        img_tag: str, 
        build_img: bool,     
        base_img_name: str=str(),
        base_img_ver: str=str(), 
    ) -> None:
        nodice = 'Same version...  Not dockering it...'        
        if up_version(img_tag, list_images(img_tag)):
            if  build_img:
                dockerit(
                    tag=tagurler(img_tag, **tag_kwargs),
                    base_img_name=base_img_name,
                    base_img_ver=base_img_ver,
                    **dockerit_kwargs
                )
            else:
                print(NOBUILD)
        else:
            print(nodice)

    def dev(
        img_tag: str, 
        build_img: bool,     
        base_img_name: str=str(),
        base_img_ver: str=str(), 
    ) -> None:
        if build_img:
            dockerit(
                tag=tagurler(img_tag, **tag_kwargs),
                base_img_name=base_img_name,
                base_img_ver=base_img_ver,
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
            base_img_name=conf.get('base_img_name'),
            base_img_ver=conf.get('base_img_ver')
        )


def build_baseimage(
    img_tag: str,
    registry: str,
    repo: str,
    ver: str,
    env: str=str(),
    github_sha: str=str(),
    *args
) -> None:
    build_steps(registry, repo, github_sha)['base'](
        f'{img_tag}_{env}-{ver}' if env else f'{img_tag}-{ver}'
    )


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
