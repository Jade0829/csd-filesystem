import lba2pba_pb2
import lba2pba_pb2_grpc

import grpc

import manager_kube

with grpc.insecure_channel("192.168.10.1:23831") as channel:
    stub = lba2pba_pb2_grpc.DBFileManagerStub(channel)
    res = stub.RegisterQA(lba2pba_pb2.FMRegisterQARequest(addr='172.16.182.33:23832'))
    print(res)

    res = stub.GetFileMap(lba2pba_pb2.FMGetFileMapRequest(ip='172.16.182.33'))
    print(res)

    res = stub.DeregisterQA(lba2pba_pb2.FMDeregisterQARequest(addr='172.16.182.33:23832'))
    print(res)
