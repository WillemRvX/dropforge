#!/usr/bin/env python


def tag_maker(img_tag: str, proj_id: str=str()) -> str:
    if aws_id:
        return (
            f'{registry}/{repo}:{img_tag}-{gitsha[0:10]}' 
            if gitsha 
            else f'{registry}/{repo}:{img_tag}'
        )
    if gcped:
        return (
            f'{registry}/{proj_id}/{img_tag}-{gitsha[0:10]}' 
            if gitsha 
            else f'{registry}/{proj_id}/{img_tag}'
        )


class TagPath:

    ecr_repo = str()
    git_sha = str()
    gcp_proj = str()
    reg = str()
    tag_path = str()    

    def aws_ecr_repo(self, val: str):
        self.ecr_repo = val
        return self

    def container_registry(self, val: str):
        self.reg = val
        return self
    
    def gcp_proj_id(self, val: str):
        self.gcp_proj = val
        return self

    def gitsha(self, val: str):
        self.git_sha = val        
        return self