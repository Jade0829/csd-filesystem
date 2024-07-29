import lba2pba_pb2
import lba2pba_pb2_grpc
import grpc

with grpc.insecure_channel('worker1:23829') as channel:
    path = 'ab/test3'

    stub = lba2pba_pb2_grpc.WorkerStub(channel)
    res = stub.WInit(lba2pba_pb2.WInitRequest(signal="worker1:23830"))

    print(res)
