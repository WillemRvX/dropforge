#!/usr/bin/env python

import os
import yaml

from distutils.version import StrictVersion
from importlib.metadata import version
from subprocess import Popen, CalledProcessError

import docker
from semantic_version import Version as semver
from dropforge.objs import tagurler


FORGE, SPLITS = 'forge.yaml', '-'


def popen(comm: list) -> bool:
    err_mssg = 'Something gone wrong!'
    try:
        proc = Popen(comm, shell=False)
        proc.communicate()
        return True
    except CalledProcessError:
        print(err_mssg)
        return False


def build(tag: str, build_path: str, aws_id: str=str(), gitsha: str=str()) -> bool:
    comm=[
        'docker', 'build', build_path, 
        '--file', f'{build_path}/Dockerfile', 
        '--tag', tag,
    ]
    comm.extend([
        '--build-arg',
        f'_BASE_IMG_VERSION_={version("")}',
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


def dockerit(tag: str, build_path: str, aws_id: str=str(), gitsha: str=str()) -> None:
    result = push(
        built=build(
            tag,
            build_path,
            aws_id if aws_id else str(),
            gitsha
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


def build_steps(registry: str, repo: str, gitsha: str=str()) -> dict:

    aws_id = registry.split('.')[0] if registry.find('erc') != - 1 else str()
    kwargs = dict(repo=repo, registry=registry, gitsha=gitsha, )

    def base(img_tag: str) -> None:
        dockerit(
            tagurler(img_tag, **kwargs),
            '.',
            aws_id
        )

    def prod(img_tag: str, build_path: str, *args) -> None:
        nodice = 'Same version...  Not dockering it...'        
        if up_version(img_tag, list_images(img_tag)):
            dockerit(
                tagurler(img_tag, **kwargs),
                build_path,
                aws_id
            )
        else:
            print(nodice)

    def dev(img_tag: str, build_path: str, build_img: bool) -> None:
        no_build = 'Not building the image...'
        if build_img:
            dockerit(
                tagurler(img_tag, **kwargs),
                build_path,
                aws_id,
                gitsha[0:10]
            )
        else:
            print(no_build)

    return dict(
        base=base,
        dev=dev,
        prod=prod,
        qa=dev,
    )


def proc_conf(
    path: str,
    buildpath: str,
    run_env: callable,
    env: str
) -> None:
    with open(path) as forge:
        conf = yaml.safe_load(forge)
        run_env[env](
            conf['image_tag'],
            buildpath,
            conf.get(f'build_deploy_{env}')
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
