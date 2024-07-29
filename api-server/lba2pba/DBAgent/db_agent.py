from concurrent import futures
import logging
import subprocess

import grpc

import lba2pba_pb2
import lba2pba_pb2_grpc


def getIP():
    cmd = "hostname -i"
    err , ip = subprocess.getstatusoutput(cmd)

    return ip				
			

class DBFileAgent:
    def __init__(self):
        self.ip = getIP()
        self.FM = {}
        with grpc.insecure_channel('DBFileManager:23831') as channel:
            stub = lba2pba_pb2_grpc.DBFileManagerStub(channel)
            res = stub.RegisterQA(lba2pba_pb2.FMRegisterQARequest(addr=f'{self.ip}:23832'))
            print(f'Register to Manager : {res}')

            res = stub.GetFileMap(lba2pba_pb2.FMGetFileMapRequest(ip=self.ip))
            self.FM = res.fileMap
            print(self.FM)

    def getPba(self,file_name, start_offset, length):
        def get(pbaList):
            result = []

            start = start_offset
            left_len = length
            
            start_chk = False
            end_chk = False

            for pba in pbaList:
                tmp_pba = lba2pba_pb2.PBA()
                s = pba.offset
                e = s + pba.length

                if not start_chk:
                    if start <= pba.length :
                        tmp_pba.disk = pba.disk
                        tmp_pba.host = pba.host
                        tmp_pba.offset = s + start

                        if tmp_pba.offset + left_len <= e:
                            tmp_pba.length = left_len
                            end_chk = True
                        else:
                            tmp_pba.length = e-(s+start)
                            left_len -= tmp_pba.length

                        result.append(tmp_pba)
                        start_chk = True
                else:
                    if not end_chk:
                        tmp_pba.disk = pba.disk
                        tmp_pba.host = pba.host
                        tmp_pba.offset = pba.offset

                        if tmp_pba.offset + left_len < e:
                            tmp_pba.length = left_len
                            end_chk = True
                        else:
                            tmp_pba.length = pba.length

                        result.append(tmp_pba)

            return result

        for file_pba in self.FM.filePba:
            print(file_pba.fileName)
            if file_name == file_pba.fileName:
                t = file_pba.type
                print(f'Type : {t}, File : {file_name}')

                if 'Replicate' in t:
                    res = []
                    
                    for pba in file_pba.rPba:
                            res.append({"Node":pba.Node,"pba":get(pba.pba)})

                    return {"fileName":file_name,"type":t,"rPba":res}

                elif 'Distribute' == t:
                                
                    return {"fileName":file_name,"type":t,"pba":get(file_pba.pba)}

        return

    def GetPba(self,request,content):
        result = []		
        
        for re in request.requests:
            file_name = re.fileName
            start_offset = re.offset
            length = re.length
            
            print("%s %s %s"%(file_name,start_offset,length))
    
            result.append(self.getPba(file_name, start_offset, length))

        if result:
            return lba2pba_pb2.FAGetPbaResponse(filePba=result)
        else:
            return lba2pba_pb2.FAGetPBaResponse(filePba={})

    def PushFile(self,request,content):
        action = request.action
        filePba = request.filePba
        _tpye = filePba.type
        print(action,filePba)

        if action == 'create':
            self.FM.filePba.append(filePba)
            print(f'Create FilePba to File Map : \n{filePba}')

        elif action == 'modify':
            for i in range(len(self.FM.filePba)):
                if filePba.fileName == self.FM.filePba[i].fileName:
                    self.FM.filePba[i].pba = filePba.pba
                    print(f'Modify FilePba to File Map : \n{filePba}')
                    break
            

        elif action == 'delete':
            index = -1
            for i in range(len(self.FM.filePba)):
                if filePba.fileName == self.FM.filePba[i].fileName:
                    index = i

            if index >= 0:
                out=self.FM.filePba.pop(index)
                print(f'Delete FilePba to File Map : \n{out}')

        print("======================================================")
        print(self.FM)

        return lba2pba_pb2.FAPushResponse(msg='OK',status='0')


def serve():
    try:
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        lba2pba_pb2_grpc.add_DBFileAgentServicer_to_server(DBFileAgent(),server)
        server.add_insecure_port('[::]:23832')
        print("DBFile Agent Start!!\nPort : 23832")
        server.start()
        server.wait_for_termination()
    finally:
        with grpc.insecure_channel('DBFileManager:23831') as channel:
            ip = getIP()
            stub = lba2pba_pb2_grpc.DBFileManagerStub(channel)
            res = stub.DeregisterQA(lba2pba_pb2.FMDeregisterQARequest(addr=f'{ip}:23832'))
            print(f'Deregister to Manager : {res}')

if __name__ == "__main__":
    logging.basicConfig()
    serve()
	

