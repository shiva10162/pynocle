#!/usr/bin/env python
"""
pynocle is a module for reporting of code metrics and other
inspection/reporting features.

It is meant to be used as a very simple API,
usually as part of the the testing/build process.
Simply create a new Monocle object with the directories
and files you want to analyze (along with coverage data if you have it),
and call generate_all.
"""
import datetime
import os
import shutil
import sys

import cyclcompl
import depgraph
import sloc
import utils


def ensure_clean_output(outputdir, _ran=0):
    """rmtree and makedirs outputdir to ensure a clean output directory.

    outputdir: The folder to create.
    _ran: For internal use only.
    """
    # There is a potential race condition where rmtree seems to succeed
    # and makedirs fails so the directory doesn't exist.
    # So for the time being, if makedirs fails, we re-invoke the function
    # 3 times.  I have observed this condition many times in the wild-
    # I don't want to believe it exists, but it does.
    try:
        shutil.rmtree(outputdir)
    except WindowsError:
        pass
    if os.path.exists(outputdir):
        raise IOError('%s was not deleted.' % outputdir)
    try:
        os.makedirs(outputdir)
    except WindowsError:
        if _ran < 3:
            ensure_clean_output(outputdir, _ran=_ran + 1)
        if not os.path.isdir(outputdir):
            raise


def _create_dependency_group(codefilenames):
    """Generates a new DependencyGroup from codefilenames."""
    depb = depgraph.DepBuilder(codefilenames)
    dependencygroup = depgraph.DependencyGroup(depb.dependencies, depb.failed)
    return dependencygroup


def generate_html_jump(htmlfilename, projectname, jumppaths):
    """Generates an html file at filename that contains links
    to all items in paths.

    :param htmlfilename: Filename of the resultant file.
    :param jumppaths: Paths to all files the resultant file should
      display links to.
    """
    jumppaths = sorted(jumppaths)
    def getJumpsHtml():
        row = '<p><a href="{0}">{0}</a></p>'
        absdir = os.path.dirname(os.path.abspath(htmlfilename)) + os.sep
        def hrefpath(p):
            absp = os.path.abspath(p)
            relp = absp.replace(absdir, '')
            return relp
        return '\n'.join([row.format(hrefpath(p)) for p in jumppaths])

    datestr = datetime.date.today().strftime('%b %d, %Y')
    jumpshtml = getJumpsHtml()

    with open(htmlfilename, 'w') as f:
        fullhtml = """
    <html>
      <head>
        <title>%(projectname)s Project Metrics (by pynocle)</title>
      </head>
      <body>
        <h1>Metrics for %(projectname)s</h1>
        <p>The following reports have been generated for the project %(projectname)s by pynocle.<br />
        View reports for details, and information about what report is and suggested actions.</p>
    %(jumpshtml)s
    <p>Metrics generated on %(datestr)s<br />
    <a href="http://code.google.com/p/pynocle/">Pynocle</a> copyright
    <a href="http://robg3d.com">Rob Galanakis</a> 2012</p>
      </body>
    </html>
    """ % locals()
        f.write(fullhtml)


class Monocle(object):
    """Entry point for all metrics generation.

    :param outputdir: Directory to write reports.
    :param rootdir: The root directory of the python files to search.
      If None, use the cwd.
    :param coveragedata: A coverage.coverage instance.
      You can get this from running coverage,
      or loading a coverage data file.

    *_filename/*_dir: File/directory names to output metrics to.
    """
    def __init__(self,
                 projectname,
                 outputdir='output',
                 rootdir=None,
                 coveragedata=None,
                 coverhtml_dir='report_covhtml',
                 cyclcompl_filename='report_cyclcompl.html',
                 sloc_filename='report_sloc.html',
                 depgraph_filename='depgraph.png',
                 coupling_filename='report_coupling.html',
                 couplingrank_filename='report_couplingrank.html',
                 htmljump_filename='index.html'):
        if not isinstance(rootdir, basestring):
            raise ValueError, 'Monocle only supports one root directory right now.'
        self.rootdir = os.path.abspath(rootdir or os.getcwd())
        self.filenames = list(utils.walk_recursive(self.rootdir))

        self.projectname = projectname
        self.outputdir = outputdir
        self.coveragedata = coveragedata

        join = lambda x: os.path.join(self.outputdir, x)
        self.coverhtml_dir = join(coverhtml_dir)
        self.cyclcompl_filename = join(cyclcompl_filename)
        self.sloc_filename = join(sloc_filename)
        self.depgraph_filename = join(depgraph_filename)
        self.coupling_filename = join(coupling_filename)
        self.couplingrank_filename = join(couplingrank_filename)
        self.htmljump_filename = join(htmljump_filename)

        self._filesforjump = set()

    def ensure_clean_output(self):
        ensure_clean_output(self.outputdir)

    def generate_cover_html(self):
        """Outputs a coverage html report from cov into directory."""
        self.coveragedata.html_report(directory=self.coverhtml_dir)
        self._filesforjump.add(os.path.join(self.coverhtml_dir, 'index.html'))

    def generate_cyclomatic_complexity(self):
        """Generates a cyclomatic complexity report for all files in self.files,
        output to self.cyclcompl_filename.
        """
        ccdata, failures = cyclcompl.measure_cyclcompl(self.filenames)
        def makeFormatter(f):
            return cyclcompl.CCGoogleChartFormatter(
                f, leading_path=self.rootdir)
        utils.write_report(
            self.cyclcompl_filename, (ccdata, failures), makeFormatter)
        self._filesforjump.add(self.cyclcompl_filename)

    def generate_sloc(self):
        """Generates a Source Lines of Code report for all files in self.files,
        output to self.sloc_filename.
        """
        slocgrp = sloc.SlocGroup(self.filenames)
        def makeSlocFmt(f):
            return sloc.SlocGoogleChartFormatter(f, self.rootdir)
        utils.write_report(self.sloc_filename, slocgrp, makeSlocFmt)
        self._filesforjump.add(self.sloc_filename)

    def generate_dependency_graph(self, depgrp):
        """Generates a dependency graph image to self.depgraph_filename
        for the files in self.files.
        """
        renderer = depgraph.DefaultRenderer(depgrp, leading_path=self.rootdir)
        renderer.render(self.depgraph_filename)
        self._filesforjump.add(self.depgraph_filename)
        return depgrp

    def generate_coupling_report(self, depgrp):
        """Generates a report for Afferent and Efferent Coupling between
        all modules in self.filenames,
        saved to self.coupling_filename
        """
        def factory(f):
            return depgraph.CouplingGoogleChartFormatter(f, self.rootdir)
        utils.write_report(self.coupling_filename, depgrp, factory)
        self._filesforjump.add(self.coupling_filename)

    def generate_couplingrank_report(self, depgrp):
        """Generates a PageRank report for all code in self.filenames to
        self.couplingrank_filename.
        """
        def factory(f):
            return depgraph.RankGoogleChartFormatter(f, self.rootdir)
        utils.write_report(self.couplingrank_filename, depgrp, factory)
        self._filesforjump.add(self.couplingrank_filename)

    def generate_html_jump(self):
        """Generates an html page that links to any generated reports."""
        return generate_html_jump(
            self.htmljump_filename,
            self.projectname,
            self._filesforjump)

    def generate_all(self, cleanoutput=True):
        """Run all report generation functions.

        If coveragedata is not set, skip the coverage functions.

        If not self.debug, raises an AggregateError after all functions run
            if any function raises (so metrics will
            be generated for any function that succeeds).

        :param cleanoutput: If True, run ensure_clean_output to clear
          the output directory.
        """
        if cleanoutput:
            self.ensure_clean_output()
        exc_infos = []
        def trydo(func):
            try:
                return func()
            except Exception:
                exc_infos.append(sys.exc_info())

        trydo(self.generate_sloc)
        trydo(self.generate_cyclomatic_complexity)

        if self.coveragedata:
            trydo(self.generate_cover_html)

        depgrp = _create_dependency_group(self.filenames)
        trydo(lambda: self.generate_coupling_report(depgrp))
        trydo(lambda: self.generate_couplingrank_report(depgrp))
        #trydo(lambda: self.generate_dependency_graph(depgrp))
        trydo(self.generate_html_jump)
        #self.generate_funcinfo_report,
        #self.generate_inheritance_report,
        if exc_infos:
            raise utils.AggregateError(exc_infos)
