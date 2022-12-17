#!/usr/bin/env python

import os
from copy import deepcopy


class TagURL:

    dockerhub_nspace = str()
    git_sha = str()
    gcp_proj = str()
    img_tag = str()
    reg = str()
    repo = str()
    tag_path = str()    

    def dockerhub_url(self) -> str:   
        base = f'{self.reg}/{self.repo}/{self.dockerhub_nspace}'
        base = f'{base}:{self.img_tag}'
        return self._handle_gitsha(base)

    def ecr_url(self) -> str:   
        base = f'{self.reg}/{self.repo}:{self.img_tag}'
        return self._handle_gitsha(base)
    
    def gar_url(self) -> str:   
        base = f'{self.reg}/{self.gcp_proj}/{self.repo}/{self.img_tag}'
        return self._handle_gitsha(base)

    def _handle_gitsha(self, base: str) -> str:
        return (
            f'{base}-{self.git_sha[0:10]}' 
            if self.git_sha 
            else base
        )

    def container_repo(self, val: str):
        self.repo = val
        return self

    def container_registry(self, val: str):
        self.reg = val
        return self
    
    def dockerhub_namespace(self, val: str):
        self.dockerhub_nspace = val
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
    gcp_proj_id: str=str(),
    gitsha: str=str(),
    namespace: str=str(),
    repo: str=str()
) -> str:
    url = deepcopy(
        TagURL().container_registry(registry).container_repo(repo)
        .image_tag(img_tag)
        .gitsha(gitsha)
    )
    if gcp_proj_id:
        return url.gcp_proj_id(gcp_proj_id).gar_url()
    if registry.find('ecr') != '-1':
        return url.ecr_url()
    return (
        url
        .dockerhub_namespace(namespace)
        .dockerhub_url()
    )
