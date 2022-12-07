#!/usr/bin/env python


class TagPath:

    ecr_repo = str()
    git_sha = str()
    gcp_proj = str()
    img_tag = str()
    reg = str()
    tag_path = str()    

    def ecr_path(self):   
        return (
            f'{self.reg}/{self.ecr_repo}:{self.img_tag}-{self.git_sha[0:10]}' 
            if self.git_sha 
            else f'{self.reg}/{self.ecr_repo}:{self.img_tag}'
        )

    def gcr_path(self):   
        return (
            f'{self.reg}/{self.gcp_proj}/{self.img_tag}-{self.git_sha[0:10]}' 
            if self.git_sha 
            else f'{self.reg}/{self.gcp_proj}/{self.img_tag}'
        )

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

    def image_tag(self, val: str):
        self.img_tag = val
        return self
