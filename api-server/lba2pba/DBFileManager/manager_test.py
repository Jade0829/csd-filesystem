import os
import yaml
import subprocess

from concurrent import futures
import logging

import grpc

import lba2pba_pb2
import lba2pba_pb2_grpc

import manager_kube

class DBFileManager(lba2pba_pb2_grpc.DBFileManagerServicer):
    def __init__(self):
        self.ip = subprocess.getstatusoutput('hostname -i')[1]
        self.FM = {}
        self.pvcInfo = manager_kube.GetPVCInfoTemp()
        self.QAs = {}

        self.rawFM = {}

        with grpc.insecure_channel("trace:23830") as channel:
            stub = lba2pba_pb2_grpc.TraceStub(channel)
            res = stub.TRegister(lba2pba_pb2.TRegisterRequest(addr=f'{self.ip}:23831'))

            if res.res == 'OK':
                self.rawFM = stub.TGetFileMap(lba2pba_pb2.TGetFileMapRequest())
                err, pvcInfo = self.pvcInfo        

                if err == 0:
                    for pvcName in pvcInfo.keys():
                        self.pvcFMInsert(pvcName)

                    print(self.FM)

    def RegisterQA(self, request, content):
        ip,port,volName = request.addr.split(":")
        

        if not volName in self.QAs.keys():
            self.QAs[volName] = []

        self.QAs[volName].append(f'{ip}:{port}')
        print(f'Register Query Agent : pvcName({volName}), addr({ip}:{port})')

        return lba2pba_pb2.FMRegisterQAResponse(res='OK')

    def DeregisterQA(self, request, content):
        ip,port,volName = request.addr.split(":")

        agents = list(set(self.QAs[volName]))
        agents.remove(f'{ip}:{port}')

        self.QAs[volName] = agents
        print(f'Deregister Query Agent : pvcName({volName}), addr({ip}:{port})')

        return lba2pba_pb2.FMDeregisterQAResponse(res='OK')

    def pvcFMInsert(self, pvcName):
        pvcInfo = self.pvcInfo[1][pvcName]
        if not pvcName in self.FM.keys():
            self.FM[pvcName] = {}

        for filePba in self.rawFM.fileMap.filePba:
            subdir = pvcInfo['subDir']
            _type = filePba.type
            if f'{subdir}/' in filePba.fileName:
                fname = filePba.fileName.split(f'{subdir}/')[1]
                if 'Distribute' == _type:
                    filePba.fileName = fname
                    self.FM[pvcName][fname] = filePba
                elif 'Replicate' in _type:
                    host = filePba.pba[0].host
                    pba = filePba.pba
                    if not fname in self.FM[pvcName].keys():
                        tmpFilePba = lba2pba_pb2.FilePBA(rPba=[{'Node':host,'pba':pba}],fileName=fname,volName=filePba.volName,type=filePba.type)
                        self.FM[pvcName][fname] = tmpFilePba
                        
                    else:
                        self.FM[pvcName][fname].rPba.append(lba2pba_pb2.ReplicaPba(Node=host,pba=pba))
                        

    def CreatePvc(self,request,content):
        pvcName = request.pvcName
        scName = request.scName
        limitt = request.limit

        template = ''
        yamlName = f'{pvcName}_pvc.yaml'
        with open('tmeplate_pvc.yaml','r') as f:
            template = yaml.load(f,Loader=yaml.FullLoader)

            template['metadata']['name'] = pvcName
            template['spec']['storageClassName'] = scName
            template['spec']['resources']['requests']['storage'] = limit

        with open(f'yaml/{yamlName}','w') as f:
            yaml.dump(template,f,default_flow_style=False)
        
        cmd = f'kubectl create -f yaml/{yamlName}'
        err, msg = subprocess.getstatusoutput(cmd)

        if err == 0:
            return lba2pba_pb2.CreatePvcResponse(msg=err) 
        else:
            return lba2pba_pb2.CreatePvcResponse(msg='ok')

    def DeletePvc(self,request,content):
        return

    def GetFileMap(self,request,content):
        #pvcName = manager_kube.GetPVC(request.ip)
        pvcName = "tmp"

        filePbas = []
        print(self.FM)

        for filePba in self.FM[pvcName].values():
            filePbas.append(filePba)

        return lba2pba_pb2.FMGetFileMapResponse(fileMap={'filePba':filePbas})

    def PushPba(self,request,content): 
        action = request.action
        filePba = request.filePba
        err, pvcInfo = self.pvcInfo
        _type = filePba.type

        pvcName = ''

        print('=============================================================')
        print(f'{action} {_type}')
        if err == 0:
            for pvc in pvcInfo.keys():
                if pvcInfo[pvc]['subDir'] in filePba.fileName:
                    pvcName = pvc

            if action == 'create':
                if pvcName:
                    subdir = pvcInfo[pvcName]['subDir']
                    self.rawFM.fileMap.filePba.append(filePba)
                    rPath = filePba.fileName.split(f'{subdir}/')[1]
                    filePba.fileName = rPath

                    if 'Distribute' == _type:
                        self.FM[pvcName][rPath] = filePba
                    elif 'Replicate' in _type:
                        node = filePba.pba[0].host
                        pba = filePba.pba

                        if not rPath in self.FM[pvcName].keys():
                            tmpFilePba = lba2pba_pb2.FilePBA(rPba=[{'Node':node,'pba':pba}],fileName=rPath,volName=filePba.volName,type=_type)
                            self.FM[pvcName][rPath] = tmpFilePba
                        else:
                            self.FM[pvcName][rPath].rPba.append(lba2pba_pb2.ReplicaPba(Node=node,pba=pba) )

                    
                    if pvcName in self.QAs.keys():
                        for agent in self.QAs[pvcName]:
                            with grpc.insecure_channel(agent) as channel:
                                stub = lba2pba_pb2_grpc.DBFileAgentStub(channel)
                                res = stub.PushFile(lba2pba_pb2.FAPushRequest(action=action,filePba=self.FM[pvcName][rPath]))
                                print(res)

            elif action == 'modify':
                if pvcName:
                    subdir = pvcInfo[pvcName]['subDir']
                    rPath = filePba.fileName.split(f'{subdir}/')[1]
                    
                    if 'Distribute' in _type:
                        self.FM[pvcName][rPath].pba = filePba.pba
                    elif 'Replicate' in _type:
                        node = filePba.pba[0].host
                        pba = filePba.pba

                        index = -1

                        for i in range(len(self.FM[pvcName][rPath].rPba)):
                            if node == self.FM[pvcName][rPath][i].Node:
                                index = i

                        if index >= 0:
                            self.FM[pvcName][rPath][i].pba = pba

                    print(f'Modify FilePba to FM => pvcName({pvcName}), fileName({rPath})')

            elif action == 'delete':
                if pvcName:
                    subdir = pvcInfo[pvcName]['subDir']
                    rPath = filePba.fileName.split(f'{subdir}/')[1]

                    print(f"Delete FilePba to FM => pvcName({pvcName}), fileName({rPath})")
                    if rPath in self.FM[pvcName].keys():
                        del self.FM[pvcName][rPath]

                    if 'Distribute' == _type:
                        index=-1
                        for i in range(len(self.rawFM.fileMap.filePba)):
                            if pvcName == self.rawFM.fileMap.filePba[i].fileName:
                                index = i

                        if index >= 0:
                            print(f"Delete FilePba to rawFM => index({index})")
                            self.rawFM.fileMap.filePba.pop(index)

                    elif 'Replicate' in _type:
                        index = []

                        for i in range(len(self.rawFM.fileMap.filePba)):
                            if pvcName == self.rawFM.fileMap.filePba[i].fileName:
                                index.appned(i)

                        if index:
                            for i in index:
                                print(f'Delete FilePba to rawFM => index({index})')
                                self.rawFm.fileMap.filePba.pop(i)
                    
                    if pvcName in self.QAs.keys():
                        for agent in self.QAs[pvcName]:
                            with grpc.insecure_channel(agent) as channel:
                                filePba.fileName = rPath
                                stub = lba2pba_pb2_grpc.DBFileAgentStub(channel)
                                res = stub.PushFile(lba2pba_pb2.FAPushRequest(action=action,filePba=filePba))
                                print(res)
            print("=============================================================")
            print(self.FM)

            return lba2pba_pb2.FMPushPbaResponse(msg='OK',status='0')

        else:
            return lba2pba_pb2.FMPushPbaResponse(msg=pvcInfo, status='1')

def serve():
    try:
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        lba2pba_pb2_grpc.add_DBFileManagerServicer_to_server(DBFileManager(),server)
        server.add_insecure_port('[::]:23831')
        print("DB File Manager Start !!\nPort : 23831")
        server.start()
        server.wait_for_termination()

    finally:
        with grpc.insecure_channel("trace:23830") as channel:
            ip = subprocess.getstatusoutput('hostname -i')[1]
            stub = lba2pba_pb2_grpc.TraceStub(channel)
            res = stub.TDeregister(lba2pba_pb2.TDeregisterRequest(addr=f'{ip}:23831'))

            print("deregister to trace : {res}")

if __name__ == "__main__":
    logging.basicConfig()
    serve()
