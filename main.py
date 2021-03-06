from __future__ import division
import numpy as np
import scipy.sparse as sp
import logging
import pickle
import argparse 
import yaml
import sys
import os
import matplotlib.pyplot as plt

log = logging.getLogger('main');
log.setLevel(logging.DEBUG);

def pdbgen(fulldat, resname, filename):
	
    numatom, numsamp = fulldat.shape;
    numatom = numatom // 3;
    assert ( len(resname) == numatom );

    log.info('Constructing PDB file... \'{0}\''.format(filename));
    f = open(filename, 'w+');
    for i in range(numsamp):
        f.write('%-6s    %4i\n' %('MODEL', i+1));
        for j in range(numatom):
            f.write('%-6s%5i %4s %s  %4i    %8.3f%8.3f%8.3f%6.2f%6.2f          %2s  \n' \
				%('ATOM', j+1, 'CA', resname[j], j+1, fulldat[3*j,i], fulldat[3*j+1,i], fulldat[3*j+2,i], 0.0, 0.0, 'C'));
        f.write('ENDMDL\n');
    f.close();
    log.info('PDB file completed!');

def _get_anharm( data, function , j):
    above = np.abs(data) > function[j](data, j);
    num = np.sum(above);
    indices = np.argsort( - above )[:num];
    indices = indices[np.argsort(np.abs(data)[indices])];

    return list(indices), num;

def _get_time( devs, std, j ):
    a = [];
    a.append(devs[3*j] > std[0]);
    for i in range(1,3):
        a += devs[3*j+i] > std[i];
    return np.sum(a>0);

def main( config ):

    log = logging.getLogger('main');

    fh = logging.FileHandler(config['logfile']);
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s');
    fh.setLevel(logging.DEBUG);
    fh.setFormatter(formatter);
    
    log.addHandler(fh);

    log.info('Saving all files to: {0}'.format(os.path.abspath(config['saveDir'])));

    coords =    np.load(config['coords']);
    resnames =  np.load(config['resnames']);
    icacoffs = np.load( config['icacoffs'] );
    num_mat = np.zeros((icacoffs.shape[0], 4));
    data_mat = np.empty( shape=(icacoffs.shape[0], 4), dtype=list );
    cent_mat = np.empty((icacoffs.shape[0],2));

    #   Bring mean to 0
    mean = np.mean(icacoffs, axis=1);
    for i in range(icacoffs.shape[0]):
        icacoffs[i] -= mean[i];

    func = [];
    func.append( lambda x, i: np.mean(x) );
    for i in range(1,4):
        func.append( lambda x, i: i*np.std(x) );
    for i in range(icacoffs.shape[0]):
        for j in range(4):
            data_mat[i,j], num_mat[i,j] = _get_anharm( icacoffs[i], func, j );

    devs = coords - np.mean(coords, axis=1).reshape((-1,1));
    std = np.std(coords, axis = 1);
    
    anharm = [];
    for i in range(2):
        anharm.append([]);
        for j in range(coords.shape[0] // 3):
            anharm[i].append(_get_time(devs, (2+i)*std[3*j:3*j+3], j));
    
    anharm = 100*np.array( anharm )/ coords.shape[1];

    for i in range(2):
        log.info('Average Percenage of time spent outside {0} standard deviations: {1}%'.format(i+2,np.mean(anharm[i]) ));
    np.save( os.path.join(config['saveDir'], '{0}_percentage_anharm.npy'.format(config['pname'])), anharm);
    np.save( os.path.join(config['saveDir'], '{0}_num_anharm.npy'.format(config['pname'])), num_mat);
    np.save( os.path.join(config['saveDir'], '{0}_anharm_groups.npy'.format(config['pname'])), data_mat);

    #   Plotting
    color = ['black', 'green', 'blue', 'red'];
    fig = plt.figure();
    ax = fig.gca();
    for i in range(icacoffs.shape[0]):
        ax.plot(np.abs(icacoffs[i]), color='black', label='Data');
        stat = [];
        for j in range(1,4):
            stat.append( func[j](icacoffs[i], j) );
            ax.plot([0,icacoffs.shape[1]], [stat[j-1],stat[j-1]], color=color[j], label='{0}*Std. Dev.'.format(j));
        ax.set_title('ICA Anharmonicity: Moment {0}'.format(i));
        ax.set_xlabel('Conformation');
        ax.legend(fontsize=10);
        plt.savefig( os.path.join(config['figDir'], '{0}_anharm_moment{1}.png'.format(config['pname'], i)) );
        pickle.dump( fig, file( os.path.join(config['figDir'], '{0}_anharm_moment{1}.pickle'.format(config['pname'], i)), 'w+') );
        plt.cla();
        if 'graph' in config and config['graph']:
            plt.show();

    for i in range( icacoffs.shape[0] ):
        pdbgen( coords[:,data_mat[i,3]], 
                resnames,
                os.path.join(config['pdbpath'], '{0}_anharm_conform_moment{1}.pdb'.format(config['pname'],i)),
              );
        
def validate(config):

    req_dirs = ['saveDir',];
    for dr in req_dirs:
        if not dr in config:
            raise KeyError('You didn\'t provide a value for the required config value: {0}'.format(dr));
    other_dirs = {
            'figDir':os.path.join(config['saveDir'], 'figures'),
            'pdbpath':os.path.join(config['saveDir'], 'pdbfiles'),
                };
    req_dirs.extend(other_dirs.keys());
    config.update(other_dirs);
    for dr in req_dirs:
        if not os.path.isdir( config[dr] ):
            os.makedirs( config[dr] );

    files = ['coords', 'resnames', 'icacoffs',];
    for f in files:
        if not f in config:
            raise KeyError('You didn\'t provide a value for the required config value: {0}'.format(dr));
        if not os.path.isfile(config[f]):
            raise IOError('The file path given for \'{0}\': \'{1}\' isn\'t a file.'.format(f, config[f]));

    config['logfile'] = os.path.join(config['saveDir'], 'log_icanalysis.txt');
    return config;

if __name__ == '__main__':

    #   Setup parser
    parser = argparse.ArgumentParser()
    parser.add_argument('-g', action='store_true', dest='graph', default=False, help='Shows graphs.');
    parser.add_argument('-v', action='store_true', dest='verbose', default=False, help='Runs program verbosely.');
    parser.add_argument('-d', '--debug', action='store_true', dest='debug', default=False, help='Prints debugging help.');
    parser.add_argument('--config', type=str, dest='configpath', default='config.yaml',
                        help='Input other configuration file.');

    values = parser.parse_args()

    #   Get config from file
    with open(values.configpath) as f:
        conf_file = f.read();
        config = yaml.load(conf_file);
    if not 'config' in locals(): raise IOError(
    'Issue opening and reading configuration file: {0}'.format(os.path.abspath(values.configpath)) );

    #   Update config with CLARGS
    level = 30;
    if values.verbose: level = 20;
    elif values.debug: level = 10;
    config['graph'] = values.graph;

    config = validate(config);

    #   Setup stream logger
    ch = logging.StreamHandler(sys.stdout);
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s');
    ch.setLevel(level);
    ch.setFormatter(formatter);

    log.addHandler(ch);

    log.debug('Configuration File:\n'+conf_file);
    log.info('Using Configuration File: {0}'.format(os.path.abspath(values.configpath)));

    if not os.path.isfile( config['icacoffs'] ):
        raise IOError( 'Error opening icacoffs file: {0}'.format(os.path.abspath(config['icacoffs'])) );

    main( config );
