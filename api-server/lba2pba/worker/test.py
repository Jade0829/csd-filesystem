import subprocess as sp
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import multiprocessing
import os
import time

class Worker(FileSystemEventHandler):
    def __init__(self, excludes,bricks):
        self.excludes = excludes
        super().__init__()
        self.last_created = {}
        self.bricks = bricks

    def is_excluded(self, path):
        for folder in self.excludes:
            if folder in path:
                return True
        return False
    
    def on_moved(self, event):
        if not self.is_excluded(event.src_path) and not self.is_excluded(event.dest_path):
            if not event.is_directory:
                self.last_created[event.src_path] = time.time()

                print(f"File move: {event.src_path} -> {event.dest_path}")
       

    def on_modified(self, event):
        if not self.is_excluded(event.src_path):
            if not event.is_directory:
                if not event.src_path in self.last_created.keys():
                    return

                check_time = time.time() - self.last_created[event.src_path]
 
                if check_time < 1:
                    return
                
                print(f"File modified: {event.src_path}\n check time : {check_time}")
                self.bricks.append(f'modify:{event.src_path}')

    def on_created(self, event):
        if not self.is_excluded(event.src_path):
            if not event.is_directory:
                print(f"File created: {event.src_path}")
                self.bricks.append(f'create:{event.src_path}')
    def on_deleted(self, event): 
        if not self.is_excluded(event.src_path):
            if not event.is_directory:
                print(f"File deleted: {event.src_path}")
                self.bricks.append(f'delete:{event.src_path}')
  


def monitoring(path, exclude_folders, bricks):
    event_handler=Worker(exclude_folders,bricks)
    observer = Observer()
    observer.schedule(event_handler,path,recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()

err, out = sp.getstatusoutput("./getBricks -n distribute")
if err == 0:
    lines = out.split("\n")
    excludes = [".gluster",".swp",".swx"]

    brickData = []

    manager = multiprocessing.Manager()
    bricks = manager.dict()

    pList = []
    for line in lines:
        brickData.append(line.split())

    for data in brickData:
        volname, path, ip = data
        print(f'Moniotoring : {path}')
        if not path in bricks.keys():
            bricks[path] = manager.list()
        
        p = multiprocessing.Process(target=monitoring,args=(path,excludes,bricks[path]))
        p.start()
        pList.append(p)

    try:
        while True:
            for brick in bricks.keys():
                while bricks[brick]:
                    data = bricks[brick].pop(0)
                    print(data)

    except KeyboardInterrupt:
        for p in pList:
            p.terminate()
        manager.shutdown()

