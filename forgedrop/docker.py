#!/usr/bin/env python

from pathlib import Path
import yaml


DFILE = 'Dockerfile'


def basedonfiles():
    path = str(Path(__file__)).split('/')
    path.pop()
    return f'{"/".join(path)}/pckgdata'


def base_img(dir):
    with open(f'{dir}/forge.yaml') as forge:
        conf = yaml.safe_load(forge)
        return conf['base_image_used']


def dockerfile(dir: str) -> None:
    with open(f'{basedonfiles()}/{DFILE}') as fin:
        data = ''
        for line in fin.readlines(): 
            if line.find('FROM') != -1:
                line = line.replace('{}', base_img(dir))
            data += line
        with open(
            f'{dir}/{DFILE}', 'w'
        ) as fout:
            fout.write(data)
