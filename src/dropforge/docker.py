#!/usr/bin/env python

import os
import yaml

from collections import namedtuple
from distutils.version import StrictVersion
from importlib.metadata import version
from subprocess import Popen, CalledProcessError

from semantic_version import Version as semver
from regs import ecr_img_list, SPLITS


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
        f'_VERSION_={version("")}',
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


def common_steps(registry: str, repo: str, gitsha: str) -> dict:

    aws_id = registry.split('.') if registry.find('erc') != - 1 else str()

    def registries(reg: str) -> callable:
        if aws_id:
            return ecr_img_list(
                aws_id,
                registry, 
                repo
            )

    def up_version(img_tag: str, registry: str) -> bool:
        name, curr_ver = img_tag.split(SPLITS)
        tags = registries(registry)
        if tags:
            semvers = list(
                t.semver for t in tags if t.name == name
            )
            try:
                latest_ver = sorted(
                    semvers,
                    key=StrictVersion
                )[-1]
            except IndexError:
                latest_ver = '0.0.0'
        else:
            latest_ver = '0.0.0'
        if semver(curr_ver) == semver('0.0.0'):
            return True
        if semver(curr_ver) > semver(latest_ver):
            return True
        return False

    def base(img_tag: str) -> None:
        dockerit(
            f'{registry}/{repo}:{img_tag}-{gitsha[0:10]}' 
            if gitsha 
            else f'{registry}/{repo}:{img_tag}',
            '.',
            aws_id
        )

    def prod(img_tag: str, build_path: str, *args) -> None:
        tag = f'{registry}/{repo}:{img_tag}'
        nodice = 'Same version...  Not dockering it...'
        if up_version(img_tag, registry):
            dockerit(
                tag,
                build_path,
                aws_id
            )
        else:
            print(nodice)

    def dev_qa(img_tag: str, build_path: str, build_img: bool) -> None:
        no_build = 'Not building the image...'
        if build_img:
            tag = f'{registry}/{repo}:{img_tag}-{gitsha[0:10]}'
            dockerit(
                tag,
                build_path,
                aws_id,
                gitsha[0:10]
            )
        else:
            print(no_build)

    return dict(
        base=base,
        dev=dev_qa,
        prod=prod,
        qa=dev_qa,
    )


def proc_forgeconf(
    path: str,
    build_path: str,
    run_env: callable,
    env: str
) -> None:
    with open(path) as hawk:
        conf = yaml.safe_load(hawk)
        run_env[env](
            conf['image_tag'],
            build_path,
            conf.get(f'build_deploy_{env}')
        )


def build_baseimage(
    img_tag: str,
    registry: str,
    repo: str,
    ver: str,
    env: str = str(),
    github_sha: str = str(),
    *args
) -> None:
    common_steps(registry, repo, github_sha)['base'](
        f'{img_tag}_{env}-{ver}' if env else f'{img_tag}-{ver}'
    )


def build_image(
    env: str,
    registry: str,
    repo: str,
    root: str,
    github_sha: str
) -> None:
    for p in os.listdir(root):
        build_path = f'{root}/{p}'
        proc_forgeconf(
            path=f'{build_path}/forge.yaml',
            build_path=build_path,
            run_env=common_steps(
                registry,
                repo,
                github_sha
            ),
            env=env
        )

