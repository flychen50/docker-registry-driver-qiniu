import qiniu.conf
import qiniu.rs
import qiniu.rsf
import qiniu.io

from docker_registry.core import driver
from docker_registry.core import exceptions
from docker_registry.core import lru
import StringIO
import tempfile
import os
import urllib

class Storage(driver.Base):

    def __init__(self, path=None, config=None):
        qiniu.conf.ACCESS_KEY = config.qiniu_accesskey
        qiniu.conf.SECRET_KEY = config.qiniu_secretkey

        self._bucket = config.qiniu_bucket
        self._domain = config.qiniu_domain
        
        self._putpolicy = qiniu.rs.PutPolicy(config.bucket)
        self._getpolicy = qiniu.rs.GetPolicy()
        self._uptoken = self._putpolicy.token()
        
    def _init_path(self, path=None):
        if path:
            if path.startswith('/'):
                path = path[1:]
            if path.endswith('/'):
                path = path[:-1]
        return path

    def content_redirect_url(self, path):
        path = self._init_path(path)
        base_url = qiniu.rs.make_base_url(self._domain, path)
        return self._getpolicy.make_request(base_url)

    @lru.get
    def get_content(self, path):
        path = self._init_path(path)

        output = StringIO.StringIO()
        try:
            for buf in self.get_store(path, self.buffer_size):
                output.write(buf)
            return output.getvalue()
        finally:
            output.close()

    def get_store(self, path, chunk_size=None):
        try:
            base_url = qiniu.rs.make_base_url(self._domain, path)
            get_url = self._getpolicy.make_request(base_url)
            response = urllib.Request.urlopen(get_url)
        except KeyNotFound:
            raise exceptions.FileNotFoundError('%s is not there' % path)

        try:
            while True:
                chunk = response.read(chunk_size)
                if not chunk: break
                yield chunk
        except:
            raise IOError("Could not get content: %s" % path)

    @lru.set
    def put_content(self, path, content):
        path = self._init_path(path)
        self.put_store(path, content)
        return path

    def put_store(self, path, content, chunk=None, length=None):
        headers = {}
        if length is not None:
            headers['Content-Length'] = str(length)

        try:
            ret, err = qiniu.io.put(self._uptoken, path, content, None)
            if err is not None:
                raise IOError("Put content %s err: %s" % (path, err))
        except Exception:
            raise IOError("Could not put content: %s" % path)

    def stream_read(self, path, bytes_range=None):
        path = self._init_path(path)
        for buf in self.get_store(path, self.buffer_size):
            yield buf

    def stream_write(self, path, fp):
        path = self._init_path(path)

        if hasattr(fp, '__len__'):
            length = len(fp)
            self.put_store(path, fp, chunk=self.buffer_size, length=length)
        else:
            tmp_file = tempfile.mktemp()
            try:
                with open(tmp_file, 'w') as f:
                    while True:
                        buf = fp.read(self.buffer_size)
                        if not buf: break
                        f.write(buf)

                with open(tmp_file, 'r') as f:
                    self.put_store(path, f, chunk=self.buffer_size)
            except:
                raise
            finally:
                if os.path.exists(tmp_file):
                    os.remove(tmp_file)

    def head_store(self, path):
        ret, err = qiniu.rs.Client().stat(self._bucket, path)
        if err is not None:
            raise IOError("Stat path %s err: %s" % (path, err))
        return ret

    def list_directory(self, path=None):
        try:
            path = self._init_path(path)
            rs = qiniu.rsf.Client()
            marker = None
            err = None
            counter = 0
            
            while err is None:
                ret, err = rs.list_prefix(bucket_name, prefix=path, marker=marker)
                marker = ret.get('marker', None)
                for item in ret['items']:
                    counter += 1
                    yield item[0]
            
            if err is not qiniu.rsf.EOF:
                raise IOError("List path %s err: %s" % (path, err))
            
            if counter == 0:
                Exception("empty")
        except Exception:
            raise exceptions.FileNotFoundError('%s is not there' % path)

    def exists(self, path):
        path = self._init_path(path)
        try:
            self.head_store(path)
            return True
        except Exception:
            return False

    @lru.remove
    def remove(self, path):
        path = self._init_path(path)

        try:
            self.head_store(path)
        except Exception:
            raise exceptions.FileNotFoundError('%s is not there' % path)

        ret, err = qiniu.rs.Client().delete(self._bucket, path)
        if err is not None:
            raise IOError("List path %s err: %s" % (path, err))

    def get_size(self, path):
        path = self._init_path(path)
        try:
            headers = self.head_store(path)
            return headers['fsize']
        except Exception:
            raise exceptions.FileNotFoundError('%s is not there' % path)
