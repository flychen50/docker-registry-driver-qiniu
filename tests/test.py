# -*- coding: utf-8 -*-

import logging

from docker_registry import testing

logger = logging.getLogger(__name__)


class TestQuery(testing.Query):
    def __init__(self):
        self.scheme = 'qiniustorage'

class TestDriver(testing.Driver):
    def __init__(self):
        self.scheme = 'qiniustorage'
        self.path = ''
        self.config = testing.Config({'qiniu_bucket':'docker-registry-qiniu','qiniu_accesskey':'V-Ua6icAAmPxxPhrTWIGoYFPHgz-aIiH7GCZDuJr','qiniu_secretkey':'SAx_l3aNFa8rcx-yfi_DTd_sOq8Iz_H8n5Zn6tVW','qiniu_domain':'docker-registry-qiniu.qiniudn.com'})