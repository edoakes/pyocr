import os
import subprocess
import tempfile
import base64

SCRIPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tesseract-lambda')
LIB_DIR = os.path.join(SCRIPT_DIR, 'lib')

def ocr(event, context):
    try:
        imgpath = '/tmp/img.' + event['filename'].split('.')[1]
        outpath = '/tmp/out'

        b64 = event['data'].split('base64,')[1]

        with open(imgpath, 'w+') as imgfd:
            imgfd.write(base64.b64decode(b64))

        command = 'LD_LIBRARY_PATH={} TESSDATA_PREFIX={} {}/tesseract {} {}'.format(
            LIB_DIR,
            SCRIPT_DIR,
            SCRIPT_DIR,
            imgpath,
            outpath,
        )

        try:
            output = subprocess.check_output(command, shell=True)
        except subprocess.CalledProcessError as ocrE:
            print ocrE.output
            raise ocrE

        with open(outpath+'.txt', 'r+') as outfd:
            ocr = base64.b64encode(outfd.read())

        ret_name = event['filename'].split('.')[0] + '.txt'

        return {'data':ocr, 'filename':ret_name}

    except Exception as e:
        raise e

def lambda_handler(event, context):
    fn = {
        'ocr': ocr
    }[event['op']]

    return fn(event, context)