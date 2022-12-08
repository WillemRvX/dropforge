#!/usr/bin/env python

import os
from copy import deepcopy


class TagURL:

    dockerhub_nspace = str()
    dockerhub_repository = str()
    ecr_repo = str()
    git_sha = str()
    gcp_proj = str()
    img_tag = str()
    reg = str()
    tag_path = str()    

    def dockerhub_url(self) -> str:   
        base = f'{self.reg}/{self.dockerhub_repository}/{self.dockerhub_nspace}'
        base = f'{base}:{self.img_tag}'
        return (
            f'{base}-{self.git_sha[0:10]}' 
            if self.git_sha 
            else f'{base}'
        )

    def ecr_url(self) -> str:   
        base = f'{self.reg}/{self.ecr_repo}:{self.img_tag}'
        return (
            f'{base}-{self.git_sha[0:10]}' 
            if self.git_sha 
            else base
        )

    def gcr_url(self) -> str:   
        base = f'{self.reg}/{self.gcp_proj}/{self.img_tag}'
        return (
            f'{base}-{self.git_sha[0:10]}' 
            if self.git_sha 
            else base
        )

    def aws_ecr_repo(self, val: str):
        self.ecr_repo = val
        return self

    def container_registry(self, val: str):
        self.reg = val
        return self
    
    def dockerhub_namespace(self, val: str):
        self.dockerhub_nspace = val
        return self

    def dockerhub_repo(self, val: str):
        self.dockerhub_repository = val
        return self

    def gcp_proj_id(self, val: str):
        self.gcp_proj = val
        return self

    def gitsha(self, val: str):
        self.git_sha = val        
        return self

    def image_tag(self, val: str):
        self.img_tag = val
        return self


def tagurler(
    img_tag: str,  
    registry: str, 
    gitsha: str,
    gcp_proj_id: str=str(),
    namespace: str=str(),
    repo: str=str()
) -> str:
    url = deepcopy(
        TagURL().container_registry(registry).image_tag(img_tag)
        .gitsha(gitsha)
    )
    if registry.find('ecr') != '-1':
        return (
            url
            .aws_ecr_repo(repo)
            .ecr_url()
        )
    elif registry.find('gcr') != '-1':
        return (
            url
            .gcp_proj_id(gcp_proj_id)
            .gcr_url()
        )
    else:
        return (
            url
            .dockerhub_repo(repo)
            .dockerhub_namespace(
                namespace
            )
            .dockerhub_url()
        )
