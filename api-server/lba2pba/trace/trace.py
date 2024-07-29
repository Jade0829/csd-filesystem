from concurrent import futures
import logging

import grpc
import subprocess
import threading

import os
import lba2pba_pb2
import lba2pba_pb2_grpc

import shard

def toShard(f, host):
    gfidCmd = f'ssh {host} "getfattr -d -m. -e hex --absolute-name {f} | grep gfid=0x | cut -d\"=\" -f2"'
    err, res = subprocess.getstatusoutput(gfidCmd)
    if err == 0:
        gfid = res.split("0x")[-1]

        return gfid
    else:
        print(f'Error : {res}')

class Trace(lba2pba_pb2_grpc.TraceServicer):
    def __init__(self):
        peerCmd = 'gluster peer status | grep Hostname | cut -d":" -f2 | sed "s/ //g"'
        err, res = subprocess.getstatusoutput(peerCmd)
    
        hostname = subprocess.getstatusoutput('hostname')[1]

        self.peers = [hostname]

        self.agent = list()

        self.rawFM = dict()
        self.FM = dict()

        self.rawFilePba = list()
        self.shardPba = list()
        self.fmDict = dict()
        self.shardDict = dict()
        
        if err == 0:
            self.peers += res.split('\n')

        for peer in self.peers:
            self.fmDict[peer] = dict()
            self.rawFM[peer] = dict()
            with grpc.insecure_channel(f'{peer}:23829') as channel:
                stub = lba2pba_pb2_grpc.WorkerStub(channel)
                res = stub.WInit(lba2pba_pb2.WInitRequest(signal=f'{hostname}:23830'))
                
                if not res:
                    continue

                for filePba in res.filePba:
                    fname = filePba.fileName
                    if '/.shard/' in fname:
                        self.shardPba.append(filePba)
                    else:
                        self.rawFilePba.append(filePba)
                        shardName = toShard(fname,peer)

                        self.shardDict[shardName] = fname
            

        print(f'fmDict : {self.fmDict.keys()}')
        print(f'rawFM : {self.fmDict.keys()}')
 
        if self.rawFilePba:
            for fPba in self.rawFilePba:
                fname = fPba.fileName
                node = fPba.pba[0].host
                if not fname in self.fmDict[node].keys():
                    self.fmDict[node][fname] = {'shard':{},'pba':fPba.pba,'type':fPba.type}

            for sPba in self.shardPba:
                sName = sPba.fileName.split('/')[-1].replace('-','')
                sKey = sName.split('.')[0]
                fname = self.shardDict[sKey]
                
                self.fmDict[node][fname]['shard'][sPba.fileName] = sPba

            for node in self.fmDict.keys():
                for fname in self.fmDict[node].keys():
                    t = self.fmDict[node][fname]['type']
                    _filePba = {'pba':[],'rPba':[],'fileName':fname,'type':t}

                    _filePba['pba'] += self.fmDict[node][fname]['pba']

                    if self.fmDict[node][fname]['shard']:
                        shards = list(self.fmDict[node][fname]['shard'].keys())
                        shards = sorted(shards, key=lambda x: int(x.rsplit('.',1)[1]))
                        print(shards) 
                        for shard in shards:
                            _filePba['pba'] += self.fmDict[node][fname]['shard'][shard].pba

                    self.rawFM[node][fname] = _filePba
            print(self.rawFM)

    def TChangeFile(self, request, content):
        try:
            action = request.action
            print(request)
            node = request.filePba.pba[0].host
            if action == 'create':
                fPba  = request.filePba
                pba = fPba.pba
                if not '.shard' in fPba.fileName:
                    fname = fPba.fileName

                    if not fname in self.fmDict[node].keys():
                        self.fmDict[node][fname] = {'shard':{},'pba':fPba.pba, 'type':fPba.type}

                    shardName = toShard(fname,pba[0].host)
                    self.shardDict[shardName] = fname.split('/')[-1]

                    _filePba = {'pba':[],'rPba':[],'fileName':fname,'type':fPba.type}
                    _filePba['pba'] += pba

                    self.rawFM[node][fname] = _filePba
                else:
                    sName = fPba.fileName
                    sKey = sName.split('/')[-1].replace('-','')
                    fname = self.shardDict[sKey]

                    self.fmDict[node][fname]['shard'][sName] = fPba
                    t = self.fmDict[node][fname]['type']                    

                    _filePba = {'pba':[],'rPba':[],'fileName':fname,'type':t}
                    _filePba['pba'] += self.fmDict[node][fname]['pba']

                    shardList = self.fmDict[node][fname]['shard'].keys()

                    if shardList:
                        shardList.sort()
                        for shard in shardList:
                            _filePba['pba'] += self.fmDict[node][fname]['shard'][shard].pba

                    self.rawFM[node][fname] = _filePba

                for agent in self.agent:
                    with grpc.insecure_channel(agent) as channel:
                        stub = lba2pba_pb2_grpc.DBFileManagerStub(channel)
                        res = stub.PushPba(lba2pba_pb2.FMPushPbaRequest(action="create",filePba=self.rawFM[node][fname]))


                return lba2pba_pb2.TChangeResponse(res='OK')
            elif action == 'modify':
                fPba = request.filePba

                if not '.shard' in fPba.fileName:
                    fname = fPba.fileName
                    pba = fPba.pba

                    shardName = toShard(fname,pba[0].host)
                    
                    self.fmDict[node][fname]['pba'] = pba

                    _filePba = {'pba':[pba],'rPba':[],'fileName':fname,'type':self.fmDict[node][fname]['type']}

                    shardList = self.fmDict[node][fname]['shard'].keys()

                    if shardList:
                        shardList.sort()
                        for shard in shardList:
                            _filePba['pba'] += self.fmDict[node][fname]['shard'][shard].pba

                else:
                    sName = fPba.fileName
                    sKey = sName.split('/')[-1].replace('-','')
                    fname = self.shardDict[sKey]
                
                    self.fmDict[node][fname]['shard'][sName] = fPba

                    _filePba = {'pba':[],'rPba':[],'fileName':fname,'type':self.fmDict[node][fname]['type']}
                    _filePba['pba'] += self.fmDict[node][fname]['pba']

                    shardList = self.fmDict[fname]['shard'].keys()
                    
                    if shardList:
                        shardList.sort()
                        for shard in shardList:
                            _filePba['pba'] = self.fmDict[node][fname]['shard'][shard].pba

                    self.rawFM[node][fname] = _filePba
                for agent in self.agent:
                    with grpc.insecure_channel(agent) as channel:
                        stub = lba2pba_pb2_grpc.DBFileManagerStub(channel)
                        res = stub.PushPba(lba2pba_pb2.FMPushPbaRequest(action="modify",filePba=self.rawFM[node][fname]))

                        print(res)

                return lba2pba_pb2.TChangeResponse(res='OK')
            elif action == 'delete':
                fPba = request.filePba
                
                if not '.shard' in fPba.fileName:
                    fname = fPba.fileName
                    _type = fPba.type

                    del self.fmDict[node][fname]
                    print(f'Delete fmDict {fname}')
                    del self.rawFM[node][fname]
                    print(f'Delete rawFM {fname}')
                    
                    for key, value in self.shardDict.items():
                        if value == fname:
                            del self.shardDict[key]

                    for agent in self.agent:
                        with grpc.insecure_channel(agent) as channel:
                            stub = lba2pba_pb2_grpc.DBFileManagerStub(channel)
                            res = stub.PushPba(lba2pba_pb2.FMPushPbaRequest(action=f"delete",filePba={'type':_type,'fileName':fname}))

                            print(res)

                else:
                    sName = fPba.fileName
                    sKey = sName.split('/')[-1].replace('-','')
                    fname = self.shardDict[sKey]

                    del self.fmDict[node][fname]['shard'][sName]

                    _filePba = {'pba':[],'rPba':[],'fileName':fname,'type':''}
                    _filePba['pba'] += self.fmDict[node][fname]['pba']

                    shardList = self.fmDict[node][fname]['shard'].keys()

                    if shardList:
                        shardList.sort()
                        for shard in shardList:
                            _filePba['pba'] += self.fmDict[node][fname]['shard'][shard].pba

                    self.rawFM[node][fname] = _filePba
  
                    for agent in self.agent:
                        with grpc.insecure_channel(agent) as channel:
                            stub = lba2pba_pb2_grpc.DBFileManagerStub(channel)
                            res = stub.PushPba(lba2pba_pb2.FMPushPbaRequest(action=f"modify",filePba=self.rawFM[fname]))

                            print(res)
               
                return lba2pba_pb2.TChangeResponse(res='OK')
            else:
                return lba2pba_pb2.TChangeResponse(res='Fail')
        except Exception as e:
            print(f'Error : {e}')
            return lba2pba_pb2.TChangeResponse(res='Fail')

    def TGetFileMap(self, request, content):
        ret = []
        for node in self.rawFM.keys():
            for fname in self.rawFM[node].keys():
                print(f'{fname} filePba => {self.rawFM[node][fname]}')
                ret.append(self.rawFM[node][fname])

        _fm = lba2pba_pb2.FileMap(filePba=ret)
        return lba2pba_pb2.TGetFileMapResponse(fileMap=_fm)

    
    def TRegister(self, request, content):
        addr = request.addr
        
        self.agent.append(addr)
        print(f"Register Client : {addr}")

        return lba2pba_pb2.TRegisterResponse(res='OK')

    def TDeregister(self, request, content):
        addr = request.addr

        agents = list(set(self.agent))
        agents.remove(addr)

        self.agent = agents
        
        print(f"Deregister Client : {addr}")

        return lba2pba_pb2.TDeregisterResponse(res='OK')
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    lba2pba_pb2_grpc.add_TraceServicer_to_server(Trace(),server)
    server.add_insecure_port('[::]:23830')
    print("LBA2PBA Trace Start !!")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    logging.basicConfig()
    serve()
