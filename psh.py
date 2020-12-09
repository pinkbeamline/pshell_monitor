#!/home/epics/miniconda3/envs/pshell_client/bin/python3

from pshell import client as psc
import time
import queue
import epics
import pathlib

## global queue variable
qbuff = queue.Queue()
state = 0
txtbuffer = []
txtstr = ""

## Constants
MAXARRAYSIZE = 500000

## file server
def save2file(list):
    try:
        logpath="/home/epics/JFData/pshell_logs"
        now=time.localtime()
        folder="/{:d}_{:02d}".format(now.tm_year,now.tm_mon)
        file="/{:d}{:02d}{:02d}.txt".format(now.tm_year,now.tm_mon,now.tm_mday)
        fullpath = logpath+folder+file
        pathlib.Path(logpath+folder).mkdir(parents=True, exist_ok=True)
        savestr = '\n'.join(list)+'\n'
        f=open(fullpath, 'a')
        f.write(savestr)
        f.close()
    except:
        print(time.asctime()+": Failed to save to file "+fullpath)

## event callback
def on_event(name, value):
    global qbuff
    qbuff.put(value)

## set PV connections
pvtxtout = epics.PV("PINK:STS:pshell", auto_monitor=False)
pvbuffsize = epics.PV("PINK:STS:buffersize", auto_monitor=False)

print("Running pshell client listener service...")

ps = psc.PShellClient("http://pink-shuttle02:8090")
ps.start_sse_event_loop_task(["shell"], on_event)

while(1):
    if(state==0):
        try:
            #ps = psc.PShellClient("http://pink-shuttle02:8090")
            resp=ps.get_state()
            state=1
            #ps.start_sse_event_loop_task(["shell"], on_event)
            print(time.asctime() + " : Pshell connected")
        except:
            state=0
    elif(state==1):
        try:
            resp=ps.get_state()
            if qbuff.qsize()>0:
                tempbuff = []
                ## transfer data from queue to tempbuff
                while qbuff.qsize():
                    tempbuff.append(str(qbuff.get()))
                ## add new data from tempbuff to txtbuffer
                for txtline in tempbuff:
                    txtbuffer.append(txtline)
                ## trim number of lines
                buffsize = int(pvbuffsize.get())
                txtbuffer = txtbuffer[-buffsize:]
                txtstr = '\n'.join(txtbuffer)
                if len(txtstr) > MAXARRAYSIZE:
                    txtstr = txtstr[-MAXARRAYSIZE:]
                try:
                    pvtxtout.put(txtstr)
                except:
                    print(time.asctime() + "Failed to post buffer to PV. Check IOC")
                ## dump new lines to log files
                save2file(tempbuff)

        except:
            print(time.asctime() + " : Pshell disconnected")
            state=0
    time.sleep(1)

