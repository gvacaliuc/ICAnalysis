def icanalysis_view(request, path):
    plugin_name = path.split('/')[0];
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

        job = globals()[str(plugin.name)+'_job']().save(commit=False);

        #   Creates model and commits
        job.username    = request.user.username;
        job.userid      = request.user.id;
        job.jobid       = jobid;
        job.saveDir     = saveDir;
        job.logfile     = logfile;
        job.figDir      = figDir;
        job.state       = 2;    #   State = QUEUED
        job.icacoffs    = icacoffs_path;
        job.resnames    = resnames_path;
        job.coords      = coords_path;
        job.pname       = pname;
        job.save(commit=True);
        
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

    jobs = Job.objects.filter( userid = request.user.id );
    context['jobs'] = jobs;

    return render(request, path+'index.html', context);
