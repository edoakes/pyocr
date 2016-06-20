#!/usr/bin/env python
import os, sys, requests, json, base64, time, random, collections, argparse
from multiprocessing import Process, Pipe

ARRIVAL_INTERVAL_MEAN = 1
ARRIVAL_INTERVAL_DEV = 0.5

def config(file):
    with open(file) as fd:
        conf = json.loads(fd.read())

    return conf

def rand_file(rel_path):
    path = os.path.join(os.path.dirname(__file__), rel_path)

    if os.path.isdir(path):
        file = os.path.join(path, random.choice(os.listdir(path)))
    else:
        file = path

    return open(file, 'r')

def file_data(code, fd):
    if code == 'b64':
        return base64.b64encode(fd.read())
    elif code == 'name':
        return os.path.basename(fd.name)

    return None


class User():
    def __init__(self, fbid, endtime):
        self.url = conf['url']
        self.endtime = endtime

        self.stats = {'ops': 0, 'latency': 0.0}
        for stat in conf['stats']:
            self.stats[stat] = 0.0

        self.freq_tot = 0
        self.ops = []

        index = 0
        for op in conf['ops']:
            self.freq_tot += op['freq']
            self.ops.append({'index': index, 'freq': op['freq']})
            index += 1


    def post(self, data):
        print data['op']

        t0 = time.time()
        r = requests.post(self.url, data=json.dumps(data))
        t1 = time.time()

        self.stats['ops'] += 1
        self.stats['latency'] += (t1-t0)

        ret = json.loads(r.text)

        for stat in conf['stats']:
            self.stats[stat] += float(ret[stat])

        return r.text

    def do_op(self, index):
        op = conf['ops'][index]['data']

        data = {}
        files = {}
        if 'files' in op:
            for pair in op['files'].items():
                files[pair[0]] = rand_file(pair[1])

        data['op'] = op['code']

        for pair in op['data'].items():
            key = pair[0]
            value = pair[1]

            if type(value) == dict:
                for subpair in value.items():
                    subkey = subpair[0]
                    subvalue = subpair[1]
                    data[key] = file_data(subkey, files[subvalue])
            else:    
                data[key] = value

        for file in files:
            files[file].close()

        return self.post(data)

    def rand_op(self):
        r = random.randrange(0, self.freq_tot)
        for op in self.ops:
            if r <= op['freq']:
                self.do_op(op['index'])
                break
            r -= op['freq']

    def run(self):
        while True:
            delay = max(random.normalvariate(ARRIVAL_INTERVAL_MEAN,
                                             ARRIVAL_INTERVAL_DEV), 0)
            if time.time() + delay >= self.endtime:
                break
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
    parser.add_argument('config', metavar="config", type=str, help='a configuration file for the RPCs')
    args = parser.parse_args()

    global conf
    conf = config(args.config)

    endtime = time.time() + args.seconds

    procs = []
    for i in range(args.users):
        procs.append(UserProcess(i+1, endtime))

    for proc in procs:
        proc.start()

    totals = {'latency': 0.0, 'ops': 0.0}
    for stat in conf['stats']:
        totals[stat] = 0.0

    for proc in procs:
        results = proc.wait()
        for k in totals.keys():
            totals[k] += results[k]

    for total in totals:
        if total == 'ops':
            continue
        print 'Average %s: %.3f seconds' % (total, totals[total] / totals['ops'])


if __name__ == '__main__':
    main()