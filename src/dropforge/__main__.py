#!/usr/bin/env python

import argparse
import os
import pkgutil

from os.path import expanduser
from pathlib import Path

from dropforge.build import build_a_baseimage


def copy_basefiles(proj_loc: str) -> None:
    whence = 'basedonfiles'
    files = ['forge.yaml', 'requirements.txt', 'setup.py']
    for f in files:
        goods = (
            pkgutil
            .get_data(__name__, f'{whence}/{f}')
            .decode()
        )
        with open(f'{proj_loc}/{f}', 'w') as fout:
            fout.write(goods)


def project_location(name: str, where: str) -> str:
    loc = where.replace('~', expanduser('~'))
    return f'{loc}/{name}'


def scaffold(proj_loc: str) -> None:
    subpaths, kwargs = dict(workspace='some.py', ), dict(exist_ok=False)
    os.makedirs(proj_loc, **kwargs)
    for p, f in subpaths.items():
        sub = f'{proj_loc}/{p}'
        os.makedirs(sub, **kwargs)        
        filer = Path(f'{sub}/{f}')
        filer.touch(**kwargs)


def baseimage(args: argparse) -> None:
    build_a_baseimage(
        dir=args.project_dir.replace('~', expanduser('~')),
        env=args.env,
        ecr_reg_full_url=args.ecr_reg_full_url,
        gitsha=args.gitsha
    )


def makeitso(args: argparse) -> None:
    if args:
        where, name  = args.localrepo_dir, args.name
        proj_loc = project_location(name=name, where=where)
        scaffold(proj_loc)
        copy_basefiles(proj_loc)


def args(what: str) -> list:
    baseimg = [
        '--project-dir', 
        '--env',
        '--ecr-reg-full-url',
        '--gitsha',
    ]
    inits = [
        '--localrepo-dir', 
        '--name', 
    ]
    return dict(
        baseimage=baseimg,
        init=inits, 
    )[what]


OPTIONALS = {
    '--ecr-reg-full-url',
    '--gitsha',
}
WHATS = dict(
    baseimage=baseimage,
    init=makeitso, 
)


def iter_subpars(subpars: argparse) -> None:
    subparsers = {k: None for k in WHATS}
    for what in WHATS:
        subparsers[what] = subpars.add_parser(what)
        for arg in args(what):
            req = True
            if arg in OPTIONALS:
                req = False
            subparsers[what] \
                .add_argument(
                    arg,
                    required=req
                )
        subparsers[what] \
            .set_defaults(
                func=WHATS[what]
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    subpars = parser.add_subparsers()
    iter_subpars(subpars)
    args = parser.parse_args()
    if not args.__dict__:
        print('This won\'t do anthing...')
    else:
        args.func(args)


if __name__ == '__main__':

    main()
