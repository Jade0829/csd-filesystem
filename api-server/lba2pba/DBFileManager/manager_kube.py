import os
import yaml
import subprocess


def GetPVC(Ip):
	ip = Ip

	podCMD = '''kubectl get pod -o json | jq '.items[] | select(.status.podIP=="%s") | .metadata.name' '''%ip
	err, podName = subprocess.getstatusoutput(podCMD)

	pvcCMD = '''kubectl get pod/%s -o json | jq -r ".spec.volumes[0].persistentVolumeClaim.claimName" '''%podName
	err, pvcName = subprocess.getstatusoutput(pvcCMD)

	return pvcName

def GetSubDir(PvcName):
	pvcName = PvcName

	pvCMD = '''kubectl get pvc/%s -o json | jq -r ".spec.volumeName" '''%pvcName
	err, pvName = subprocess.getstatusoutput(pvCMD)

	subdirCMD = '''kubectl get pv/%s -o json | jq -r ".spec.csi.volumeAttributes.path" '''%pvName
	err, subDir = subprocess.getstatusoutput(subdirCMD)

	scCMD = '''kubectl get pvc/%s -o json | jq -r ".spec.storageClassName" '''%pvcName
	err, scName = subprocess.getstatusoutput(scCMD)

	glsCMD = '''kubectl get sc/%s -o json | jq -r ".parameters.gluster_volname" '''%scName
	err, volName = subprocess.getstatusoutput(glsCMD)

	subDir = subDir.replace("\n","")
	volName = volName.replace("\n","")

	return subDir, volName	

def GetPVCInfo():
    pvcCmd = "kubectl get pvc | awk 'NR>=2 {print $1}'"
    info = {}

    err, res = subprocess.getstatusoutput(pvcCmd)
    if err == 0:
        pvcList = res.split('\n')

        for pvc in pvcList:
            data = {}
            subDir, volName = GetSubDir(pvc)
            data['subDir'] = subDir
            data['volName'] = volName

            info[pvc] = data

        return 0, info

    else:
        return 1, res

def GetPVCInfoTemp():
    data={}
    data['subDir'] = 'temp'
    data['volName'] = 'tmp'

    info={'tmp':data}

    return 0, info
