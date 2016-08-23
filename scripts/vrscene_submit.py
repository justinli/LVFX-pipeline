import sys
import os
import xmlrpclib
import getopt
import getpass
import re


hq_server = xmlrpclib.ServerProxy('http://192.168.0.153:5000')
try:
    hq_server.ping()
except:
    print "HQueue server is down."


def submitJob(filename, imgFile, startFrame, endFrame, step, chunk, multiple, group, priority):
    jobList = []
    jobname = 'VRay - '+ os.path.split(filename)[-1]
    imgDir = os.path.split(imgFile)[0]
    if not os.path.exists(imgDir):
        os.makedirs(imgDir)
    if 'LOGNAME' in os.environ.keys():
        submitter = os.environ['LOGNAME']
    else:
        submitter = getpass.getuser()
    if step > 1 or multiple:
        vrayCmdList = []
        for x in range(startFrame, endFrame+1, step):
            frameStart = x
            if multiple:
                newFilename = filename.replace('#', '%04d' % frameStart)
            else:
                newFilename = filename
            vrayCmd = '"/usr/autodesk/maya2016/vray/bin/vray" -display=0 -interactive=0 ' \
                      '-verboseLevel=3 -sceneFile={0} -imgFile={1} ' \
                      '-frames={2}-{2}'.format(newFilename, imgFile, frameStart)
            vrayCmdList.append(vrayCmd)
        for y in range(0, len(vrayCmdList), chunk):
            command = ' ; '.join(vrayCmdList[y:y+chunk])
            frameFinder = re.findall('frames=(\d+)-(\d+)', command)
            job_spec = {
                'name': jobname+ ' Frames:{0}-{1}'.format(frameFinder[0][0], frameFinder[-1][0]),
                'shell': 'bash',
                'command': command,
                'submittedBy': submitter,
                'tags': ['single'],
                'priority': priority,
                'triesLeft': 1,
                'onError': 'python2.7 /data/production/pipeline/linux/scripts/vray_restart_onError.py'
            }
            if group != '':
                job_spec['conditions'] = [{"type" : "client", "name": "group", "op": "==", "value": group}, ]
            jobList.append(job_spec)
    else:
        for x in range(startFrame, endFrame+1, chunk):
            frameStart = x
            if x+chunk-1 > endFrame:
                frameEnd = endFrame
            else:
                frameEnd = x+chunk-1
            job_spec = {
                'name': jobname + ' Frames:{0}-{1}'.format(frameStart, frameEnd),
                'shell': 'bash',
                'command': '"/usr/autodesk/maya2016/vray/bin/vray" -display=0 -interactive=0 '
                           '-verboseLevel=3 -sceneFile={0} -imgFile={1} '
                           '-frames={2}-{3},{4}'.format(filename, imgFile,frameStart, frameEnd, step),
                'submittedBy': submitter,
                'tags': ['single'],
                'priority': priority,
                'triesLeft': 1,
                'onError': 'python2.7 /data/production/pipeline/linux/scripts/vray_restart_onError.py'
            }
            if group != '':
                job_spec['conditions'] = [{"type" : "client", "name": "group", "op": "==", "value": group}, ]
            jobList.append(job_spec)

    mainJob = {
        'name': jobname,
        'shell': 'bash',
        'tags' : 'single',
        'priority': priority,
        'submittedBy': submitter,
        'children': jobList
    }

    jobs_ids = hq_server.newjob(mainJob)
    return jobs_ids

def main(argv):
    filename = ''
    imgFile = ''
    start = 1
    end = 1
    step = 1
    chunk = 5
    multiple = False
    group = ''
    priority = 0

    try:
        opts, args = getopt.getopt(argv, 'hv:i:f:l:s:c:mg:p:', ['vrscene=', 'imgFile=', 'first=',
                                                              'last=', 'step=', 'chunk=', 'multiple=',
                                                              'group=', 'priority='])
    except getopt.GetoptError:
        print 'vrscene_submit -v <filename> -i <imgFile> -f <startFrame> -e <endFrame> -s <step>' \
              '-c <chunk> -m -g <group> -p <priority>'
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print '\nUsage: vrscene_submit -v <vrscene> -i <imgFile> -f <firstFrame> -l <lastFrame> -s <step> ' \
                  '-c <chunk> -m\n' \
                  'Submits vrscene file for render to hqueue \n' \
                  'vrscene = Full filepath. When submitting multiple vrscene files, replace frame with # \n' \
                  'eg. /data/production/ftrack_test/shots/REEL3/REEL3_sh010/scene/lighting/test.#.vrscene \n' \
                  'imgFile = Full path to output img file \n' \
                  'first = first Frame\n' \
                  'last = last Frame\n' \
                  'step = frame step. Default = 1\n' \
                  'chunk = chunk size. Default = 5\n' \
                  'multiple = multiple VR scene files. Default = False\n' \
                  'group = name of group to submit to \n' \
                  'priority = priority of job. 0 is lowest. Default is 0' \
                  '\n ---Multiple VRScene File Example--- \n' \
                  'vrscene_submit -v /data/production/ftrack_test/shots/REEL3/REEL3_sh010/scene/lighting/vrscene/stagBeetleTest_#.vrscene -i /data/production/ftrack_test/shots/REEL3/REEL3_sh010/scene/lighting/vrscene/renders/stagBeetleTest.#.exr -f 1 -l 15 -s 4 -c 5 -m\n' \
                  '\n ---Single VRScene File Example--- \n' \
                  'vrscene_submit -v /data/production/ftrack_test/shots/REEL3/REEL3_sh010/scene/lighting/vrscene/stagBeetleTest.vrscene -i /data/production/ftrack_test/shots/REEL3/REEL3_sh010/scene/lighting/vrscene/renders/stagBeetleTest.#.exr -f 1 -l 15 -s 1 -c 5'

            sys.exit()
        elif opt in ('-v', '--vrscene'):
            filename = arg
        elif opt in ('-i', '--imgFile'):
            imgFile = arg
        elif opt in ('-f', '--first'):
            start = int(arg)
        elif opt in ('-l', '--last'):
            end = int(arg)
        elif opt in ('-s', '--step'):
            step = int(arg)
        elif opt in ('-c', '--chunk'):
            chunk = int(arg)
        elif opt in ('-m', '--multiple'):
            multiple = True
        elif opt in ('-g', '--group'):
            group = arg
        elif opt in ('-p', '--priority'):
            priority = int(arg)
    if filename == '':
        print "Please specify a valid vrscene file."
        sys.exit(2)
    elif imgFile == '':
        print "Please specify a valid output file."
        sys.exit(2)
    jobIds = submitJob(filename, imgFile, start, end, step, chunk, multiple, group, priority)
    print 'Job Submit Successful. Job Id = {0}'.format(jobIds)

if __name__ == '__main__':
    main(sys.argv[1:])