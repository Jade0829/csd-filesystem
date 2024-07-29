LBA2PBA는 쿠버네티스에서 동작하는 파드가 사용중인 PV(Persistent Volume)에 저장된 파일들의 물리 주소를 찾아주는 소프트웨어입니다.

LBA2PBA는 gRPC를 사용하며, 4개의 서비스(DB Agent, DB File Manager, Trace, Worker)가 있습니다.


DB Agent
---
DB Agent는 파드에 저장된 파일들의 논리 주소를 받으면 대응되는 물리 주소로 반환해주는 서비스입니다.

```
# LBA2PBA.proto Code
service DBFileAgent{
	rpc GetPba (FAGetPbaRequest) returns (FAGetPbaResponse);
	rpc PushFile (FAPushRequest) returns (FAPushResponse);
}

message PBA{
	string disk = 1;
	string host = 2;
	int64 offset = 3;
	int64 length = 4;
	int64 major = 5;
	int64 minor = 6;
}

message ReplicaPba{
	repeated PBA pba = 1;
	string Node = 2;
}

message FilePBA{
	repeated PBA Pba = 1;
	repeated ReplicaPba rPba = 2;
	string fileName = 3;
	string volName = 4;
	string type = 5;
}

message FileMap{
	repeated FilePBA filePba = 1;
}

message FAGetPbaRequest{
	message Request{
		string fileName = 1;
	    int64 offset = 2;
	    int64 length = 3;
	}
  
	repeated Request requests = 1;
}

message FAGetPbaResponse{
	repeated FilePBA filePba = 1;
}

message FAPushRequest{
	string action = 1;
	FilePBA filePba = 2;
}

message FAPushResponse{
	string msg = 1;
	string status = 2;
}
```

DB File Manager
---
Manager는 QueryAgent로부터 PV에 저장된 파일 리스트 전달받아 전체 FileMap을 관리하고, PVC 생성 및 삭제 기능을 하는 서비스입니다.

```
service Manager{
	rpc RegisterQA (FMRegisterQARequest) return (FMRegisterQAResponse);
	rpc DeregisterQA (FMDeregisterQARequest) return (FMDeregisterQAResponse);
	rpc CreatePvc (CreatePvcRequest) returns (CreatePvcResponse);
	rpc DeletePvc (DeletePvcRequest) returns (DeletePvcResponse);
	rpc GetFileMap (FMGetFileMapRequest) returns (FMGetFileMapResponse);
	rpc PsuhPba (FMPushPbaRequest) returns (FMPushPbaResponse);
}

message CreatePvcRequest{
	string pvcName = 1;
	string pvcType = 2;
	string dupliType = 3;
}

message CreatePvcResponse{
	string msg = 1;
	string pvcName = 2;
}

message DeletePvcRequest{
	string pvcName = 1;
}

message DeletePvcResponse{
	string msg = 1;
	string pvcName = 2;
}

message FMRegisterQARequest{
	string addr = 1;
}

message FMRegisterQAResponse{
	string res = 1;
}

message FMDeregisterQARequest{
	string addr = 1;
}

message FMDeregisterQAResponse{
	string res = 1;
}

message FMGetFileMapRequest{
	string ip = 1;
	repeated string fileList = 2;
}

message FMGetFileMapResponse{
	FileMap fileMap = 1;
}

message FMPushPbaRequest{
	string action = 1;
	FilePba filePba = 2;
}

message FMPushPbaResponse{
	string msg = 1;
	string status = 2;
}
```

Trace
---
Trace는 worker가 전달해준 FilePba 정보를 가지고 FileMap을 구성합니다.

```
service Trace{
	rpc TChangeFile (TChangeRequest) returns (TChangeResponse);
	rpc TGetFileMap (TGetFileMapRequest) returns (TGetFileMapResponse);
	rpc TRegister (TRegisterRequest) returns (TRegisterResponse);
	rpc TDeregister ( TDeregisterRequest) returns (TDeregisterResponse);
}

message PBA{
	string disk = 1;
	string host = 2;
	int64 offset = 3;
	int64 length = 4;
	int64 major = 5;
	int64 minor = 6;
}

message TChangeRequest{
	string action = 1;
	FilePBA filePba = 2;
}

message TChangeResponse{
	string res = 1;
}

message TGetFileMapRequest{
	string signal = 1;
}

message TGetFileMapResponse{
	FileMap fileMap = 1;
}

message TRegisterRequest{
	string addr = 1
}

message TRegisterResponse{
	string res = 1;
}

message TDeregisterRequest{
	string addr = 1;
}

message TDeregisterResponse{
	string res = 1;
}
```

Worker
---
Worker는 gluster volume에 해당되는 brick들을 모니터링해서 물리 주소를 반환하며 주기적으로 파일 변화를 감지합니다.

```
service Worker{
	rpc WInit (WInitRequest) returns (WInitResponse);
}

message PBA{
	string disk = 1;
	string host = 2;
	int64 offset = 3;
	int64 length = 4;
	int64 major = 5;
	int64 minor = 6;
}

message ReplicaPba{
	repeated PBA pba = 1;
	string Node = 2;
}

message FilePBA{
	repeated PBA pba = 1;
	repeated ReplicaPba rPba = 2;
	string fileName = 3;
	string volName = 4;
	string type = 5; 
}

message WInitRequest{
	string signal = 1;
}

message WInitResponse{
	repeated FilePBA filePba = 1;
}
```
