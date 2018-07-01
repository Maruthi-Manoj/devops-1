'''
Requires fpm to be installed on target
gem install fpm
'''
import datetime
import string
import os
import re
import base64
import re
import requests
from fabric.api import env, cd, run, shell_env
#import gitlab_helper

# Where all the rpms are built
env.hosts= ['35.231.84.32']
env.user = 'root'
env.key_filename = '~/.ssh/id_rsa'

# Where to clone all the repos
WORKDIR = os.getenv('WORKDIR', '/root/rpm_building')
# Where the atlas svn path exists on host
ATLASDIR = os.getenv('SVNDIR', '/www2/ATLAS/x86_64/6')

# extra pips required
# Should eventually move into actual repo
extra_pips = [
        'uWSGI==2.0.14',
        'supervisor==3.1.3',
        ]

def build_xap(branch='develop', sha='latest'):
    '''Build rpm of target'''
    sha = _get_branch_and_real_sha('Spark', branch, sha)
    _build_rpm_from_directory('Spark', branch, sha)


def _get_branch_and_real_sha(name, branch, sha):
    '''
    Gets the branch and then returns the real sha if set to latest
    If sha is set then it just uses that to pull code
    '''
    run("rm -rf %s/%s" % (WORKDIR, name))
    with cd(WORKDIR):
        run("git clone git@github.com:Maruthi-Manoj/%s.git --branch %s" % (name, branch))
    # If there is a sha do a reset on that sha to get that specific snapshot
    if sha != 'latest':
        with cd('%s/%s' % (WORKDIR, name)):
            run("git reset --hard %s" % sha)
    # If latest get the current sha and set it to it
    sha = _get_current_sha_if_latest(name, sha)
    if not sha or sha == '':
        raise SystemExit('Invalid sha found %s' % sha)
    return sha

def _directory_repo_fpm_command(name, version, build, sha):
    year = datetime.datetime.now().year
    release = "%s.%s" % (build, sha)
    fpm_command = string.Template(
            "fpm -f -s tar -t rpm -n $name -v $version --iteration $release "
            "--description \"$sha\" "
            "--license '$year. manohar. All rights reserved.' "
            "--url 'https://github.com/Maruthi-Manoj' --directories /app/$name-$version-$build.$sha "
            "--prefix /app/$name-$version-$build.$sha "
            "$name.tar.gz"
            ).substitute(name=name, version=version, build=build, year=year, sha=sha, release=release)
    return fpm_command

def _build_rpm(name, version, build, sha):
    '''
    Builds a rpm
    '''
    build, _, _ = _get_build_number_and_latest_sha(name, version)
    # traffic consumer is special
    # 2 rpms get built for it
    if name == 'pr_device_traffic_data':

        _build_consumer("pr_device_usage_ingestion", version, build, sha)
        _build_consumer("network_activity_accumulator", version, build, sha)
        _build_consumer("network_activity_detection", version, build, sha)
        _build_consumer("device_usage_aggregation_daily", version, build, sha)
        _build_consumer("device_usage_aggregation_hourly", version, build, sha)
        _build_consumer("network_activity_limits_simulator", version, build, sha)
        _build_consumer("network_activity_simulator", version, build, sha)

    with cd(WORKDIR):
        filename = _get_full_rpm_name(name, version, build, sha)
        if name in SCALA_CONSUMERS:
            fpm_command = _spark_fpm_command(name, version, build, sha)
        else:
            fpm_command = _directory_repo_fpm_command(name, version, build, sha)
        run(fpm_command)
    _add_rpm_to_repo(name, filename, version)
    _final_cleanup(name, version)

def _get_full_rpm_name(name, version, build, sha):
    '''
    Gets the full rpm name
    '''
    filename= "%s-%s-%s.%s.x86_64.rpm" % (name, version, build, sha)
    return filename


def _add_rpm_to_repo(name, filename, version):
    with cd(WORKDIR):
        run('chmod 666 %s' % filename)
        # openstack yumrepo
        run('mkdir -p /www/html/repos/xpc/%s' % version)
        # atlas yumrepo
        run('mkdir -p /www/html/xpc/x86_64/6/global')
        # Add rpm to atlas repo
        run("cp -r %s %s/global/." % (filename, ATLASDIR))
        # Move rpm to openstack repo
        run("mv %s /www/html/repos/xpc/%s/." % (filename, version))

def _final_cleanup(name, version):
    '''
    cleans up rpm build
    '''
    with cd(WORKDIR):
        run("rm -rf %s.tar.gz" % name)

def _build_rpm_from_directory(name, branch, sha):
    '''
    Helper function to build all the rpms
    '''
    with cd(WORKDIR):
        if branch == 'xpc_extender':
            run('GZIP=-9 tar -cvzf xpc_extender.tar.gz --exclude=.git -C {0} .'.format(name))
        else:
            run('GZIP=-9 tar -cvzf {0}.tar.gz --exclude=.git -C {0} .'.format(name))
    version = _determine_version(branch)
    if branch == 'xpc_extender':
        name = 'xpc_extender'
    build, _, _ = _get_build_number_and_latest_sha(name, version)
    _build_rpm(name, version, build, sha)

def _get_build_number_and_latest_sha(name, version):
    '''
    Checks the rpm directory and determines the next build number
    based on name and version
    Returns a tuple of
    (next_build_number, last_build_number, latest_sha)
    '''
    regex = re.compile("%s-%s.*-([0-9]+)\.([^\.]*)\.?x86_64.rpm" % (name, version))
    run('mkdir -p /www/html/repos/xpc/%s' % version)
    ls_data = run('ls -al /www/html/repos/xpc/%s 2>/dev/null' % version)
    current_build = 0
    sha = None
    for match in regex.finditer(ls_data):
        build = int(match.groups(0)[0])
        sha = match.groups(0)[1]
        if build > current_build:
            current_build = build
    next_build = str(current_build + 1).zfill(2)
    print "Next build set to %s and latest sha is %s" % (next_build, sha)
    return next_build, current_build, sha

def _updaterepo():
    '''
    Reloads the repo database
    Required anytime repo changes
    '''
    run('restorecon /www/html/repos/xpc/*')
    run('restorecon /www/html/repos/xpc/**/*')
    run('createrepo --update /www/html/repos/xpc')

def _determine_version(branch):
    '''
    Based on what branch the version is returned
    '''
    current_version, previous_version = _get_current_versions()
    # xpc uses branch master where odp uses branch develop for main branch
    if branch == 'develop' or branch == 'master' or branch == 'spark2' or branch == 'xpc_extender':
        return current_version
    elif branch == 'developn-1' or branch == 'odp-patch' or branch == 'xpc-patch':
        return previous_version
    raise SystemExit("Invalid branch '%s': Only develop, master and developn-1 allowed" % branch)

def _get_current_versions():
    '''
    Gets the version from within sprint_version.txt
    '''
    with open('./sprint_version.txt') as version_file:
        version_info = version_file.read()

    # Determine the current sprint via the sprint_version.txt file
    # This file is updated on end of sprint manually
    current_match = re.search("current_sprint = '(.*)'", version_info)
    previous_match = re.search("previous_sprint = '(.*)'", version_info)
    current_version = current_match.groups(0)[0]
    previous_version = previous_match.groups(0)[0]
    return (current_version, previous_version)

def _commit_atlas_changes():
    '''
    Adds changes to atlas
    '''
    with cd(ATLASDIR):
        run("svn add --force .")
        run('svn commit --username xpcgithub --password meta3030! '
                '-m "Updating repo for xpc"')

def _get_current_sha_if_latest(name, sha='latest'):
    '''
    If sha is set to latest
    Get the current one
    '''
    if sha != 'latest':
        return sha
    with cd(WORKDIR + '/' + name):
        last_commit = run('git log -1 --oneline')
    new_sha = last_commit.split('\r')[1].split(' ')[0]
    return new_sha


def add_virtualenv(name, relative_requirement_path='.', force=False):
    # francis said this will work
    virtualdir = 'virtualenvs'
    with cd(WORKDIR):
        if force:
            run('rm -rf %s/%s' % (virtualdir, name))
        run('if [[ ! -d %s ]]; then mkdir virtualenvs;fi' % virtualdir)
        run('if [[ ! -d {1}/{0} ]]; then virtualenv --always-copy -p /app/interpreters/python/2.7.11/bin/python2.7 {1}/{0};fi'.format(name, virtualdir))
        run('./{2}/{0}/bin/pip install -r {0}/{1}/requirements.txt'.format(
            name, relative_requirement_path, virtualdir))
        for pip in extra_pips:
            run('./{2}/{0}/bin/pip install {1}'.format(
                name, pip, virtualdir))

        # http://stackoverflow.com/questions/6628476/renaming-a-virtualenv-folder-without-breaking-it

        run('virtualenv --relocatable %s/%s' % (virtualdir, name))
        # This is to make source activate work -- useful only for debugging
        # Look at stackoverflow question above if you want to know why
        run('sed -i "s/^VIRTUAL_ENV=.*/VIRTUAL_ENV=\/app\/{0}\/virtualenv/g" {1}/{0}/bin/activate'.format(
            name, virtualdir))

        run('cp -r {1}/{0} {0}/virtualenv'.format(name, virtualdir))


def _get_full_version_from_rpmrepo(name, version, build, sha, branch='develop') :
    '''
    If sha or version or build are not set. Get the latest
    '''
    # If version is not set.. no way to use sha and build
    if version == '' and (sha != '' or build != ''):
        raise SystemExit('Version not set but sha is or build is sha (%s) build (%s)' % (sha, build))
    # can't make full version if we don't have sha and version together
    if (sha != '' and build == '') or (sha == '' and build != ''):
        raise SystemExit('If sha or build are set the other must be as well')
    # If all values are given then just create the version string
    if sha != '' and version != '' and build != '':
        full_version = _create_full_version(version, build, sha)
        print('Full version is %s' % full_version)
        return full_version
    # If the version is not set get the version based on the branch
    if version == '':
        version = _determine_version(branch)
    # Get the current build and latest sha
    _, current_build, latest_sha = _get_build_number_and_latest_sha(name, version)
    if current_build <= 0:
        raise SystemExit('There is no build at %s %s' % (name, version))
    # If the sha was not set then use the latest one
    if sha == '':
        sha = latest_sha
    full_version = _create_full_version(version, current_build, sha)
    print('Full version is %s' % full_version)
    return full_version

def _create_full_version(version, build, sha):
    build = str(build).zfill(2)
    if sha == '':
        full_version = "%s-%s" % (version, build)
    else:
        full_version = "%s-%s.%s" % (version, build, sha)
    print "Full version:", full_version
    return full_version

def update_atlas():
    _commit_atlas_changes()

def update_xaprepo():
    _updaterepo()
