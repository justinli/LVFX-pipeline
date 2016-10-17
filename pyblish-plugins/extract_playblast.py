import os
import pyblish.api
import ftrack
import json
from Utils import capture


def load_preset(path):
    """Load options json from path"""
    with open(path, "r") as f:
        return json.load(f)


@pyblish.api.log
class ExtractPlayblast(pyblish.api.InstancePlugin):

    order = pyblish.api.ExtractorOrder
    hosts = ['maya']
    label = 'Extract Playblast'
    families = ['scene']
    optional = True

    def process(self, instance):

        task = ftrack.Task(instance.context.data['taskid'])
        taskName = task.getType().getName().lower()
        if taskName not in ['animation', 'layout']:
            self.log.info('Skipping playblast for %s' % taskName)
            return

        playblastDir = os.path.join(instance.data['workPath'], 'playblast')
        if not os.path.exists(playblastDir):
            os.makedirs(playblastDir)
        version = instance.data['vprefix'] + instance.data['version']
        shotName = task.getParent().getName()
        outFile = os.path.join(playblastDir, '{0}_{1}_playblast.mov'.format(shotName, version))
        instance.set_data('playblastFile', value=outFile)

        presetName = 'default'

        presetPath = os.path.join(os.path.dirname(capture.__file__),
                                  'capture_presets',
                                  (presetName + '.json'))
        preset = load_preset(presetPath)
        preset['camera'] = 'renderCam'

        capture.capture(filename=outFile,
                        overwrite=True,
                        quality=70,
                        **preset)
        self.log.info('extract playblast')