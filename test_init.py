#!/usr/bin/env python

import nose
import os
import sys

def run_on_pynocle(cov=None):
    import _pynoclecover
    #Under debugger in pycharm, it uses the wrong coverage module!
    try:
        result, cov = _pynoclecover.run_with_coverage(nose.run)
    except TypeError as exc:
        if exc.args[0] == "__init__() got an unexpected keyword argument 'data_file'":
            cov = None
        else:
            raise
    except NameError as exc:
        if exc.args[0] == "global name 'cache_location' is not defined":
            cov = None
        else:
            raise

    import pynocle
    dirname = os.path.dirname(__file__)
    outdir = os.path.join(dirname, 'exampleoutput')
    m = pynocle.Monocle(outdir, rootdir=dirname, coveragedata=cov, debug=True)
    m.generate_all()
    m2 = pynocle.Monocle(outdir, rootdir=dirname, debug=True,
                         cyclcompl_filename='report_cyclcompl.txt',
                         coupling_filename='report_coupling.txt',
                         couplingrank_filename='report_couplingrank.txt',
                         sloc_filename='report_sloc.txt')
    m2._filesforjump.update(m._filesforjump)
    m2.generate_all(False)

def run_on_ccppipeline():
    import pynocle
    dirname = os.path.dirname(__file__)
    pipedir = os.path.join(dirname, '..', 'pipeline')
    outdir = os.path.join(pipedir, 'metrics')
    sys.path.append(pipedir)
    m = pynocle.Monocle(outdir, rootdir=pipedir, debug=True)
    m.generate_all()

if __name__ == '__main__':
    if '--testccp' in sys.argv:
        run_on_ccppipeline()
    else:
        run_on_pynocle()
