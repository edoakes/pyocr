#!/usr/bin/env python
import os, sys, requests, json, base64, time, random, collections, argparse
from multiprocessing import Process, Pipe

ARRIVAL_INTERVAL_MEAN = 1
ARRIVAL_INTERVAL_DEV = 0.5

def conf():
    if conf.val == None:
        with open('static/config.json') as f:
            conf.val = json.loads(f.read())
    return conf.val
conf.val = None

def rand_img():
    img = random.choice(os.listdir(IMG_DIRECTORY))
    with open(os.path.join(IMG_DIRECTORY, img)) as fd:
        return {'data': 'base64,'+base64.b64encode(fd.read()), 'filename': img}

class User():
    def __init__(self, fbid, endtime):
        self.url = 'http://107.170.74.208:32771/runLambda/wgdsuobwhagv'
        self.endtime = endtime
        self.img = rand_img()
        self.ops = [
            {'fn': self.OP_img, 'freq': 1},
        ]
        self.freq_tot = sum(map(lambda op: op['freq'], self.ops))
        self.stats = {'ops': 0, 
                      'latency-sum': 0.0,
                      'ocr-sum': 0.0,
                      'convert-sum': 0.0}

    def post(self, op, data):
        print op
        data['op'] = op

        t0 = time.time()
        r = requests.post(self.url, data=json.dumps(data))
        t1 = time.time()

        self.stats['ops'] += 1
        self.stats['latency-sum'] += (t1-t0)

        ret = json.loads(r.text)
        self.stats['ocr-sum'] += float(ret['ocr_time'])
        if IMG_DIRECTORY == 'pdf':
            self.stats['convert-sum'] += float(ret['convert_time'])

        return r.text

    # TODO: verify results
    def OP_img(self):
        self.post('ocr', rand_img()) 

    def do_op(self, op):
        fn = op['fn']
        fn()

    def rand_op(self):
        r = random.randrange(0, self.freq_tot)
        for op in self.ops:
            if r <= op['freq']:
                self.do_op(op)
                break
            r -= op['freq']

    def run(self):
        while True:
            delay = max(random.normalvariate(ARRIVAL_INTERVAL_MEAN,
                                             ARRIVAL_INTERVAL_DEV), 0)
            if time.time() + delay >= self.endtime:
                break
            # TODO: subtract out time spent on last req
            time.sleep(delay)
            self.rand_op()
        return self.stats

class UserProcess:
    def __init__(self, fbid, endtime):
        self.fbid = fbid
        self.parent_conn = None
        self.child = None
        self.endtime = endtime

    def run(self, conn):
        u = User(self.fbid, self.endtime)
        results = u.run()
        conn.send(results)
        conn.close()

    def start(self):
        self.parent_conn, child_conn = Pipe()
        self.child = Process(target=self.run, args=(child_conn,))
        self.child.start()

    def wait(self):
        result = self.parent_conn.recv()
        self.child.join()
        return result

# child
def run(conn):
    u = User()
    results = u.run()
    conn.send(results)
    conn.close()

# parent
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--users', '-u', metavar='u', default=1, type=int)
    parser.add_argument('--seconds', '-s', metavar='s', default=10, type=int)
    parser.add_argument('--filetype', '-f', metavar='f', default='image', type=str)
    args = parser.parse_args()

    endtime = time.time() + args.seconds
    global IMG_DIRECTORY
    IMG_DIRECTORY = args.filetype

    procs = []
    for i in range(args.users):
        procs.append(UserProcess(i+1, endtime))

    for proc in procs:
        proc.start()

    totals = {'latency-sum': 0.0, 'ops': 0.0, 'ocr-sum': 0.0, 'convert-sum': 0.0}
    for proc in procs:
        results = proc.wait()
        for k in totals.keys():
            totals[k] += results[k]

    print 'Average latency: %.3f seconds' % (totals['latency-sum'] / totals['ops'])
    print 'Average ocr time: %.3f seconds' % (totals['ocr-sum'] / totals['ops'])
    print 'Average conversion time: %.3f seconds' % (totals['convert-sum'] / totals['ops'])

if __name__ == '__main__':
    main()