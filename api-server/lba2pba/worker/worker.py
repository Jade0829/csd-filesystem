from concurrent import futures
import logging

import grpc

import lba2pba_pb2
import lba2pba_pb2_grpc

import os
import errno
import struct
import array
import fcntl
import json
import subprocess
import time
import threading

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import multiprocessing 

_PBASCAN_FORMAT = "=QQLLLL"
_PBASCAN_SIZE = struct.calcsize(_PBASCAN_FORMAT)
_PBASCAN_EXTENT_FORMAT = "=QQQQQLLLL"
_PBASCAN_EXTENT_SIZE = struct.calcsize(_PBASCAN_EXTENT_FORMAT)
_PBASCAN_IOCTL = 0xC020660B
_PBASCAN_FLAG_SYNC = 0x00000001
_PBASCAN_BUFFER_SIZE = 256 * 1024

def getPBA(path):
    try:
        cmd = f'df {path}'
        err, res = subprocess.getstatusoutput(cmd)
        res = res.split("\n")[1]
        
        disk = res.split()[0].split("/")[-1]

        pba_buf_size = _PBASCAN_BUFFER_SIZE - _PBASCAN_SIZE
        _filemap_extent_cnt = pba_buf_size // _PBASCAN_EXTENT_SIZE
        pba_buf_size = _filemap_extent_cnt * _PBASCAN_EXTENT_SIZE
        pba_buf_size += _PBASCAN_SIZE

        pba_buf = array.array('B', [0] * pba_buf_size)

        db_fd = open(f'{path}','r')
        db_info = os.stat(path)
        disk_major = os.major(db_info.st_dev)
        disk_minor = os.minor(db_info.st_dev)

        struct.pack_into(_PBASCAN_FORMAT, pba_buf, 0, 0, db_info.st_size, _PBASCAN_FLAG_SYNC, 0, _filemap_extent_cnt, 0)

        try:
            fcntl.ioctl(db_fd, _PBASCAN_IOCTL, pba_buf, 1)
        except IOError as err:
            if err.errno == errno.EOPNOTSUPP:
                logging.info(f"FILEMAP ioctl is not supported by filesystem {err}")
            if err.errno == errno.ENOTTY:
                logging.info(f"FILEMAP ioctl is not supported by kernel {err}")

            raise Exception(f"the FILEMAP ioctl failed for {path} : {err}")

        pba_map = struct.unpack(_PBASCAN_FORMAT, pba_buf[:_PBASCAN_SIZE])
        logging.info(f"DEBUG: extent count: {pba_map[3]}")

        chunk_list = list()

        host=subprocess.getstatusoutput('hostname')[1]

        for i in range(0, pba_map[3]):
            dist = _PBASCAN_SIZE + _PBASCAN_EXTENT_SIZE * i
            pba_extent = struct.unpack(_PBASCAN_EXTENT_FORMAT, pba_buf[dist:dist+_PBASCAN_EXTENT_SIZE])
            chunk_obj = dict()
            chunk_obj['disk'] = disk
            chunk_obj['host'] = host
            chunk_obj['major'] = disk_major
            chunk_obj['minor'] = disk_minor
            chunk_obj['offset'] = pba_extent[1]
            chunk_obj['length'] = pba_extent[2]
            chunk_list.append(chunk_obj)

        logging.info(f"Files : {path}")
        logging.info(f"ChunkObj : {chunk_obj}")
        return chunk_list
    except Exception as e:
        logging.info(f'Error : {e}')
        return []

class BrickMonitor(FileSystemEventHandler):
    def __init__(self,excludes, brick, volName,t):
        self.excludes = excludes
        self.brick = brick
        self.volName = volName
        super().__init__()
        self.last_created = {}
        self.type = t
        
        
    def is_excluded(self,path):
        for exclude in self.excludes:
            if exclude in path:
                return True
        return False


    def on_moved(self, event):
        if not self.is_excluded(event.src_path) and not self.is_excluded(event.dest_path):
            if not event.is_directory:
                self.last_created[event.src_path] = time.time()

                

    def on_modified(self, event):
        if not self.is_excluded(event.src_path):
            if not event.is_directory:
                if not event.src_path in self.last_created.keys():
                    return

                check_time = time.time() - self.last_created[event.src_path]

                if check_time < 1:
                    return

                
                if '~' == event.src_path[-1]:
                    return

                logging.info(f'modify {event.src_path}')
                
                if not event.src_path in self.brick.keys():
                    #self.brick.append(f'{self.volName}:modify:{event.src_path}')
                    self.brick[event.src_path] = f'{self.volName}:{self.type}:modify'
    def on_created(self, event):
        if not self.is_excluded(event.src_path):
            if not event.is_directory:
                if '~' == event.src_path[-1]:
                    return

                logging.info(f'create {event.src_path}')
                self.last_created[event.src_path] = time.time()
    
                if not event.src_path in self.brick.keys():
                    self.brick[event.src_path] = f'{self.volName}:{self.type}:create'
    def on_deleted(self, event):
        if not self.is_excluded(event.src_path):
            if not event.is_directory:
                if '~' == event.src_path[-1]:
                    return
                logging.info(f'delete {event.src_path}')
                
                if not event.src_path in self.brick.keys():
                    self.brick[event.src_path] = f'{self.volName}:{self.type}:delete'
		

class Worker(lba2pba_pb2_grpc.WorkerServicer):
    def __init__(self):
        self.nodeFilePbas = {}
        self.nodeFileMonitors = {}
        self.traceIp = ''
        self.tracePort = ''
        self.pManager = multiprocessing.Manager()
        self.targets = self.pManager.dict()
        self.pList = []

    def sendPba(self,fname,action,volName,t):
        try:
            if not action == 'delete':
                pba = getPBA(fname)
                print(pba)
            else:
                pba = [{'host':subprocess.getstatusoutput('hostname')[1]}]

            filePba = {'fileName':fname,'volName':volName,'pba':pba,'type':t}
            logging.info(f'Send filePba:{filePba} -> {self.traceIp}:{self.tracePort}')
            with grpc.insecure_channel(f'{self.traceIp}:{self.tracePort}') as channel:
                logging.info(f'start send filePba({t}) to Trace')
                stub = lba2pba_pb2_grpc.TraceStub(channel)
                res = ''
                try:
                    if action == 'create':
                        logging.info(f'Send Create Stub -> start')
                        res = stub.TChangeFile(lba2pba_pb2.TChangeRequest(action='create',filePba=filePba))
                        logging.info(f'Send Create Stub -> {filePba}')
                    elif action == 'modify':
                        res = stub.TChangeFile(lba2pba_pb2.TChangeRequest(action='modify',filePba=filePba))
                        logging.info(f'Send Modify Stub -> {filePba}')
                    elif action == 'move':
                        res = stub.TChangeFile(lba2pba_pb2.TChangeRequest(action='move',filePba=filePba))
                        logging.info(f'Send Move Stub -> {filePba}')
                    elif action == 'delete':
                        res = stub.TChangeFile(lba2pba_pb2.TChangeRequest(action='delete',filePba=filePba))
                        logging.info(f'Send Delete Stub -> {filePba}')
                    else:
                        logging.info(f'type error : {action}')
                
                except grpc.RpcError as e:
                    res = f'RPC Failed : {e}'
                    logging.info(res)
                except Exception as e:
                    res = e
                    logging.info(res)
                
        except Exception as e:
            logging.info(f'Err : {e}')

    def _monitor(self, path, excludes, volName,bricks,t):
        if not path in bricks.keys():
            bricks[path] = self.pManager.dict()

        evtHandler = BrickMonitor(excludes, bricks[path], volName,t)
        observer = Observer()
        observer.schedule(evtHandler, path,recursive=True)
        observer.start()

        
        logging.info(f'Brick Monitoring Start -> {path}')
        stop_event = threading.Event()
        try:
            stop_event.wait()
        except KeyboardInterrupt:
            observer.stop()
        except Exception as e:
            print(f'Err : {e}')
        finally:
            self.pManager.shutdown()
            observer.stop()
            for p in self.pList:
                p.terminate()

    def sendProcess(self):
        try:
            while True:
                for target in self.targets.keys():
                    while self.targets[target]:
                        for path, data in self.targets[target].items():
                            volName, t, action = data.split(":",2)
                            self.sendPba(path,action,volName,t)

                            del self.targets[target][path]
                time.sleep(1)        
        except Exception as e:
            print(f'Err : {e}')
        finally:
            self.pManager.shutdown()
            for p in self.pList:
                p.terminate()     

    def getFilePba(self,path,volume,t):
        exclude_dirs = ['.glusterfs','.remove_me']

        filePbaList = []

        for root, dirs, files in os.walk(path):
            if any(exclude in root for exclude in exclude_dirs):
                continue

            for f in files:
                if not (".swp" in f or ".smx" in f):
                    filePba = dict()
                    fname = os.path.join(root,f)
                    filePba['pba'] = getPBA(fname)
                    filePba['volName'] = volume
                    filePba['fileName'] = fname
                    filePba['type'] = t

                    filePbaList.append(filePba)

        return filePbaList

    def WInit(self, request, content):
        traceIp, tracePort = request.signal.split(":")

        self.traceIp = traceIp
        self.tracePort = tracePort

        logging.info(f'IP : {traceIp}, Port : {tracePort}')
        
        volumeCmd = 'gluster volume list'
        err, res = subprocess.getstatusoutput(volumeCmd)
        if err == 0:
            volumes = res.split("\n")
            filePbaList = []
    
            for volume in volumes:
                err, res = subprocess.getstatusoutput(f"/lba2pba/worker/getBricks -n {volume}")
                if err == 0:
                    lines = res.split("\n")
                    excludes = [".gluster", ".swp", ".smx",'.remove_me']
                    typeCmd = f'gluster volume info {volume}| grep "Type" | cut -d":" -f2 | sed "s/ //g"'

                    err, res = subprocess.getstatusoutput(typeCmd)
                    if err == 0:
                        for line in lines:
                            volName, path, ip = line.split()
      
                            filePbaList += self.getFilePba(path,volName, res)
                            
                            p = multiprocessing.Process(target=self._monitor, args=(path,excludes,volName,self.targets,res))
                            p.start()
                            self.pList.append(p)
                    else:
                        logging.error(f'ERR : {err}')
                        
                else:
                    logging.error(f'ERR : {err}')
            
            p = multiprocessing.Process(target=self.sendProcess, args=())
            p.start()
            self.pList.append(p)

            logging.info(filePbaList)
            return lba2pba_pb2.WInitResponse(filePba=filePbaList)
        else:                
            logging.error(f'ERR: {res}')
            return lba2pba_pb.WInitResponse(filePba=[])


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    lba2pba_pb2_grpc.add_WorkerServicer_to_server(Worker(),server)
    server.add_insecure_port('[::]:23829')
    logging.info("PBA Worker Start!!")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    serve()


