from core.views import *
from core.models import PluginModel, Job
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render

import os
import markdown
md = markdown.Markdown();
import glob
from importlib import import_module
import sys

def icanalysis_view(request, path):
    plugin_name = path.split('/')[0].lower();
    plugin = PluginModel.objects.filter(name = plugin_name)[0];
    username = request.user.username;
    context = {'plugin':plugin,'username':username,};

    with open(os.path.join(plugin.folder, 'description.md')) as f:
        desc = md.convert(f.read());
        setattr(plugin, 'description', desc);
    with open(os.path.join(plugin.folder, 'README.md')) as f:
        readme = md.convert(f.read());
        setattr(plugin, 'readme', readme);

    if request.method == 'POST' and 'job_selected' in request.POST:
        numjob = len( Job.objects.filter( userid = request.user.id ) );
        jobid = str('{:03}'.format(request.user.id)+\
                    '{:02}'.format(plugin.pluginid)+\
                    '{:02}'.format(numjob)
                   );

        parent_jobid = request.POST['job'];
        parent_plugin = PluginModel.objects.filter( pluginid = parent_jobid[3:5] )[0].name;
        parent = globals()[str(parent_plugin)+'_job'].objects.filter( jobid = parent_jobid)[0];

        parent_saveDir  = parent.saveDir;
        with open('/home/v32/Devel/log.txt', 'w+') as f:
            f.write(parent_saveDir + '\n');
        icacoffs_path   = os.path.join( parent_saveDir, glob.glob(os.path.join( parent_saveDir, '*icacoffs*'))[0] );
        resnames_path   = os.path.join( parent_saveDir, glob.glob(os.path.join( parent_saveDir, '*resnames*'))[0] );
        coords_path     = os.path.join( parent_saveDir, glob.glob(os.path.join( parent_saveDir, '*coords*'))[0] );
        pname           = parent.pname;
        
        #Loads in all the excluded data
            #   Need static_root for hosting these files
        saveDir = os.path.join(static_root, 'user_{0}'.format(request.user.id), 'savefiles_job{0}'.format(jobid));
        figDir  = os.path.join(saveDir, 'figures');
        if not os.path.isdir(saveDir):
            os.makedirs(saveDir);
        if not os.path.isdir(figDir):
            os.makedirs(figDir);
        logfile = os.path.join(saveDir, 'log.txt');

        #   Creates model and commits
        job_config = {};
        job_config['username']    = request.user.username;
        job_config['userid']      = request.user.id;
        job_config['jobid']       = jobid;
        job_config['saveDir']     = saveDir;
        job_config['logfile']     = logfile;
        job_config['figDir']      = figDir;
        job_config['state']      = 2;    #   State = QUEUED
        job_config['icacoffs']    = icacoffs_path;
        job_config['resnames']    = resnames_path;
        job_config['coords']      = coords_path;
        job_config['pname']       = pname;

        job = globals()[str(plugin.name)+'_job'](**job_config);
        job.save();
        
        #   Turn Model into Dict
        job_config = model_to_dict(job);

        #   Add to Job Queue
        pathtoplugin = [];
        pathtoplugin.append(plugin.folder.split('/')[-2]);
        pathtoplugin.append(plugin.folder.split('/')[-1]);
        pathtoplugin.append('main');
        plugin_exec = import_module('.'.join(pathtoplugin));

        log = logging.getLogger('main');
        log.setLevel(logging.DEBUG);

        add_task(plugin_exec.main, job_config, jobid,);
        time.sleep(2);
        return HttpResponseRedirect('/account/');

    count = 0;
    jobs = _getjobs(request, request.user.id);
    keep = [];
    for i in range(len(jobs)):
        if jobs[i].plugin_name == 'wqaa':
            keep.append(jobs[i]);
    jobs = keep;
    keep = [];
    for i in range(len(jobs)):
        if len( icanalysis_job.objects.filter( pname = jobs[i].pname ) ) == 0:
            keep.append(jobs[i]);
    jobs = keep;

    if not len(jobs) == 0:
        context['jobs'] = jobs;

    return render(request, path+'index.html', context);

def _getjobs(request, userid, jobid=None):
    context = {'userid': userid,};
    if not jobid == None:
        context['jobid'] = jobid;
    plugins = PluginModel.objects.all();
    jobs = [];
    for plugin in plugins:
        temp = globals()[str(plugin.name)+'_job'].objects.filter(**context);
        for plug in temp:
            jobs.append(plug);
    return jobs;
