import grpc

import lba2pba_pb2
import lba2pba_pb2_grpc



def run():
    with grpc.insecure_channel("172.16.182.39:23832") as channel:
        stub = lba2pba_pb2_grpc.DBFileAgentStub(channel)
        res = stub.GetPba(lba2pba_pb2.FAGetPbaRequest(requests=[{'fileName':'monitor.log','offset':4184304,'length':20240}]))

        print(res)


if __name__ == "__main__":
    run()
