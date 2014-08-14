#!/usr/bin/env python
#
# Copyright 2014 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied. See the License for the specific language governing permissions and limitations under
# the License.
import gce_helper
from fabric.api import *
from contextlib import nested
import json
import os
import utils
import sqlite3 as lite
import datetime
from operator import itemgetter
import itertools
from collections import defaultdict

class DenovoHelper(object):
    """ Helper for running commands on denovo instances

    Wraps up ssh requests and submits them
    """
    def __init__(self, helper):
        self.gce_helper = helper
        self.jobs = {}
        with JobTable() as tbl:
            for stat in ("submitted", "running"):
                self.jobs[stat] = tbl.get_jobs_by_status(stat)

    def denovo_update_from_github(self):
        """ Update denovo-variant-caller on all hosts"""
        with cd("denovo-variant-caller"):
            run("git pull origin master")

    @with_settings(shell_escape=False)
    def denovo_any_cmd(self, cmd):
        """ Run any command on denovo instances """
        for line in run(cmd).splitlines():
            print("#"+line)

    def denovo_push_client_secrets(self):
        """ Push denovo client_secrets file to all hosts """
        local()

    def denovo_run_mvn_package(self):
        """ Run maven package on all hosts """
        with cd("denovo-variant-caller"):
            run("mvn package")

    @with_settings(shell_escape=False)
    def denovo_exec_bg_cmd(self, \
            cmd, err="my.err", out="my.out", inp="/dev/null"):
        """ Run background job with no hup"""
        cmd = "(nohup " + cmd + " 2>%s 1>%s <%s & ); "%(err, out, inp) +\
            " ps ax --sort=etime " +\
            "| grep -F \'" + cmd + "\' " +\
            "| grep -v -F 'grep' | head -n 1 | tr -s \' \'"
        for line in run(cmd).splitlines():
            return line.split()[0]

    @with_settings(shell_escape=False)
    def denovo_run_from_cli(self, denovo_cli):
        """ Run java program using command line params """
        with cd("denovo-variant-caller"):
            return self.denovo_exec_bg_cmd(denovo_cli)

    @with_settings(shell_escape=False)
    def denovo_run_from_jsonf(self, f):
        """ Run java program from params stored in json """
        with open(f) as fin :
            json_string = fin.read()
        builder = DenovoBuilder()
        denovo_cli = builder.from_json(json_string).to_string()
        return self.denovo_run_from_cli(denovo_cli)

    def update_jobs_table(self):
        """ Update the jobs table """
        hostname = self.gce_helper.IPtoNameMap[env.host]
        updates = defaultdict(list)

        for job in itertools.chain(self.jobs["submitted"],self.jobs["running"]):
            db_hostname, db_pid = job[3], job[1]
            if db_hostname != hostname :
                continue
            if not self._check_pid_exists(db_pid):
                updates["finished"].append(job[0])
            else:
                updates["running"].append(job[0])

        updates = dict(updates)
        with JobTable() as tbl:
            for stat in updates:
                tbl.update_stat(updates[stat], stat)
            tbl.display_all()


    def _check_pid_exists(self, pid):
        """ Check that a pid exists """
        return int(run("[ -e /proc/%d ] && echo 1 || echo 0"%pid))

class DenovoBuilder(object):
    """ Builder object for denovo commandline options """

    arglist = ["stage_id"]
    optlist = ["chromosome", "client_secrets_filename", "debug_level",
               "denovo_mut_rate", "inference_method", "input_file",
               "job_name", "lrt_threshold", "num_threads", "output_file",
               "seq_err_rate"]

    def __init__(self):
        self.opts = {}
        from argparse import ArgumentParser
        self.parser = ArgumentParser(description="Parser for strings")

        for arg in DenovoBuilder.arglist:
            self.parser.add_argument(arg, type=str)
        for opt in DenovoBuilder.optlist:
            self.parser.add_argument("--"+opt, type=str)

    def from_string(self, s):
        """ Convert to string"""
        java_string = "java -jar target/denovo-variant-caller-0.1.jar "
        if s.startswith(java_string):
            s = s[len(java_string):]

        parsed = self.parser.parse_args(s.split())
        self.opts = parsed.__dict__
        return self

    def from_json(self, j):
        self.opts = json.loads(j)
        return self

    def to_json(self):
        return json.dumps(self.opts)

    def to_string(self):
        s = "java -jar target/denovo-variant-caller-0.1.jar " +\
            " ".join(v for k,v in self.opts.items() \
                     if k in DenovoBuilder.arglist) + " " +\
            " ".join("--"+k+" "+v for k,v in self.opts.items() \
                     if k not in DenovoBuilder.arglist and v is not None)
        return s

    def update_from_dict(self, d):
        self.opts.update(d)

class JobTable:
    """ MySQL table containing all the jobs and the job ids """
    def __enter__(self):
        self.con = lite.connect(utils.constants["JOB_TABLE"])
        self.cur = self.con.cursor()
        self._create_table()
        return self

    def __exit__(self, type, value, traceback):
        self.con.close()

    def insert_record(self, record):
        """ Insert a record into the table """
        cmd = "insert into jobs(job_id, pid, ts, mach, stat, cmd) values"+\
            "(?, ?, ?, ?, ?, ?)"
        self.cur.execute(cmd, record)
        self.con.commit()

    def get_jobs_by_status(self, status, all=False):
        """ Get jobs according to status - submitted/running/finished """
        cmd = 'select * from jobs where stat="%s"'%status
        self.cur.execute(cmd)
        return self.cur.fetchall()

    def get_max_jobid(self):
        """ Return the max job id stored in the table """
        cmd = "select max(job_id) from jobs"
        self.cur.execute(cmd)
        max_id = self.cur.fetchone()
        return max_id[0]

    def display_all(self):
        """ Display all the records """
        cmd = "select * from jobs"
        self.cur.execute(cmd)
        for line in self.cur.fetchall():
            print(line)

    def _create_table(self):
        """ Create a job table """
        cmd = "create table if not exists jobs(job_id int, pid int, "+\
            "ts timestamp, mach text, stat text, cmd text)"
        self.cur.execute(cmd)

    def _delete_table(self):
        """Delete the job table"""
        cmd = "drop table jobs"
        self.cur.execute()

    def update_stat(self, jobids, stat):
        """ updates values """
        cmd = 'update jobs set stat="%s" '%stat + 'where job_id in ('+\
            ','.join(map(str,jobids)) +')'
        print cmd
        self.cur.execute(cmd)
        self.con.commit()

if __name__ == '__main__':
    helper = gce_helper.GCEHelper()
    denovo_helper = DenovoHelper(helper)
    builder = DenovoBuilder()
    print(builder.from_string(
        "java -jar target/denovo-variant-caller-0.1.jar stage1 "+\
        "--client_secrets_filename ~/Downloads/client_secrets.json "+\
        "--job_name myStage1Job "+\
        "--output_file stage1.calls "+\
        "--debug_level 1").to_json());
    print(builder.from_string(builder.to_string()).to_string())

    with JobTable() as tbl:
        now = datetime.datetime.now()
        max_job_id = tbl.get_max_jobid()
        new_job_id = 1 if max_job_id is None else max_job_id+1
        record = (new_job_id, 5300, now, "denovo-1", "submitted", "ls -la")
        tbl.insert_record(record)
        record = (new_job_id+1, 5301, now, "denovo-1", "submitted", "ls -la")
        tbl.insert_record(record)
        for rec in tbl.get_jobs_by_status("submitted"):
            print rec

